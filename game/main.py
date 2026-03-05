from __future__ import annotations

import traceback
import shutil
import json
import time
import sys
from pathlib import Path
from types import SimpleNamespace

import pygame

from game.audio.music_manager import MusicManager
from game.audio.sfx_manager import SFXManager
from game.combat.card import CardDef, CardInstance
from game.combat.combat_state import CombatState
from game.combat.combat_engine import CombatEngine
from game.content.card_art_generator import CardArtGenerator, export_prompts
from game.content.enemy_art_generator import EnemyArtGenerator
from game.content.background_generator import BackgroundGenerator
from game.content.guide_avatar_generator import GuideAvatarGenerator, GUIDE_TYPES
from game.core.bootstrap_assets import ensure_placeholder_assets
from game.core.localization import LocalizationManager
from game.core.lore_service import LoreService
from game.lore.lore_engine import LoreEngine
from game.core.paths import data_dir, assets_dir
from game.core.rng import SeededRNG
from game.core.safe_io import atomic_write_json, atomic_write_json_if_changed, load_json
from game.core.settings_store import load_settings, save_settings
from game.core.state_machine import StateMachine
from game.settings import FPS, INTERNAL_HEIGHT, INTERNAL_WIDTH
from game.qa.runner import QARunner
from game.qa.content_validator import validate_content
from game.ui.render import AssetManager, Renderer
from game.ui.screens.combat import CombatScreen
from game.ui.screens.deck import DeckScreen
from game.ui.screens.error import ErrorScreen
from game.ui.screens.event import EventScreen
from game.ui.screens.map import MapScreen
from game.ui.screens.menu import MenuScreen
from game.ui.screens.path_select import PathSelectScreen
from game.ui.screens.reward import RewardScreen
from game.ui.screens.settings import SettingsScreen
from game.ui.screens.shop import ShopScreen
from game.ui.screens.qa_results import QAResultsScreen
from game.ui.screens.pack_opening import PackOpeningScreen
from game.ui.screens.end import EndScreen
from game.ui.screens.intro import IntroScreen
from game.ui.screens.pacha_transition import PachaTransitionScreen
from game.version import VERSION
from game.art.gen_art32 import GEN_ART_VERSION, GEN_BIOME_VERSION
from game.services.content_service import ContentService
from game.services.asset_pipeline import AssetPipeline
from game.services.audio_pipeline import AudioPipeline
from game.systems.reward_system import build_reward_boss, build_reward_guide, build_reward_normal
from game.ui.screens.loading import LoadingScreen

DEFAULT_CARDS = [
    {"id": "strike", "name_key": "card_strike_name", "text_key": "card_strike_desc", "rarity": "basic", "cost": 1, "target": "enemy", "tags": ["attack"], "effects": [{"type": "damage", "amount": 6}]},
    {"id": "defend", "name_key": "card_defend_name", "text_key": "card_defend_desc", "rarity": "basic", "cost": 1, "target": "self", "tags": ["skill"], "effects": [{"type": "block", "amount": 5}]},
]
DEFAULT_ENEMY = {"id": "dummy", "name_key": "enemy_voidling_name", "hp": [20, 20], "pattern": [{"intent": "attack", "value": [5, 5]}]}


class App:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            print("[audio] mixer disabled")

        self.project_root = Path(__file__).resolve().parent
        self.asset_root = assets_dir() if callable(assets_dir) else (self.project_root / "assets")
        self.data_root = data_dir() if callable(data_dir) else (self.project_root / "data")
        (self.asset_root / ".cache").mkdir(parents=True, exist_ok=True)
        (self.asset_root / "tmp").mkdir(parents=True, exist_ok=True)
        (self.data_root / ".cache").mkdir(parents=True, exist_ok=True)

        self.clock = pygame.time.Clock()
        self.running = True
        self.rng = SeededRNG(1337)
        self.user_settings = load_settings()
        self.loc = LocalizationManager(self.user_settings.get("language", "es"))
        self.renderer = Renderer()
        if self.user_settings.get("fullscreen", False):
            self.renderer.toggle_fullscreen()
        self.assets = AssetManager()
        self.sfx = SFXManager()
        self.music = MusicManager()
        self.sfx.set_volume(self.user_settings.get("sfx_volume", 0.7))
        self.music.set_volume(self.user_settings.get("music_volume", 0.5))
        self.music.set_muted(self.user_settings.get("music_muted", self.user_settings.get("music_mute", False)))
        # font pipeline (local pack + safe fallback)
        fonts_dir = data_dir().parent / "assets" / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)
        title_path = fonts_dir / "title.ttf"
        ui_path = fonts_dir / "ui.ttf"
        mono_path = fonts_dir / "mono.ttf"

        def _safe_font(path, size, fallback_name="arial", bold=False):
            try:
                if path.exists():
                    return pygame.font.Font(str(path), size)
            except Exception:
                pass
            return pygame.font.SysFont(fallback_name, size, bold=bold)

        self.font = _safe_font(ui_path, 24)
        self.small_font = _safe_font(ui_path, 22)
        self.tiny_font = _safe_font(ui_path, 18)
        self.big_font = _safe_font(title_path, 34, bold=True)
        self.card_text_font = _safe_font(ui_path, 20)
        self.card_title_font = _safe_font(title_path, 26, bold=True)
        self.map_font = _safe_font(ui_path, 24)
        self.mono_font = _safe_font(mono_path, 22)
        self.sm = StateMachine()
        self.run_state = None
        self.menu_return_screen = None
        self.combat_actions_log = []
        self.last_biome_seen = None
        self.node_lookup = {}
        self.current_node_id = None
        self.debug_overlay = False
        self.debug = {"last_ui_event": "-", "hovered_card_id": "-", "selected_card_id": "-", "target_mode": False, "combat_end_turn_button_visible": False, "combat_status_button_visible": False, "combat_end_turn_rect": "-", "combat_status_rect": "-", "enemy_intent": "-", "art_regenerated": 0, "xp_last_gain": 0}
        self.asset_generation_active = False
        self.asset_generation_progress = 1.0
        self.asset_generation_label = ""
        self._restart_requested = False
        self._restart_reason = ""

        self.loading_screen = LoadingScreen(self.big_font, self.font)
        self._loading_step("Inicializando", 0.01)

        content_payload = ContentService().load_all(progress_cb=self._loading_step)
        self.content = SimpleNamespace(
            cards=content_payload.get("cards", []),
            enemies=content_payload.get("enemies", []),
            bosses=content_payload.get("bosses", []),
            dialogues_combat=content_payload.get("dialogues_combat", {}),
            dialogues_events=content_payload.get("dialogues_events", {}),
            status=content_payload.get("status", "OK"),
            errors=content_payload.get("errors", []),
        )
        self.content.debug_counts = lambda: {
            "cards": len(self.content.cards),
            "enemies": len(self.content.enemies),
            "bosses": len(self.content.bosses),
            "dialogues_combat": bool(self.content.dialogues_combat),
            "dialogues_events": bool(self.content.dialogues_events),
        }
        self.debug["content_status"] = self.content.status
        self.debug["art_status"] = "OK"
        self.debug["music_status"] = "OK"
        self.debug["biome_status"] = "OK"
        self.debug["last_regen_ts"] = int(time.time())
        self.cards_data = self._load_cards_data()
        self.card_defs = {c["id"]: c for c in self.cards_data}
        self.enemies_data = self._load_enemies_data()
        self.events_data = self._load_events_data()
        self.relics_data = self._load_relics_data()
        self.lore_service = LoreService()
        self.lore_engine = LoreEngine((data_dir().parent).parent)
        self.biomes_lore = self._load_biomes_lore_data()
        self.lore_data = self.lore_service.data
        self.debug["lore_status"] = self.lore_service.status
        self.debug["lore_paths"] = ",".join(str(v) for v in self.lore_service.paths.values())
        self.design_doc = self._load_design_doc()
        self.canonical_design_source = str(data_dir() / "design" / "gdd_chakana_purple_wizard.txt")
        print(f"[boot] content OK cards={len(self.cards_data)} enemies={len(self.enemies_data)} events={len(self.events_data)} relics={len(self.relics_data)}")
        self.art_gen = CardArtGenerator()
        self.enemy_art_gen = EnemyArtGenerator()
        self.bg_gen = BackgroundGenerator()
        self.guide_gen = GuideAvatarGenerator()
        self.asset_pipeline = AssetPipeline(self.art_gen, self.enemy_art_gen, self.guide_gen, self.bg_gen)
        self.audio_pipeline = AudioPipeline()
        self.autogen_art_mode = self.user_settings.get("autogen_art_mode", "missing_only")
        self.user_settings.setdefault("detail_panel", False)
        self._apply_dev_reset_if_enabled()
        self.ensure_assets(progress_cb=self._loading_step)
        self._log_card_art_status()
        content_report = validate_content(self.cards_data, assets_dir())
        self.debug["content_validation"] = content_report
        print(f"[boot] validate_content status={content_report.get('status')} cards={content_report.get('cards')} summary_ok={content_report.get('summary_ok')} can_play_ok={content_report.get('can_play_ok')} placeholders={content_report.get('placeholders')} issues={len(content_report.get('issues', []))}")
        self.audio_pipeline.ensure_music_assets(self.user_settings, progress_cb=self._loading_step)
        self._loading_step("Completado", 1.0)
        dk = int(getattr(self.lore_engine, "keys_count", 0))
        covered = len([e for e in self.enemies_data if isinstance(self.lore_engine.combat_dialogues.get(e.get("id"), {}), dict)]) if isinstance(self.lore_engine.combat_dialogues, dict) else 0
        print(f"[load] dialogues_combat keys={dk} enemies_covered={covered}/{len(self.enemies_data)}")
        print(f"[boot] dialogues OK keys={dk}")
        print("[boot] assets OK")
        print(f"[boot] placeholders used: {self.debug.get('placeholders_used',0)}")
        self.debug["art_regenerated"] = self.art_gen.generated_count + self.art_gen.replaced_count

        self.validate_navigation_methods()
        pygame.display.set_caption(self.loc.t("game_title"))
        self.sm.set(IntroScreen(self))
        self.music.play_for(self.get_bgm_track("menu"))


    def _log_card_art_status(self):
        cards_dir = assets_dir() / "sprites" / "cards"
        total = len(self.cards_data)
        exists = 0
        missing = 0
        fallback = 0
        manifest = load_json(data_dir() / "art_manifest.json", default={})
        items = manifest.get("items", {}) if isinstance(manifest, dict) else {}
        for c in self.cards_data:
            cid = c.get("id")
            if not cid:
                continue
            p = cards_dir / f"{cid}.png"
            if p.exists():
                exists += 1
            else:
                missing += 1
            entry = items.get(cid, {}) if isinstance(items, dict) else {}
            if not p.exists() or bool(entry.get("placeholder", False)):
                fallback += 1
        print(f"[art] cards total={total} art_exists={exists} missing={missing} fallback_used={fallback}")
        if total > 0 and fallback == total:
            print("[art] WARNING fallback_used == total; pipeline broken")

    def _load_biomes_lore_data(self) -> dict:
        path = data_dir() / "lore" / "biomes_lore.json"
        payload = load_json(path, default={})
        return payload if isinstance(payload, dict) else {}

    def get_biome_lore(self, biome_id: str | None = None) -> dict:
        biome_key = str(biome_id or (self.run_state or {}).get("biome") or "kaypacha").lower()
        data = self.biomes_lore.get(biome_key, {}) if isinstance(self.biomes_lore, dict) else {}
        return data if isinstance(data, dict) else {}

    def get_biome_display_name(self, biome_id: str | None = None) -> str:
        biome_key = str(biome_id or (self.run_state or {}).get("biome") or "kaypacha").lower()
        lore = self.get_biome_lore(biome_key)
        return str(lore.get("display_name_es") or biome_key.title())

    def get_bgm_track(self, context: str, biome_id: str | None = None) -> str:
        ctx = str(context or "menu").lower()
        lore = self.get_biome_lore(biome_id)
        tracks = lore.get("bgm_tracks", {}) if isinstance(lore, dict) else {}
        if isinstance(tracks, dict):
            track = tracks.get(ctx)
            if isinstance(track, str) and track:
                return track
        fallback = {
            "menu": "menu",
            "map": f"map_{str(biome_id or (self.run_state or {}).get('biome') or 'kaypacha').lower()}",
            "combat": f"combat_{str(biome_id or (self.run_state or {}).get('biome') or 'kaypacha').lower()}",
            "boss": "boss",
            "events": "event",
        }
        return fallback.get(ctx, "menu")

    def _loading_step(self, label: str, pct: float):
        if not hasattr(self, "loading_screen"):
            return
        self.asset_generation_label = label
        self.asset_generation_progress = max(0.0, min(1.0, float(pct)))
        self.asset_generation_active = self.asset_generation_progress < 0.999
        self.loading_screen.set_step(label, pct)
        now = pygame.time.get_ticks()
        if not hasattr(self, "_loading_watch_ts"):
            self._loading_watch_ts = now
            self._loading_watch_label = label
        if label != getattr(self, "_loading_watch_label", ""):
            self._loading_watch_label = label
            self._loading_watch_ts = now
        elif now - getattr(self, "_loading_watch_ts", now) > 12000 and pct < 0.98:
            self.loading_screen.set_step("Continuando con placeholders…", pct)
        self.loading_screen.draw(self.renderer.internal, 1.0 / max(1, FPS))
        self.renderer.present()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False

    def _load_cards_data(self):
        cards = self.content.cards if isinstance(self.content.cards, list) and self.content.cards else load_json(data_dir() / "cards.json", default=[])
        cooked = []
        for c in cards if isinstance(cards, list) else []:
            if not isinstance(c, dict) or not c.get("id"):
                continue
            cooked.append({
                "id": c.get("id"),
                "name_key": c.get("name_es", c.get("name_key", c.get("id"))),
                "text_key": c.get("text_es", c.get("text_key", c.get("id"))),
                "rarity": c.get("rarity", "common"),
                "cost": int(c.get("cost", 1)),
                "target": c.get("target", "enemy"),
                "tags": list(c.get("tags", [])),
                "effects": list(c.get("effects", [])),
                "family": (c.get("direction", "ESTE") or "ESTE").lower(),
                "direction": c.get("direction", "ESTE"),
            })
        by_id = {c.get("id"): c for c in cooked if c.get("id")}
        if not by_id:
            for base in DEFAULT_CARDS:
                by_id.setdefault(base["id"], base)
        return list(by_id.values())

    def _load_enemies_data(self):
        enemies = self.content.enemies if isinstance(self.content.enemies, list) and self.content.enemies else load_json(data_dir() / "enemies.json", default=[DEFAULT_ENEMY])
        valid = []
        for e in enemies if isinstance(enemies, list) else []:
            if not isinstance(e, dict) or not e.get("id"):
                continue
            valid.append({
                "id": e.get("id"),
                "name_key": e.get("name_es", e.get("name_key", e.get("id"))),
                "hp": e.get("hp", [20, 20]),
                "pattern": e.get("pattern", [{"intent": "attack", "value": [5, 5]}]),
                "guard": int(e.get("guard", 0)),
                "fable_lesson_key": e.get("fable_lesson_key", "duda"),
                "tier": e.get("tier", "common"),
            })
        return valid or [DEFAULT_ENEMY]

    def _load_events_data(self):
        events = load_json(data_dir() / "events.json", default=[])
        return events if isinstance(events, list) else []

    def _load_relics_data(self):
        relics = load_json(data_dir() / "relics.json", default=[])
        return relics if isinstance(relics, list) else []

    def _load_design_doc(self):
        design_path = data_dir() / "design" / "gdd_chakana_purple_wizard.txt"
        data = {}
        raw = ""
        try:
            raw = design_path.read_text(encoding="utf-8")
        except Exception:
            return {"raw": "", "path": str(design_path)}
        for line in raw.splitlines():
            if "=" in line and line.strip() and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
        data["raw"] = raw
        data["path"] = str(design_path)
        return data

    def design_value(self, key: str, default: str = "") -> str:
        return self.design_doc.get(key, default)

    def _build_card_prompts_payload(self):
        payload = {"version": 1, "seed": 12345, "cards": {}}
        seen = set()
        for i, card in enumerate(self.cards_data):
            cid = str(card.get("id", f"card_{i}")).strip()
            if not cid:
                continue
            if cid in seen:
                print(f"[prompts] warning duplicate write attempt for card_id={cid}")
                continue
            seen.add(cid)
            tags = card.get("tags", []) or []
            ctype = "attack" if "attack" in tags else "defense" if ("block" in tags or "defense" in tags) else "control" if ("draw" in tags or "scry" in tags or "control" in tags) else "spirit"
            payload["cards"][cid] = {
                "prompt": f"chakana card::{cid}::{ctype} layered sacred geometry with glyph focus",
                "style": ctype,
                "updated_at": "1970-01-01T00:00:00Z",
            }
        return payload

    def _ensure_card_prompts_file(self, force: bool = False):
        prompts_path = self.data_root / "card_prompts.json"
        if prompts_path.exists() and not force:
            return
        payload = self._build_card_prompts_payload()
        atomic_write_json_if_changed(prompts_path, payload, sort_keys=True)

    def ensure_assets(self, progress_cb=None):
        regen_flag = (data_dir() / "regen_on_boot.flag").exists()
        force_regen = bool(self.user_settings.get("force_regen_art", False) or self.user_settings.get("update_manifests", False) or regen_flag)
        if not force_regen:
            print("[assets] normal boot: skipping autogen regeneration")
            return
        if regen_flag:
            self.user_settings["force_regen_art"] = True
        self._ensure_card_prompts_file(force=True)
        ensure_placeholder_assets([c.get("id", "strike") for c in self.cards_data], [e.get("id", "dummy") for e in self.enemies_data])
        content_payload = {
            "cards": self.cards_data,
            "enemies": self.enemies_data,
            "guide_types": GUIDE_TYPES,
        }
        try:
            ap = self.asset_pipeline.ensure_all_assets(self.user_settings, content_payload, progress_cb=progress_cb)
            if isinstance(ap, dict):
                self.debug["placeholders_used"] = int(ap.get("placeholders", 0))
        except Exception as exc:
            print(f"[safe_gen] using placeholder for pipeline due to {exc}")
            (assets_dir() / "sprites" / "cards" / "_placeholder.png").parent.mkdir(parents=True, exist_ok=True)
            surf = pygame.Surface((256, 384)); surf.fill((52, 36, 74)); pygame.image.save(surf, assets_dir() / "sprites" / "cards" / "_placeholder.png")


    def validate_navigation_methods(self):
        required = ["goto_menu", "goto_map", "goto_combat", "goto_reward", "goto_shop", "goto_event", "goto_deck", "goto_settings", "goto_end"]
        missing = [m for m in required if not hasattr(self, m)]
        if missing:
            raise RuntimeError(f"Missing navigation methods: {', '.join(missing)}")

    def toggle_language(self):
        self.loc.load("en" if self.loc.current_lang == "es" else "es")
        self.user_settings["language"] = self.loc.current_lang
        self.validate_navigation_methods()
        pygame.display.set_caption(self.loc.t("game_title"))

    def goto_menu(self):
        if self.sm.current and not isinstance(self.sm.current, MenuScreen):
            self.menu_return_screen = self.sm.current
        self.sm.set(MenuScreen(self))
        self.music.play_for(self.get_bgm_track("menu"))

    def goto_settings(self):
        self.sm.set(SettingsScreen(self))

    def goto_end(self, victory=True):
        title = "Victoria" if victory else "Derrota"
        lore = "el eco celebró tu equilibrio." if victory else "la Trama pidió un nuevo intento."
        self.sm.set(PachaTransitionScreen(self, title, lambda: self.sm.set(EndScreen(self, victory=victory)), lore_line=lore, hint="Cierre del capítulo"))

    def goto_path_select(self):
        self.sm.set(PathSelectScreen(self))

    def goto_deck(self):
        self.sm.set(DeckScreen(self))

    def new_run(self):
        self.goto_path_select()

    def start_run_with_deck(self, starter_deck):
        self.run_state = {
            "gold": 80,
            "relics": ["violet_seal"],
            "player": {"hp": 70, "max_hp": 70, "block": 0, "energy": 3, "rupture": 0, "statuses": {}},
            "deck": list(starter_deck),
            "sideboard": [],
            "map": self.generate_map(),
            "biome": self.rng.choice(["kaypacha", "forest", "umbral", "hanan"]),
            "xp": 0,
            "level": 1,
            "combats_won": 0,
            "settings": {
                "turn_timer_enabled": bool(self.user_settings.get("turn_timer_enabled", True)),
                "turn_timer_seconds": int(self.user_settings.get("turn_timer_seconds", 20)),
                "music_muted": bool(self.user_settings.get("music_muted", self.user_settings.get("music_mute", False))),
            },
        }
        self.goto_map()

    def generate_map(self):
        columns = 6
        by_col = []
        self.node_lookup = {}
        type_cycle = ["combat", "event", "challenge", "shop", "treasure", "boss"]
        x_margin = 140
        x_step = (INTERNAL_WIDTH - x_margin * 2) // (columns - 1)
        for col in range(columns):
            count = 1 if col in (0, columns - 1) else 3
            col_nodes = []
            for row in range(count):
                node_id = f"{col}_{row}"
                if count == 1:
                    y = INTERNAL_HEIGHT // 2
                else:
                    y = 240 + row * 190
                node_type = type_cycle[col]
                if node_type == "challenge" and self.rng.randint(0, 100) < 45:
                    node_type = "combat"
                node = {"id": node_id, "col": col, "x": x_margin + col * x_step, "y": y, "type": node_type, "next": [], "state": "available" if col == 0 else "locked"}
                col_nodes.append(node)
                self.node_lookup[node_id] = node
            by_col.append(col_nodes)
        for col in range(columns - 1):
            for i, node in enumerate(by_col[col]):
                next_nodes = by_col[col + 1]
                node["next"].append(next_nodes[min(i, len(next_nodes) - 1)]["id"])
                alt = self.rng.choice(next_nodes)
                if alt["id"] not in node["next"]:
                    node["next"].append(alt["id"])
        return by_col

    def goto_map(self):
        if self.run_state and self.run_state.get("levelup_pending", 0) > 0:
            self.sm.set(PackOpeningScreen(self))
            self.music.play_for("chest")
            return
        self.debug["map_available_count"] = self.available_nodes_count() if self.node_lookup else 0
        self.debug["current_node_id"] = self.current_node_id or "-"
        biome_track = self.run_state.get("biome", "kaypacha") if self.run_state else "kaypacha"
        if self.last_biome_seen is None:
            self.last_biome_seen = biome_track
            self.sm.set(PachaTransitionScreen(self, "Comienza la Trama", lambda: self.sm.set(MapScreen(self)), lore_line="Chakana abrió su primer sendero.", hint="Pulsa cualquier tecla para caminar"))
        elif self.last_biome_seen != biome_track:
            self.last_biome_seen = biome_track
            self.sm.set(PachaTransitionScreen(self, f"Mapa: {str(biome_track).title()}", lambda: self.sm.set(MapScreen(self)), lore_line="un nuevo territorio abrió su geometría.", hint="Pulsa cualquier tecla para continuar"))
        else:
            self.sm.set(MapScreen(self))
        self.music.play_for(self.get_bgm_track("map", biome_track))

    def goto_combat(self, combat_state, is_boss=False):
        self.current_combat = combat_state
        try:
            pc = combat_state.pile_counts() if hasattr(combat_state, "pile_counts") else {"draw": 0, "hand": len(getattr(combat_state, "hand", []) or []), "discard": 0}
            print(f"[boot] combat_engine piles: draw={pc.get('draw',0)} hand={pc.get('hand',0)} discard={pc.get('discard',0)}")
        except Exception:
            pass

        def _enter_combat():
            self.sm.set(CombatScreen(self, combat_state, is_boss=is_boss))
            if is_boss:
                self.music.play_for(self.get_bgm_track("boss"))
            else:
                biome_track = self.run_state.get("biome", "kaypacha") if self.run_state else "kaypacha"
                self.music.play_for(self.get_bgm_track("combat", biome_track))

        title = "Umbral del Jefe" if is_boss else "Entrando en Combate"
        lore = "la sombra mayor despertó." if is_boss else "el pulso enemigo se hizo audible."
        self.sm.set(PachaTransitionScreen(self, title, _enter_combat, lore_line=lore, hint="Pulsa cualquier tecla para preparar tu mano"))

    def goto_reward(self, picks=None, gold=None, mode=None, relic=None, guide_reward=None):
        reward_mode = mode or "choose1of3"
        if reward_mode == "guide_choice":
            reward_data = guide_reward or build_reward_guide("guide", self.rng, self.cards_data, self.run_state or {})
            reward_data["type"] = "guide_choice"
            self.sm.set(RewardScreen(self, reward_data, gold=0, xp_gained=self.debug.get("xp_last_gain", 0)))
            self.music.play_for(self.get_bgm_track("events"))
            return

        if reward_mode == "boss_pack":
            reward_data = build_reward_boss(self.rng, self.cards_data, self.relics_data, self.run_state or {})
            if relic is not None:
                reward_data["relic"] = relic
            reward_data["type"] = "boss_pack"
            self.sm.set(RewardScreen(self, reward_data, gold=gold or 0, xp_gained=self.debug.get("xp_last_gain", 0)))
            self.music.play_for("victory")
            return

        if picks is None:
            unlock_level = self.run_state.get("level", 1) if self.run_state else 1
            rarities = {"basic", "common"} if unlock_level < 2 else {"common", "uncommon", "rare"}
            pool = [c for c in self.cards_data if c.get("rarity") in rarities] or self.cards_data
            reward_data = build_reward_normal(self.rng, pool, self.run_state or {})
        else:
            reward_data = {"type": "choose1of3", "cards": list(picks)}
        if gold is None:
            gold = self.rng.randint(10, 25)

        self.sm.set(RewardScreen(self, reward_data, gold, xp_gained=self.debug.get("xp_last_gain", 0)))
        self.music.play_for("victory")

    def goto_shop(self):
        pool = [c for c in self.cards_data if c.get("rarity") in {"common", "uncommon"}] or self.cards_data
        self.sm.set(ShopScreen(self, self.rng.choice(pool) or DEFAULT_CARDS[0]))
        self.music.play_for(self.get_bgm_track("events"))

    def goto_event(self):
        event = self.rng.choice(self.events_data) if self.events_data else {"title_key": "map_title", "body_key": "lore_tagline", "choices": [{"text_key": "event_continue", "effects": []}]}
        self.sm.set(EventScreen(self, event))
        self.music.play_for(self.get_bgm_track("events"))

    def goto_guide_reward(self, event_id: str = "guide"):
        reward_data = build_reward_guide(event_id, self.rng, self.cards_data, self.run_state or {})
        self.goto_reward(mode="guide_choice", guide_reward=reward_data)

    def run_qa_mode(self):
        results = QARunner(self).run_all()
        self.sm.set(QAResultsScreen(self, results))

    def run_qa_scripted_mode(self):
        results = QARunner(self).run_combat_scripted_smoke()
        self.sm.set(QAResultsScreen(self, results))

    def select_map_node(self, node):
        self.current_node_id = node["id"]
        node["state"] = "current"
        self.debug["current_node_id"] = self.current_node_id
        self.debug["next_nodes_ids"] = ",".join(node.get("next", [])) if node.get("next") else "-"
        self.enter_node(node)

    def _complete_current_node(self):
        if not self.current_node_id:
            return []
        node = self.node_lookup.get(self.current_node_id)
        if not node:
            return []
        node["state"] = "cleared"
        unlocked = []
        for next_id in node.get("next", []):
            nxt = self.node_lookup.get(next_id)
            if nxt and nxt["state"] == "locked":
                nxt["state"] = "available"
                unlocked.append(nxt["id"])
        if node.get("type") in {"combat", "challenge"}:
            extra = self._unlock_optional_challenge(node)
            if extra:
                unlocked.append(extra)
        if self.available_nodes_count() <= 0:
            unlocked.extend(self._fallback_unlock_next_column(node))
        self.debug["next_nodes_ids"] = ",".join(unlocked) if unlocked else "-"
        self.debug["map_available_count"] = self.available_nodes_count()
        return unlocked

    def _unlock_optional_challenge(self, node):
        target_col = min(node.get("col", 0) + 1, max(n.get("col", 0) for n in self.node_lookup.values()))
        candidates = [n for n in self.node_lookup.values() if n.get("col") == target_col and n.get("state") == "locked"]
        if not candidates:
            return None
        chosen = self.rng.choice(candidates)
        chosen["state"] = "available"
        if chosen.get("type") == "combat":
            chosen["type"] = "challenge"
        return chosen["id"]

    def _fallback_unlock_next_column(self, node):
        target_col = node.get("col", 0) + 1
        candidates = [n for n in self.node_lookup.values() if n.get("col") == target_col and n.get("state") == "locked"]
        if not candidates:
            return []
        candidates[0]["state"] = "available"
        return [candidates[0]["id"]]

    def available_nodes_count(self):
        return sum(1 for n in self.node_lookup.values() if n.get("state") == "available")

    def _enemy_pool(self, node=None):
        commons = [e["id"] for e in self.enemies_data if e.get("id") and e.get("tier", "common") == "common"]
        elites = [e["id"] for e in self.enemies_data if e.get("id") and e.get("tier") == "elite"]
        commons = commons or [DEFAULT_ENEMY["id"]]
        pivot = max(1, len(commons) // 2)
        tier1 = commons[:pivot]
        tier2 = commons[pivot:] or commons
        col = int((node or {}).get("col", 0))
        if col <= 1:
            pool = tier1
        elif col <= 3:
            pool = tier1 + tier2
        else:
            pool = tier2 + elites
        return pool or commons

    def enter_node(self, node):
        node_type = node.get("type", "combat")
        if node_type in {"combat", "challenge", "boss"}:
            boss_ids = [b.get("id") for b in self.content.bosses if isinstance(b, dict) and b.get("id")]
            enemy_ids = [self.rng.choice(boss_ids)] if node_type == "boss" and boss_ids else [self.rng.choice(self._enemy_pool(node))]
            self.run_state["last_node_type"] = node_type
            base_state = CombatState(self.rng, self.run_state, enemy_ids, cards_data=self.cards_data, enemies_data=self.enemies_data)
            early = int(self.run_state.get("combats_won", 0)) < 2 and node_type != "boss"
            if early:
                for e in base_state.enemies:
                    e.max_hp = int(max(10, e.max_hp * 0.82)); e.hp = min(e.hp, e.max_hp)
                    for pat in getattr(e, "pattern", []) or []:
                        val = pat.get("value")
                        if isinstance(val, list) and val:
                            pat["value"] = [max(1, int(v) - 1) for v in val]
            self.current_combat = CombatEngine(base_state)
            self.goto_combat(self.current_combat, is_boss=node_type == "boss")
        elif node_type == "shop":
            self.goto_shop()
        elif node_type == "treasure":
            self._complete_current_node()
            self.goto_reward(gold=self.rng.randint(22, 40))
        else:
            self.goto_event()

    def gain_xp(self, amount: int):
        levels = 0
        self.debug["xp_last_gain"] = max(0, int(amount))
        self.run_state["xp"] += amount
        needed = self.run_state["level"] * 20
        while self.run_state["xp"] >= needed:
            self.run_state["xp"] -= needed
            self.run_state["level"] += 1
            levels += 1
            needed = self.run_state["level"] * 20
        if levels:
            self.run_state["levelup_pending"] = self.run_state.get("levelup_pending", 0) + levels
        return levels

    def on_combat_victory(self):
        self._complete_current_node()
        node_type = self.run_state.get("last_node_type", "combat")
        if node_type == "boss":
            self.goto_reward(mode="boss_pack", gold=self.rng.randint(40, 70))
            return
        self.run_state["combats_won"] = int(self.run_state.get("combats_won", 0)) + 1
        bonus_gold = self.rng.randint(16, 30) if node_type == "challenge" else self.rng.randint(10, 25)
        difficulty_bonus = {"combat": 2, "challenge": 5, "boss": 12}.get(node_type, 2)
        perfect_bonus = 5 if self.current_combat and getattr(self.current_combat, "player_damage_taken", 0) <= 0 else 0
        self.gain_xp(10 + difficulty_bonus + perfect_bonus)
        enemy = self.current_combat.enemies[0] if self.current_combat and self.current_combat.enemies else None
        self.debug["last_lesson_key"] = getattr(enemy, "fable_lesson_key", "duda") if enemy else "duda"
        self.goto_reward(gold=bonus_gold)


    def consume_levelup_pending(self):
        pending = self.run_state.get("levelup_pending", 0)
        if pending > 0:
            self.run_state["levelup_pending"] = pending - 1
        if self.run_state.get("levelup_pending", 0) > 0:
            self.sm.set(PackOpeningScreen(self))
        else:
            self.goto_map()

    def apply_event_effects(self, effects):
        player = self.run_state["player"]
        rare = any(e.get("type") == "gain_relic" for e in effects)
        self.gain_xp(self.rng.randint(7, 8) if rare else self.rng.randint(4, 6))
        for effect in effects:
            effect_type = effect.get("type")
            if effect_type == "lose_gold":
                self.run_state["gold"] = max(0, self.run_state["gold"] - int(effect.get("amount", 0)))
            elif effect_type == "gain_gold":
                self.run_state["gold"] += int(effect.get("amount", 0))
            elif effect_type == "heal":
                player["hp"] = min(player["max_hp"], player["hp"] + int(effect.get("amount", 0)))
            elif effect_type == "lose_hp":
                player["hp"] = max(1, player["hp"] - int(effect.get("amount", 0)))
            elif effect_type == "gain_max_hp":
                amount = int(effect.get("amount", 0)); player["max_hp"] += amount; player["hp"] += amount
            elif effect_type == "gain_rupture":
                player["rupture"] += int(effect.get("amount", 0))
            elif effect_type == "reduce_rupture":
                player["rupture"] = max(0, player["rupture"] - int(effect.get("amount", 0)))
            elif effect_type == "gain_card":
                self.run_state["sideboard"].append(effect.get("card_id", "strike"))
            elif effect_type == "gain_card_random":
                rarity = effect.get("rarity")
                pool = [c.get("id") for c in self.cards_data if c.get("rarity") == rarity and c.get("id")]
                if pool:
                    self.run_state["sideboard"].append(self.rng.choice(pool))
            elif effect_type == "remove_card_from_deck" and self.run_state["deck"]:
                self.run_state["deck"].pop(0)
            elif effect_type == "gain_relic":
                rid = effect.get("relic_id")
                if rid:
                    self.run_state["relics"].append(rid)
            elif effect_type == "gain_relic_random":
                rarity = effect.get("rarity")
                pool = [r.get("id") for r in self.relics_data if r.get("rarity") == rarity and r.get("id")]
                if pool:
                    self.run_state["relics"].append(self.rng.choice(pool))
            else:
                print(f"[events] warning: unsupported effect type '{effect_type}'")


    def recover_map_progression(self):
        if not self.run_state:
            return
        if self.available_nodes_count() > 0:
            return
        node = self.node_lookup.get(self.current_node_id) if self.current_node_id else None
        if node:
            unlocked = self._fallback_unlock_next_column(node)
            if unlocked:
                print("[map] recovery unlocked next column node", unlocked)
                return
        for n in self.node_lookup.values():
            if n.get("state") != "cleared":
                n["state"] = "available"
                print("[map] recovery unlocked unfinished node", n.get("id"))
                return
        node_id = f"recovery_{len(self.node_lookup)}"
        new_node = {"id": node_id, "col": 0, "x": INTERNAL_WIDTH // 2, "y": INTERNAL_HEIGHT // 2, "type": "event", "next": [], "state": "available"}
        self.node_lookup[node_id] = new_node
        self.run_state["map"].append([new_node])
        print("[map] recovery created Camino Abierto")

    def _draw_progress_splash(self, title: str, detail: str):
        self.renderer.internal.fill((10, 8, 22))
        self.renderer.internal.blit(self.big_font.render(title, True, (234, 210, 126)), (640, 460))
        self.renderer.internal.blit(self.font.render(detail, True, (230, 230, 236)), (640, 520))
        self.renderer.present()

    def _apply_dev_reset_if_enabled(self):
        regen_flag = data_dir() / "regen_on_boot.flag"
        if self.user_settings.get("dev_reset_autogen_on_boot", False) or regen_flag.exists():
            self.user_settings["force_regen_art"] = True
            if regen_flag.exists():
                try:
                    regen_flag.unlink()
                except Exception:
                    pass
            self.user_settings["dev_reset_autogen_on_boot"] = False
            self.user_settings["force_regen_art"] = True
            save_settings(self.user_settings)

    def reset_autogen_total(self, mark_only: bool = True, delete_now: bool = False):
        regen_flag = data_dir() / "regen_on_boot.flag"
        if mark_only or not delete_now:
            regen_flag.write_text(str(int(time.time())), encoding="utf-8")
            for p in [data_dir() / "art_manifest.json", data_dir() / "art_manifest_cards.json", data_dir() / "art_manifest_enemies.json", data_dir() / "art_manifest_guides.json", data_dir() / "art_manifest_avatar.json", data_dir() / "audio_manifest.json", data_dir() / "biome_manifest.json", data_dir() / "bgm_manifest.json", data_dir() / "prompt_manifest.json", data_dir() / "card_prompts.json"]:
                try:
                    if p.exists(): p.unlink()
                except Exception:
                    pass
            self._loading_step("Reset aplicado. Reiniciando…", 0.15)
            self.request_restart("regen")
            return

        self._draw_progress_splash("Regenerando Trama…", "Reset Autogen Total")
        try:
            pygame.mixer.music.stop(); pygame.mixer.stop()
            if hasattr(pygame.mixer.music, "unload"):
                try: pygame.mixer.music.unload()
                except Exception: pass
            pygame.mixer.quit()
        except Exception:
            pass
        targets = [assets_dir() / "sprites" / "cards", assets_dir() / "sprites" / "enemies", assets_dir() / "sprites" / "biomes", assets_dir() / "sprites" / "guides", assets_dir() / "music", assets_dir() / "sfx" / "generated"]
        for td in targets:
            if td.exists():
                for f in td.rglob("*"):
                    if not f.is_file():
                        continue
                    try:
                        f.unlink()
                    except PermissionError:
                        pend = f.with_suffix(f.suffix + ".delete_pending")
                        try:
                            f.rename(pend)
                            print(f"[reset] locked file -> renamed pending: {f}")
                        except Exception:
                            pass
                    except Exception:
                        pass
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass

    def regenerate_art_missing(self):
        self.user_settings["force_regen_art"] = False
        self.user_settings["update_manifests"] = True
        self.ensure_assets(progress_cb=self._loading_step)
        self.user_settings["update_manifests"] = False
        self.asset_generation_active = False
        self.assets._cache.clear()

    def regenerate_art_all(self):
        self.user_settings["force_regen_art"] = True
        self.user_settings["update_manifests"] = True
        self.ensure_assets(progress_cb=self._loading_step)
        self.user_settings["update_manifests"] = False
        self.asset_generation_active = False
        self.assets._cache.clear()

    def regenerate_music(self):
        try:
            pygame.mixer.music.stop()
            if hasattr(pygame.mixer.music, "unload"):
                pygame.mixer.music.unload()
        except Exception:
            pass
        try:
            pygame.mixer.stop()
            pygame.mixer.quit()
        except Exception:
            pass
        self.user_settings["force_regen_music"] = True
        self.user_settings["update_manifests"] = True
        self.audio_pipeline.ensure_music_assets(self.user_settings, progress_cb=self._loading_step)
        self.user_settings["force_regen_music"] = False
        self.user_settings["update_manifests"] = False
        self.music._manifest = self.music._load_manifest()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass
        self.music = MusicManager()
        self.music.set_volume(self.user_settings.get("music_volume", 0.5))
        self.music.set_muted(self.user_settings.get("music_muted", self.user_settings.get("music_mute", False)))
        self.music._checked_silence.clear()
        self.music.play_for(self.get_bgm_track("menu"))

    def regenerate_card_art_with_cleanup(self):
        manifest_path = data_dir() / "art_manifest.json"
        manifest = load_json(manifest_path, default={})
        cards_dir = assets_dir() / "sprites" / "cards"
        if isinstance(manifest, dict):
            items = manifest.get("items", manifest) if isinstance(manifest.get("items", {}), dict) else manifest
            for cid in items.keys():
                p = cards_dir / f"{cid}.png"
                if p.exists():
                    p.unlink()
        self.regenerate_card_art()

    def set_debug(self, **kwargs):
        self.debug.update(kwargs)

    def regenerate_card_art(self):
        total = len(self.cards_data)
        manifest = {"generator_version": GEN_ART_VERSION, "created_at": time.strftime("%Y-%m-%d %H:%M:%S"), "items": {}}
        for i, c in enumerate(self.cards_data, start=1):
            cid = c.get("id", "strike")
            self.art_gen.ensure_art(cid, c.get("tags", []), c.get("rarity", "common"), "force_regen")
            manifest["items"][cid] = {
                "prompt_hash": str(abs(hash(cid))),
                "generated_at": int(time.time()),
                "seed": str(abs(hash(cid)) % 1000000),
            }
            self.set_debug(last_ui_event=f"regen_art:{i}/{total}")
        atomic_write_json(data_dir() / "art_manifest.json", manifest)
        self.assets._cache.clear()

    def save_user_settings(self):
        self.user_settings["sfx_volume"] = self.sfx.master_volume
        self.user_settings["music_volume"] = self.music.volume
        self.user_settings["music_muted"] = self.music.muted
        self.user_settings["music_mute"] = self.music.muted
        self.user_settings["fullscreen"] = self.renderer.fullscreen
        self.user_settings["autogen_art_mode"] = self.user_settings.get("autogen_art_mode", "missing_only")
        self.user_settings["turn_timer_enabled"] = self.user_settings.get("turn_timer_enabled", True)
        self.user_settings["turn_timer_seconds"] = int(self.user_settings.get("turn_timer_seconds", 20))
        self.user_settings["dev_reset_autogen_on_boot"] = bool(self.user_settings.get("dev_reset_autogen_on_boot", False))
        self.user_settings["fx_vignette"] = bool(self.user_settings.get("fx_vignette", True))
        self.user_settings["fx_scanlines"] = bool(self.user_settings.get("fx_scanlines", False))
        self.user_settings["fx_glow"] = bool(self.user_settings.get("fx_glow", True))
        self.user_settings["fx_particles"] = bool(self.user_settings.get("fx_particles", True))
        self.user_settings["force_regen_art"] = bool(self.user_settings.get("force_regen_art", False))
        self.user_settings["detail_panel"] = bool(self.user_settings.get("detail_panel", False))
        save_settings(self.user_settings)

    def draw_debug_overlay(self):
        if not self.debug_overlay:
            return
        x,y,nw,nh,scale = self.renderer._viewport()
        counts = self.content.debug_counts() if hasattr(self, "content") else {}
        ok_cards = f"OK({counts.get('cards',0)})" if counts.get('cards',0)==60 else f"FALLBACK({counts.get('cards',0)})"
        ok_enemies = f"OK({counts.get('enemies',0)})" if counts.get('enemies',0)==30 else f"FALLBACK({counts.get('enemies',0)})"
        ok_boss = f"OK({counts.get('bosses',0)})" if counts.get('bosses',0)==3 else f"FALLBACK({counts.get('bosses',0)})"
        dlgc = "OK" if counts.get('dialogues_combat') else "MISSING"
        dlge = "OK" if counts.get('dialogues_events') else "MISSING"
        biome_on = "ON" if self.user_settings.get("fx_particles", True) else "OFF"
        current_biome = getattr(self.sm.current, "selected_biome", "-") if self.sm.current else "-"
        lines = [
            f"screen={self.sm.current.__class__.__name__ if self.sm.current else '-'}",
            f"Cards: {ok_cards}  Enemies: {ok_enemies}  Bosses: {ok_boss}",
            f"DialoguesCombat: {dlgc}  DialoguesEvents: {dlge}",
            f"ContentStatus={self.debug.get('content_status','-')}",
            f"BiomeLayers: {biome_on}  CurrentBiome: {current_biome}",
            f"Version: v{VERSION}",
            f"BGM {self.music.debug_state()}",
            f"LoreStatus={self.debug.get('lore_status','-')} paths={self.debug.get('lore_paths','-')}",
            f"map.available_count={self.debug.get('map_available_count','-')} current_node_id={self.debug.get('current_node_id','-')}",
            f"next_nodes={self.debug.get('next_nodes_ids','-')}",
        ]
        panel = pygame.Surface((1200, 230), pygame.SRCALPHA)
        panel.fill((0,0,0,170))
        self.renderer.internal.blit(panel, (8,8))
        for i,line in enumerate(lines):
            self.renderer.internal.blit(self.tiny_font.render(line, True, (240,240,240)), (16, 16+i*20))


    def request_restart(self, reason="regen"):
        self._restart_requested = True
        self._restart_reason = reason

    def _soft_restart(self):
        self._loading_step("Reset aplicado. Regenerando Trama…", 0.02)
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        pygame.event.clear()
        self.assets._cache.clear()
        self.sfx = SFXManager()
        self.music = MusicManager()
        self.music.set_volume(self.user_settings.get("music_volume", 0.5))
        self.music.set_muted(self.user_settings.get("music_muted", self.user_settings.get("music_mute", False)))
        content_payload = ContentService().load_all(progress_cb=self._loading_step)
        self.content.cards = content_payload.get("cards", [])
        self.content.enemies = content_payload.get("enemies", [])
        self.content.bosses = content_payload.get("bosses", [])
        self.content.dialogues_combat = content_payload.get("dialogues_combat", {})
        self.content.dialogues_events = content_payload.get("dialogues_events", {})
        self.lore_engine.load_all()
        self.biomes_lore = self._load_biomes_lore_data()
        self.cards_data = self._load_cards_data()
        self.card_defs = {c["id"]: c for c in self.cards_data}
        self.enemies_data = self._load_enemies_data()
        self.ensure_assets(progress_cb=self._loading_step)
        self._log_card_art_status()
        content_report = validate_content(self.cards_data, assets_dir())
        self.debug["content_validation"] = content_report
        print(f"[boot] validate_content status={content_report.get('status')} cards={content_report.get('cards')} summary_ok={content_report.get('summary_ok')} can_play_ok={content_report.get('can_play_ok')} placeholders={content_report.get('placeholders')} issues={len(content_report.get('issues', []))}")
        self.audio_pipeline.ensure_music_assets(self.user_settings, progress_cb=self._loading_step)
        self.sm.set(IntroScreen(self))
        self.music.play_for(self.get_bgm_track("menu"))
        self.asset_generation_active = False

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.renderer.toggle_fullscreen()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                    self.toggle_language()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
                    self.debug_overlay = not self.debug_overlay
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F10:
                    self.run_qa_mode()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F8:
                    self.run_qa_scripted_mode()
                else:
                    self.sm.handle_event(event)
            if self._restart_requested:
                self._restart_requested = False
                self._soft_restart()
                continue
            self.music.tick()
            self.sm.update(dt)
            self.renderer.internal.fill((8, 8, 14))
            self.sm.render(self.renderer.internal)
            self.draw_debug_overlay()
            self.renderer.present()
        pygame.quit()


if __name__ == "__main__":
    app = None
    try:
        cli_force_manifests = "--regen-manifests" in set(sys.argv[1:])
        app = App()
        if cli_force_manifests:
            app.user_settings["force_regen_art"] = True
            app.user_settings["force_regen_music"] = True
            app.user_settings["update_manifests"] = True
            app.ensure_assets(progress_cb=app._loading_step)
            app.audio_pipeline.ensure_music_assets(app.user_settings, progress_cb=app._loading_step)
            app.user_settings["update_manifests"] = False
            app.user_settings["force_regen_music"] = False
        app.run()
    except Exception:
        trace = traceback.format_exc()
        print(trace)
        if app is not None:
            try:
                app.sm.set(ErrorScreen(app, trace.splitlines()))
                for _ in range(240):
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            raise
                        app.sm.handle_event(event)
                    app.sm.update(1 / FPS)
                    app.sm.render(app.renderer.internal)
                    app.renderer.present()
                    app.clock.tick(FPS)
            except Exception:
                pass
        raise
