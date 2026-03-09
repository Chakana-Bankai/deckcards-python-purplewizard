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
from game.core.save import load_run, save_run, clear_run
from game.core.state_machine import StateMachine
from game.settings import FPS, INTERNAL_HEIGHT, INTERNAL_WIDTH
from game.qa.runner import QARunner
from game.qa.content_validator import validate_content
from game.ui.render import AssetManager, Renderer
from game.ui.screens.combat import CombatScreen
from game.ui.screens.codex import CodexScreen
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
from game.ui.screens.studio_intro import StudioIntroScreen
from game.ui.screens.pacha_transition import PachaTransitionScreen
from game.ui.screens.tutorial import TutorialScreen
from game.ui.tutorial_flow import TutorialFlowController
from game.ui.components.card_effect_summary import infer_card_role
from game.ui.components.holographic_oracle import HolographicOracleUI
from game.ui.system.typography import ChakanaTypography, SMALL_FONT
from game.version import VERSION
from game.art.gen_art32 import GEN_ART_VERSION, GEN_BIOME_VERSION
from game.services.content_service import ContentService
from game.services.asset_pipeline import AssetPipeline
from game.services.audio_pipeline import AudioPipeline
from game.services.archetype_distribution import enforce_archetype_rarity_distribution
from game.visual import get_visual_engine
from game.systems.reward_system import build_reward_boss, build_reward_guide, build_reward_normal
from game.ui.screens.loading import LoadingScreen, DataLoadingScreen

DEFAULT_CARDS = [
    {"id": "strike", "name_key": "card_strike_name", "text_key": "card_strike_desc", "rarity": "basic", "cost": 1, "target": "enemy", "tags": ["attack"], "effects": [{"type": "damage", "amount": 6}]},
    {"id": "defend", "name_key": "card_defend_name", "text_key": "card_defend_desc", "rarity": "basic", "cost": 1, "target": "self", "tags": ["skill"], "effects": [{"type": "block", "amount": 5}]},
]
DEFAULT_ENEMY = {"id": "dummy", "name_key": "enemy_voidling_name", "hp": [20, 20], "pattern": [{"intent": "attack", "value": [5, 5]}]}

MAP_TEMPLATE = [
    {"type": "combat", "count": 1, "types": ["combat"]},
    {"type": "branch", "count": 4, "types": ["event", "combat", "combat", "sanctuary"]},
    {"type": "branch", "count": 4, "types": ["combat", "shop", "combat", "event"]},
    {"type": "branch", "count": 4, "types": ["challenge", "combat", "relic", "combat"]},
    {"type": "merge", "count": 2, "types": ["combat", "elite"]},
    {"type": "boss", "count": 1, "types": ["boss"]},
]

SEVEN_PATHS = [
    {"id": "camino_filo", "title": "Camino del Filo", "lore": "Golpea primero; corta la duda."},
    {"id": "camino_velo", "title": "Camino del Velo", "lore": "Protege tu pulso antes del rito."},
    {"id": "camino_eco", "title": "Camino del Eco", "lore": "Toda jugada vuelve con nueva forma."},
    {"id": "camino_pulso", "title": "Camino del Pulso", "lore": "La energia obedece a quien respira."},
    {"id": "camino_umbral", "title": "Camino del Umbral", "lore": "Cruza limites para obtener vision."},
    {"id": "camino_cielo", "title": "Camino del Cielo", "lore": "La armonia alta revela rutas ocultas."},
    {"id": "camino_sello", "title": "Camino del Sello", "lore": "El sello despierta con voluntad pura."},
]

POST_COMBAT_HEAL = {"combat": 0.15, "challenge": 0.12, "boss": 0.10}
MAX_LEVEL = 20


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
        self.user_settings.setdefault("dev_skip_intro", False)
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
        self.typography = ChakanaTypography()
        self.typography.apply_to_app(self)
        self.mono_font = self.typography.get(SMALL_FONT, 22)
        self.sm = StateMachine()
        self.run_state = None
        self.current_combat = None
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

        self.loading_screen = LoadingScreen(self.big_font, self.font, lang=self.user_settings.get("language", "es"))
        self.content = SimpleNamespace(cards=[], enemies=[], bosses=[], dialogues_combat={}, dialogues_events={}, status="PENDING", errors=[])
        self.content.debug_counts = lambda: {
            "cards": len(self.content.cards),
            "enemies": len(self.content.enemies),
            "bosses": len(self.content.bosses),
            "dialogues_combat": bool(self.content.dialogues_combat),
            "dialogues_events": bool(self.content.dialogues_events),
        }
        self.debug["content_status"] = "PENDING"
        self.debug["art_status"] = "PENDING"
        self.debug["music_status"] = "PENDING"
        self.debug["biome_status"] = "PENDING"
        self._content_validation_cache_key = None
        self._content_validation_cache_result = None
        self.debug["last_regen_ts"] = int(time.time())
        self.cards_data = []
        self.card_defs = {}
        self.enemies_data = []
        self.events_data = []
        self.relics_data = []
        self.lore_service = LoreService()
        self.lore_engine = LoreEngine((data_dir().parent).parent)
        self.biomes_lore = {}
        self.biome_defs = []
        self.biome_def_by_id = {}
        self.lore_data = {}
        self.debug["lore_status"] = "PENDING"
        self.debug["lore_paths"] = ""
        self.design_doc = {"raw": "", "path": str(data_dir() / "design" / "gdd_chakana_purple_wizard.txt")}
        self.canonical_design_source = str(data_dir() / "design" / "gdd_chakana_purple_wizard.txt")
        self.art_gen = CardArtGenerator()
        self.enemy_art_gen = EnemyArtGenerator()
        self.bg_gen = BackgroundGenerator()
        self.guide_gen = GuideAvatarGenerator()
        self.asset_pipeline = AssetPipeline(self.art_gen, self.enemy_art_gen, self.guide_gen, self.bg_gen)
        self.audio_pipeline = AudioPipeline()
        self.visual_engine = get_visual_engine()
        self.oracle_ui = HolographicOracleUI()
        self._oracle_last_ms = 0
        self._oracle_last_by_trigger = {}
        self._oracle_active_priority = -1
        self._oracle_active_until_ms = 0
        self.autogen_art_mode = self.user_settings.get("autogen_art_mode", "missing_only")
        self.user_settings.setdefault("detail_panel", False)
        self.user_settings.setdefault("tutorial_completed", False)
        self.pending_tutorial_enabled = False
        self.story_intro_seen = False
        self.tutorial_flow = TutorialFlowController()
        self._boot_content_ready = False

        self.validate_navigation_methods()
        pygame.display.set_caption(self.loc.t("game_title"))
        self._set_boot_screen()

    def _set_boot_screen(self):
        loading_to_menu = lambda: self.sm.set(DataLoadingScreen(self, next_fn=self.goto_menu))
        skip_intro = self.user_settings.get("dev_skip_intro", False) is True
        if skip_intro:
            loading_to_menu()
            return
        self.sm.set(StudioIntroScreen(self, next_fn=loading_to_menu, fade_in=1.2, hold=1.5, fade_out=1.2))

    def ensure_boot_content_ready(self):
        if getattr(self, "_boot_content_ready", False):
            return

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
            content_lock=content_payload.get("content_lock", {}),
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
        self.cards_data = self._load_cards_data()
        self.card_defs = {c["id"]: c for c in self.cards_data}
        self.enemies_data = self._load_enemies_data()
        self.events_data = self._load_events_data()
        self.relics_data = self._load_relics_data()
        self.lore_service = LoreService()
        self.lore_engine = LoreEngine((data_dir().parent).parent)
        self.biomes_lore = self._load_biomes_lore_data()
        self.biome_defs = self._load_biome_defs()
        self.biome_def_by_id = {str(b.get("id")).lower(): b for b in self.biome_defs if isinstance(b, dict) and b.get("id")}
        self.lore_data = self.lore_service.data
        self.debug["lore_status"] = self.lore_service.status
        self.debug["lore_paths"] = ",".join(str(v) for v in self.lore_service.paths.values())
        self.design_doc = self._load_design_doc()

        print(f"[boot] content OK cards={len(self.cards_data)} enemies={len(self.enemies_data)} events={len(self.events_data)} relics={len(self.relics_data)}")
        lock = self.content.content_lock if isinstance(getattr(self.content, "content_lock", {}), dict) else {}
        if lock:
            print(f"[boot] content_lock status={lock.get('status', 'OK')} issues={len(lock.get('issues', []))} warnings={len(lock.get('warnings', []))}")
        self._apply_dev_reset_if_enabled()
        self.ensure_assets(progress_cb=self._loading_step)
        self._log_card_art_status()
        content_report = self._validate_content_cached()
        self.debug["content_validation"] = content_report
        print(f"[boot] validate_content status={content_report.get('status')} cards={content_report.get('cards')} summary_ok={content_report.get('summary_ok')} can_play_ok={content_report.get('can_play_ok')} placeholders={content_report.get('placeholders')} issues={len(content_report.get('issues', []))}")
        self.audio_pipeline.ensure_music_assets(self.user_settings, progress_cb=self._loading_step)
        self.visual_engine.ensure_core(force=bool(self.user_settings.get("force_regen_art", False)))
        self._loading_step("Completado", 1.0)
        dk = int(getattr(self.lore_engine, "keys_count", 0))
        covered = len([e for e in self.enemies_data if isinstance(self.lore_engine.combat_dialogues.get(e.get("id"), {}), dict)]) if isinstance(self.lore_engine.combat_dialogues, dict) else 0
        print(f"[load] dialogues_combat keys={dk} enemies_covered={covered}/{len(self.enemies_data)}")
        print(f"[boot] dialogues OK keys={dk}")
        print("[boot] assets OK")
        print(f"[boot] placeholders used: {self.debug.get('placeholders_used',0)}")
        self.debug["art_regenerated"] = self.art_gen.generated_count + self.art_gen.replaced_count
        self._try_restore_run_from_save()
        self._boot_content_ready = True
        self.music.play_for(self.get_bgm_track("menu"))

    def _validate_content_cached(self):
        key = tuple(
            (
                str(c.get("id", "")),
                int(c.get("cost", 0) or 0),
                str(c.get("rarity", "")),
                len(list(c.get("effects", []) or [])),
            )
            for c in (self.cards_data or [])
            if isinstance(c, dict)
        )
        if self._content_validation_cache_key == key and isinstance(self._content_validation_cache_result, dict):
            return dict(self._content_validation_cache_result)

        report = validate_content(self.cards_data, assets_dir())
        self._content_validation_cache_key = key
        self._content_validation_cache_result = dict(report)
        return report

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

    def _load_biome_defs(self) -> list[dict]:
        path = data_dir() / "biomes.json"
        payload = load_json(path, default=[])
        out = []
        for b in payload if isinstance(payload, list) else []:
            if not isinstance(b, dict):
                continue
            biome_id = str(b.get("id", "")).strip().lower()
            if not biome_id:
                continue
            out.append({
                "id": biome_id,
                "name": b.get("name", biome_id.title()),
                "description": b.get("description", ""),
                "background": b.get("background", biome_id),
                "enemy_pool": list(b.get("enemy_pool", [])),
                "event_pool": list(b.get("event_pool", [])),
                "boss": b.get("boss"),
                "atmosphere_tags": list(b.get("atmosphere_tags", [])),
            })
        if not out:
            out = [
                {"id": "ukhu", "name": "Ukhu Pacha", "description": "", "background": "umbral", "enemy_pool": ["ukhu"], "event_pool": [], "boss": "guardian_de_la_grieta", "atmosphere_tags": ["subterraneo"]},
                {"id": "kaypacha", "name": "Kay Pacha", "description": "", "background": "kaypacha", "enemy_pool": ["kay"], "event_pool": [], "boss": "oraculo_del_vacio", "atmosphere_tags": ["terrenal"]},
                {"id": "hanan", "name": "Hanan Pacha", "description": "", "background": "hanan", "enemy_pool": ["hanan"], "event_pool": [], "boss": "senor_de_la_chakana_rota", "atmosphere_tags": ["astral"]},
                {"id": "fractura_chakana", "name": "Fractura de la Chakana", "description": "", "background": "ruinas_chakana", "enemy_pool": ["boss", "hanan"], "event_pool": [], "boss": "arconte_supremo", "atmosphere_tags": ["final"]},
            ]
        return out

    def _normalize_biome_id(self, biome_id: str | None) -> str:
        key = str(biome_id or "").strip().lower()
        if key in self.biome_def_by_id:
            return key
        if self.biome_defs:
            return str(self.biome_defs[0].get("id") or "kaypacha")
        return "kaypacha"

    def _biome_progression(self) -> list[str]:
        progression = []
        for b in self.biome_defs if isinstance(self.biome_defs, list) else []:
            if not isinstance(b, dict) or not b.get("id"):
                continue
            bid = self._normalize_biome_id(b.get("id"))
            if bid not in progression:
                progression.append(bid)
            if len(progression) >= 4:
                break
        for fallback in ["ukhu", "kaypacha", "hanan", "fractura_chakana"]:
            if fallback not in progression:
                progression.append(fallback)
            if len(progression) >= 4:
                break
        return progression[:4]

    def _biome_for_column(self, col: int, total_columns: int) -> str:
        prog = self._biome_progression()
        if not prog:
            return "kaypacha"
        if total_columns <= 1:
            return prog[0]
        idx = int((max(0, min(total_columns - 1, int(col))) * len(prog)) / total_columns)
        idx = max(0, min(len(prog) - 1, idx))
        return prog[idx]

    def _enemy_biome_tokens(self, biome_id: str | None) -> set[str]:
        biome_key = self._normalize_biome_id(biome_id)
        biome = self.biome_def_by_id.get(biome_key, {})
        tokens = set()
        for t in biome.get("enemy_pool", []) if isinstance(biome, dict) else []:
            tok = str(t or "").strip().lower()
            if tok:
                tokens.add(tok)
        return tokens

    def _event_pool_for_biome(self, biome_id: str | None) -> list[dict]:
        biome_key = self._normalize_biome_id(biome_id)
        biome = self.biome_def_by_id.get(biome_key, {})
        event_ids = [str(x).strip().lower() for x in biome.get("event_pool", []) if str(x).strip()] if isinstance(biome, dict) else []
        if not event_ids:
            return list(self.events_data)
        by_id = {
            str(e.get("id", "")).strip().lower(): e
            for e in self.events_data
            if isinstance(e, dict) and e.get("id")
        }
        selected = [by_id[eid] for eid in event_ids if eid in by_id]
        return selected or list(self.events_data)

    def get_biome_lore(self, biome_id: str | None = None) -> dict:
        biome_key = str(biome_id or (self.run_state or {}).get("biome") or "kaypacha").lower()
        data = self.biomes_lore.get(biome_key, {}) if isinstance(self.biomes_lore, dict) else {}
        return data if isinstance(data, dict) else {}

    def get_biome_display_name(self, biome_id: str | None = None) -> str:
        biome_key = str(biome_id or (self.run_state or {}).get("biome") or "kaypacha").lower()
        lore = self.get_biome_lore(biome_key)
        if isinstance(lore, dict) and lore.get("display_name_es"):
            return str(lore.get("display_name_es"))
        biome = self.biome_def_by_id.get(biome_key, {}) if isinstance(self.biome_def_by_id, dict) else {}
        return str((biome or {}).get("name") or biome_key.title())

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
            "lore": "event",
            "map": f"map_{str(biome_id or (self.run_state or {}).get('biome') or 'kaypacha').lower()}",
            "combat": f"combat_{str(biome_id or (self.run_state or {}).get('biome') or 'kaypacha').lower()}",
            "shop": "shop",
            "reward": "shop",
            "boss": "boss",
            "events": "event",
        }
        return fallback.get(ctx, "menu")

    def play_stinger(self, name: str):
        try:
            self.sfx.play(name)
        except Exception:
            pass

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
            self.loading_screen.set_step("Continuando con placeholders...", pct)
        self.loading_screen.draw(self.renderer.internal, 1.0 / max(1, FPS))
        self.renderer.present()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False

    def _load_cards_data(self):
        cards_path = data_dir() / "cards.json"
        cards = self.content.cards if isinstance(self.content.cards, list) and self.content.cards else load_json(cards_path, default=[])

        # Startup-safe auto-fix for archetype rarity lock (12/7/1 per archetype).
        if isinstance(cards, list) and cards:
            fixed = enforce_archetype_rarity_distribution(cards)
            cards = fixed.get("cards", cards)
            for line in list(fixed.get("logs", []) or []):
                print(line)
            if bool(fixed.get("changed", False)):
                try:
                    atomic_write_json_if_changed(cards_path, cards)
                    print("[content] archetype rarity auto-fix applied")
                except Exception as exc:
                    print(f"[content] archetype rarity auto-fix persist failed: {exc}")

        cards = self._apply_phase75_card_tuning(cards)

        cooked = []
        for c in cards if isinstance(cards, list) else []:
            if not isinstance(c, dict) or not c.get("id"):
                continue
            enriched = self._enrich_card_semantic_fields(c)
            cooked.append({
                "id": enriched.get("id"),
                "name_key": enriched.get("name_es", enriched.get("name_key", enriched.get("id"))),
                "text_key": enriched.get("text_es", enriched.get("text_key", enriched.get("id"))),
                "rarity": enriched.get("rarity", "common"),
                "cost": int(enriched.get("cost", 1)),
                "target": enriched.get("target", "enemy"),
                "tags": list(enriched.get("tags", [])),
                "effects": list(enriched.get("effects", [])),
                "role": str(enriched.get("role") or infer_card_role(enriched)),
                "family": (enriched.get("direction", "ESTE") or "ESTE").lower(),
                "direction": enriched.get("direction", "ESTE"),
                "strategy": enriched.get("strategy", {}),
                "lore_text": enriched.get("lore_text", ""),
                "effect_text": enriched.get("effect_text", enriched.get("text_key", "")),
                "archetype": enriched.get("archetype", ""),
                "motif": enriched.get("motif", ""),
                "palette": enriched.get("palette", ""),
                "energy": enriched.get("energy", ""),
                "symbol": enriched.get("symbol", ""),
                "author": enriched.get("author", "Mauricio"),
                "order": enriched.get("order", "Chakana"),
            })
        by_id = {c.get("id"): c for c in cooked if c.get("id")}
        if not by_id:
            for base in DEFAULT_CARDS:
                by_id.setdefault(base["id"], base)
        return list(by_id.values())

    def _enrich_card_semantic_fields(self, card: dict) -> dict:
        """Ensure runtime card semantics exist for UI/art guidance without changing mechanics."""
        row = dict(card or {})
        direction = str(row.get("direction", "ESTE") or "ESTE").upper()
        role = str(row.get("role") or infer_card_role(row)).strip().lower()
        tags = {str(t).strip().lower() for t in list(row.get("tags", []) or [])}

        if not str(row.get("archetype", "")).strip():
            by_dir = {
                "ESTE": "cosmic_warrior",
                "SUR": "harmony_guardian",
                "NORTE": "oracle_of_fate",
                "OESTE": "oracle_of_fate",
            }
            row["archetype"] = by_dir.get(direction, "cosmic_warrior")

        if not str(row.get("motif", "")).strip():
            if "ritual" in tags:
                row["motif"] = "ritual_symbols"
            elif "attack" in tags or role == "attack":
                row["motif"] = "demons"
            elif "block" in tags or role == "defense":
                row["motif"] = "sacred_forms"
            elif "scry" in tags or "draw" in tags or role in {"control", "combo"}:
                row["motif"] = "cosmic_geometry"
            else:
                row["motif"] = "chakana"

        if not str(row.get("palette", "")).strip():
            by_arch = {
                "cosmic_warrior": "crimson-magenta",
                "harmony_guardian": "teal-gold",
                "oracle_of_fate": "indigo-cyan",
            }
            row["palette"] = by_arch.get(str(row.get("archetype", "")).strip().lower(), "violet-neutral")

        if not str(row.get("energy", "")).strip():
            if "ritual" in tags:
                row["energy"] = "ritual_flux"
            elif "attack" in tags:
                row["energy"] = "burst_arcs"
            elif "block" in tags:
                row["energy"] = "stable_rings"
            elif "draw" in tags or "scry" in tags:
                row["energy"] = "spiral_streams"
            else:
                row["energy"] = "arc_traces"

        if not str(row.get("symbol", "")).strip():
            if "attack" in tags:
                row["symbol"] = "blade_sigil"
            elif "block" in tags:
                row["symbol"] = "shield_mandala"
            elif "ritual" in tags:
                row["symbol"] = "seal_lock"
            elif "draw" in tags or "scry" in tags:
                row["symbol"] = "astral_eye"
            else:
                row["symbol"] = "chakana_glyph"

        if not str(row.get("author", "")).strip():
            row["author"] = "Mauricio"
        if not str(row.get("order", "")).strip():
            row["order"] = "Chakana"

        return row
    def _apply_phase75_card_tuning(self, cards):
        """Phase 7.5 tuning: keep archetype identity while improving viability and pacing."""
        if not isinstance(cards, list):
            return cards

        tuned = []
        guardian_damage_ids = {"guardia_terrenal", "hg_lore_15"}
        guardian_break_ids = {"sello_protector", "hg_lore_27", "muralla_de_piedra", "hg_lore_19"}
        guardian_hybrid_ids = {"campo_protector"}

        for c in cards:
            if not isinstance(c, dict):
                continue
            cc = dict(c)
            effects = [dict(e) for e in list(cc.get("effects", []) or []) if isinstance(e, dict)]
            cc["effects"] = effects
            cid = str(cc.get("id", ""))
            arch = str(cc.get("archetype", "")).strip().lower()
            role = str(cc.get("role", "")).strip().lower()
            tags = set(cc.get("tags", []) or [])

            def _sum(types: set[str]) -> int:
                total = 0
                for ef in effects:
                    if str(ef.get("type", "")).lower() in types:
                        total += int(ef.get("amount", 0) or 0)
                return int(total)

            def _has(ef_type: str) -> bool:
                k = str(ef_type or "").lower()
                return any(str(ef.get("type", "")).lower() == k for ef in effects)

            def _append(ef_type: str, amount: int):
                effects.append({"type": str(ef_type), "amount": int(amount)})

            if arch == "harmony_guardian":
                if cid in guardian_damage_ids and not _has("damage"):
                    _append("damage", 2)
                if cid in guardian_hybrid_ids and _sum({"damage"}) <= 0:
                    _append("damage", 2)
                if cid in guardian_break_ids and not _has("apply_break"):
                    _append("apply_break", 2 if cid in {"muralla_de_piedra", "hg_lore_19"} else 1)
                if _sum({"damage"}) > 0:
                    tags.add("attack")

            if arch == "oracle_of_fate":
                scry = _sum({"scry"})
                draw = _sum({"draw"})
                dmg = _sum({"damage", "damage_plus_rupture"})
                harmony = _sum({"harmony_delta"})
                cost = int(cc.get("cost", 1) or 1)
                if role in {"control", "ritual"} and cost >= 2 and dmg <= 0 and (scry >= 3 or harmony > 0):
                    cc["cost"] = max(0, cost - 1)
                if scry >= 4 and draw <= 0:
                    _append("draw", 1)
                    tags.add("draw")

            cc["tags"] = sorted(tags)

            # Keep card text/KPI coherent with tuned effects.
            totals = {
                "damage": _sum({"damage", "damage_plus_rupture"}),
                "block": _sum({"gain_block", "block"}),
                "rupture": _sum({"apply_break", "rupture", "set_rupture"}),
                "scry": _sum({"scry"}),
                "draw": _sum({"draw"}),
                "energy": _sum({"gain_mana", "gain_mana_next_turn"}),
                "harmony": _sum({"harmony_delta"}),
                "seal": _sum({"consume_harmony"}),
                "ritual": _sum({"ritual_trama"}),
                "support": _sum({"weaken_enemy", "debuff", "heal"}),
            }
            cc["kpi"] = {k: int(v) for k, v in totals.items() if int(v) > 0}

            labels = [
                ("damage", "Dano"),
                ("block", "Bloqueo"),
                ("rupture", "Ruptura"),
                ("scry", "Prever"),
                ("draw", "Roba"),
                ("energy", "Energia"),
                ("harmony", "Armonia"),
                ("seal", "Sello"),
                ("ritual", "Ritual"),
                ("support", "Soporte"),
            ]
            parts = [f"{label} {int(totals[key])}" for key, label in labels if int(totals.get(key, 0)) > 0]
            if parts:
                cc["effect_text"] = ", ".join(parts[:4])

            tuned.append(cc)

        return tuned

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
                "biome": str(e.get("biome", "")).lower(),
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
            tags = {str(t).lower() for t in (card.get("tags", []) or [])}
            arch = str(card.get("archetype", "") or "core").lower()
            role = str(card.get("role", "") or infer_card_role(card)).lower()
            effects = [str(e.get("type", "")).lower() for e in list(card.get("effects", []) or []) if isinstance(e, dict)]
            if "attack" in tags:
                ctype = "attack"
            elif "block" in tags or "defense" in tags:
                ctype = "defense"
            elif "draw" in tags or "scry" in tags or "control" in tags:
                ctype = "control"
            elif "ritual" in tags:
                ctype = "ritual"
            else:
                ctype = "spirit"
            primary = "damage" if "damage" in effects else "block" if "gain_block" in effects or "block" in effects else "scry" if "scry" in effects else "ritual" if "ritual_trama" in effects else "support"
            mood = "astral crimson" if arch == "cosmic_warrior" else "guardia dorada" if arch == "harmony_guardian" else "oraculo indigo" if arch == "oracle_of_fate" else "violeta mistico"
            payload["cards"][cid] = {
                "prompt": f"chakana card::{cid} role={role} archetype={arch} type={ctype} primary={primary} mood={mood} sacred geometry, crisp pixel art, no blur, intentional silhouette",
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
            "starter_decks": [
                {"id": "cosmic_warrior", "name": "Cosmic Warrior"},
                {"id": "harmony_guardian", "name": "Harmony Guardian"},
                {"id": "oracle_of_fate", "name": "Oracle of Fate"},
            ],
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

    def _oracle_line(self, trigger: str, payload=None, speaker: str = "chakana") -> str:
        trig = str(trigger or "").lower()
        role = str(speaker or "chakana").lower()
        lore_data = self.lore_data if isinstance(self.lore_data, dict) else {}
        event_fragments = list(lore_data.get("event_fragments", []) or [])

        # Context pools: lore narration / reactive gameplay / prophecy.
        lore_pool = {
            "run_start": "La Trama despierta. El viaje ritual comienza.",
            "path_selected": "Los 7 Caminos reescriben tu destino.",
            "event_node": "Un eco ancestral abre una decision.",
        }
        reactive_pool = {
            "combat_start": "Respira: cada carta define el pulso del rito.",
            "elite_encounter": "La geometria se tensa: se acerca una prueba mayor.",
            "enemy_low_hp": "Su forma se quiebra. Mantente firme.",
            "player_low_hp": "Sostente. Aun puedes inclinar la Trama.",
        }
        prophecy_pool = {
            "boss_reveal": "El Arconte ya observa tu pulso.",
            "victory": "Tu equilibrio altero el destino del pacha.",
            "defeat": "La caida tambien ensena el siguiente trazo.",
        }

        archon_lore = {
            "run_start": "Cada sendero termina en mi umbral.",
            "path_selected": "Ese camino tambien alimenta mi dominio.",
            "event_node": "Los ecos no te salvaran del quiebre.",
        }
        archon_reactive = {
            "combat_start": "Tu rito es fragil frente al vacio.",
            "elite_encounter": "Esta prueba abrira tu fractura.",
            "enemy_low_hp": "Aun herido, mi designio permanece.",
            "player_low_hp": "Tu pulso cae. Entregate al silencio.",
        }
        archon_prophecy = {
            "boss_reveal": "Por fin frente a mi: no habra retorno.",
            "victory": "Una victoria breve en una guerra infinita.",
            "defeat": "La Trama te rompe y me pertenece.",
        }

        if role == "archon":
            lpool, rpool, ppool = archon_lore, archon_reactive, archon_prophecy
        else:
            lpool, rpool, ppool = lore_pool, reactive_pool, prophecy_pool

        if trig == "event_node" and event_fragments and role != "archon":
            return str(self.rng.choice(event_fragments))

        if trig in {"path_selected", "path_node"} and isinstance(payload, dict):
            ptxt = str(payload.get("path_lore") or payload.get("path_name") or "")
            if ptxt:
                return ptxt

        if trig in {"boss_reveal", "elite_encounter"} and isinstance(payload, dict):
            n = str(payload.get("name") or payload.get("id") or "").strip()
            base = ppool if trig in ppool else rpool
            line = base.get(trig, "")
            if n and line:
                return f"{line} {n}."

        if trig in ppool:
            return ppool[trig]
        if trig in rpool:
            return rpool[trig]
        if trig in lpool:
            return lpool[trig]
        return "La Trama habla en silencio."

    def _oracle_priority(self, trigger: str, speaker: str) -> int:
        trig = str(trigger or "").lower()
        role = str(speaker or "chakana").lower()
        high = {"boss_reveal", "victory", "defeat"}
        medium = {"elite_encounter", "path_selected", "event_node", "player_low_hp", "enemy_low_hp"}
        if trig in high:
            return 3 if role == "archon" else 2
        if role == "archon" and trig in {"combat_start", "player_low_hp", "enemy_low_hp"}:
            return 2
        if trig in medium:
            return 1
        return 0

    def _oracle_duration(self, trigger: str, line: str, speaker: str) -> float:
        trig = str(trigger or "").lower()
        words = max(1, len(str(line or "").split()))
        base = 2.7 if words <= 8 else 3.5 if words <= 14 else 4.4
        if trig in {"boss_reveal", "victory", "defeat"}:
            base += 0.8
        if str(speaker or "").lower() == "archon":
            base += 0.25
        return max(2.5, min(5.6, base))

    def trigger_oracle(self, trigger: str, payload=None):
        if not hasattr(self, "oracle_ui") or self.oracle_ui is None:
            return

        trig = str(trigger or "").lower()
        now = pygame.time.get_ticks()

        # Anti-spam cooldown (global + per trigger).
        global_cd_ms = 1300
        per_trigger_cd = {
            "player_low_hp": 9000,
            "enemy_low_hp": 7600,
            "combat_start": 3000,
            "event_node": 2600,
            "path_selected": 2600,
            "elite_encounter": 3400,
            "boss_reveal": 4200,
            "victory": 1300,
            "defeat": 1300,
            "run_start": 1300,
        }
        if now - int(self._oracle_last_ms or 0) < global_cd_ms:
            return
        trig_last = int(self._oracle_last_by_trigger.get(trig, 0) or 0)
        if now - trig_last < int(per_trigger_cd.get(trig, 3000)):
            return

        speaker = "chakana"
        interference = False

        # Rare Archon interruptions, focused on major beats.
        rare_roll = self.rng.randint(1, 100)
        if trig == "boss_reveal":
            speaker = "archon"
            interference = True
        elif trig in {"elite_encounter", "player_low_hp"} and rare_roll <= 26:
            speaker = "archon"
            interference = True
        elif trig in {"combat_start", "enemy_low_hp", "victory", "defeat"} and rare_roll <= 12:
            speaker = "archon"
            interference = True

        prio = self._oracle_priority(trig, speaker)
        if bool(getattr(self.oracle_ui, "active", False)) and now < int(self._oracle_active_until_ms or 0):
            if prio < int(self._oracle_active_priority or 0):
                return

        title = "ORACULO CHAKANA" if speaker == "chakana" else "INTERFERENCIA DEL ARCONTE"
        line = self._oracle_line(trig, payload=payload, speaker=speaker)
        duration = self._oracle_duration(trig, line, speaker)
        self.oracle_ui.show(
            line,
            trigger=trig,
            title=title,
            speaker=speaker,
            interference=interference,
            duration=duration,
            priority=prio,
        )

        self._oracle_last_ms = now
        self._oracle_last_by_trigger[trig] = now
        self._oracle_active_priority = prio
        self._oracle_active_until_ms = now + int(duration * 1000)

    def goto_menu(self):
        if self.sm.current and not isinstance(self.sm.current, MenuScreen):
            self.menu_return_screen = self.sm.current
        self.sm.set(MenuScreen(self))
        self.music.play_for(self.get_bgm_track("menu"))

    def goto_settings(self):
        self.sm.set(SettingsScreen(self))

    def goto_end(self, victory=True):
        if not victory:
            self.play_stinger("stinger_defeat")
        can_resume_defeat = (not victory) and isinstance(self.run_state, dict) and bool(self.run_state.get("allow_defeat_continue", False))
        if victory or not can_resume_defeat:
            self._clear_saved_run()
            self.current_combat = None
            self.run_state = None
            self.current_node_id = None
            self.node_lookup = {}
        else:
            self.current_combat = None
            self._autosave_run("defeat_screen_resume_ready")
        self.trigger_oracle("victory" if victory else "defeat")
        title = "Victoria" if victory else "Derrota"
        lore = "el eco celebro tu equilibrio." if victory else "la Trama pidio un nuevo intento."
        self.sm.set(PachaTransitionScreen(self, title, lambda: self.sm.set(EndScreen(self, victory=victory)), lore_line=lore, hint="Cierre del capitulo"))

    def goto_path_select(self):
        self.sm.set(PathSelectScreen(self))

    def goto_deck(self):
        self.sm.set(DeckScreen(self))

    def goto_codex(self):
        self.sm.set(CodexScreen(self))

    def goto_tutorial(self):
        self.sm.set(TutorialScreen(self, next_fn=self.goto_path_select))

    def new_run(self):
        self.pending_tutorial_enabled = not bool(self.user_settings.get("tutorial_completed", False))
        if self.user_settings.get("dev_skip_intro", False) is True:
            self.goto_path_select()
            return
        if not self.story_intro_seen:
            self.story_intro_seen = True
            self.sm.set(IntroScreen(self, next_fn=self.goto_path_select))
            return
        self.goto_path_select()

    def _sync_tutorial_run_state(self):
        if not isinstance(self.run_state, dict):
            return
        self.run_state["tutorial"] = self.tutorial_flow.snapshot()

    def mark_tutorial_completed(self):
        if not getattr(self.tutorial_flow, "completed", False):
            return
        self.user_settings["tutorial_completed"] = True
        self.pending_tutorial_enabled = False
        self._sync_tutorial_run_state()
        save_settings(self.user_settings)
        print("[tutorial] completed: first-run guide disabled")

    def xp_needed_for_level(self, level: int) -> int:
        lvl = max(1, int(level or 1))
        return 25 + (lvl - 1) * 15

    def _refresh_node_lookup_from_map(self):
        self.node_lookup = {}
        if not isinstance(self.run_state, dict):
            return
        for col in self.run_state.get("map", []):
            for node in col if isinstance(col, list) else []:
                if isinstance(node, dict) and node.get("id"):
                    self.node_lookup[str(node["id"])] = node

    def _migrate_legacy_shop_nodes(self):
        """Legacy hook kept for save compatibility; shop nodes are now first-class again."""
        return 0

    def _autosave_run(self, reason: str = ""):
        if not isinstance(self.run_state, dict):
            return
        if isinstance(self.sm.current, CombatScreen):
            return
        payload = dict(self.run_state)
        payload["current_node_id"] = self.current_node_id
        payload["last_biome_seen"] = self.last_biome_seen
        payload["saved_at"] = int(time.time())
        save_run(payload)
        if reason:
            print(f"[save] autosave: {reason}")

    def _try_restore_run_from_save(self):
        if self.run_state:
            return
        payload = load_run()
        if not isinstance(payload, dict):
            return
        run_map = payload.get("map")
        player = payload.get("player")
        deck = payload.get("deck")
        if not isinstance(run_map, list) or not isinstance(player, dict) or not isinstance(deck, list):
            return
        self.run_state = payload
        self.run_state.setdefault("allow_defeat_continue", True)
        self._migrate_legacy_shop_nodes()
        self.current_node_id = payload.get("current_node_id")
        self.last_biome_seen = payload.get("last_biome_seen")
        self._refresh_node_lookup_from_map()
        self.recover_map_progression()
        print("[save] continue run restored")

    def _clear_saved_run(self):
        clear_run()

    def _apply_post_combat_recovery(self, node_type: str):
        if not isinstance(self.run_state, dict):
            return
        player = self.run_state.get("player", {})
        if not isinstance(player, dict):
            return
        max_hp = int(player.get("max_hp", 0) or 0)
        hp = int(player.get("hp", 0) or 0)
        if max_hp <= 0 or hp <= 0:
            return
        ratio = POST_COMBAT_HEAL.get(str(node_type or "combat"), POST_COMBAT_HEAL["combat"])
        heal = max(1, int(max_hp * float(ratio)))
        player["hp"] = min(max_hp, hp + heal)
        print(f"[run] post-combat heal +{heal} ({player['hp']}/{max_hp})")

    def _apply_relic_noncombat_hook(self, hook: str):
        if not isinstance(self.run_state, dict):
            return
        owned = {str(rid) for rid in list(self.run_state.get("relics", []) or []) if rid}
        if not owned:
            return
        by_id = {str(r.get("id")): r for r in list(self.relics_data or []) if isinstance(r, dict) and r.get("id")}
        player = self.run_state.get("player", {}) if isinstance(self.run_state.get("player", {}), dict) else {}
        for rid in sorted(owned):
            relic = by_id.get(rid)
            if not relic:
                continue
            hooks = {str(h).lower() for h in list(relic.get("hooks", []) or [])}
            if str(hook).lower() not in hooks:
                continue
            for eff in list(relic.get("effects", []) or []):
                et = str(eff.get("type", "")).lower()
                amt = int(eff.get("amount", 0) or 0)
                if et == "heal":
                    max_hp = int(player.get("max_hp", 0) or 0)
                    hp = int(player.get("hp", 0) or 0)
                    if max_hp > 0 and hp > 0 and amt > 0:
                        player["hp"] = min(max_hp, hp + amt)
                elif et == "gain_gold":
                    self.apply_run_rewards(gold=max(0, amt), source=f"relic_{rid}_{hook}")
                elif et == "gain_xp":
                    self.apply_run_rewards(xp=max(0, amt), source=f"relic_{rid}_{hook}")
                elif et == "gain_max_hp":
                    if amt > 0:
                        player["max_hp"] = int(player.get("max_hp", 0) or 0) + amt
                        player["hp"] = int(player.get("hp", 0) or 0) + amt
            print(f"[relic] hook={hook} relic={rid}")

    def _apply_relic_combat_start_effects(self, combat_state):
        if not isinstance(self.run_state, dict) or combat_state is None:
            return
        owned = {str(rid) for rid in list(self.run_state.get("relics", []) or []) if rid}
        if not owned:
            return
        by_id = {str(r.get("id")): r for r in list(self.relics_data or []) if isinstance(r, dict) and r.get("id")}
        for rid in sorted(owned):
            relic = by_id.get(rid)
            if not relic:
                continue
            hooks = {str(h).lower() for h in list(relic.get("hooks", []) or [])}
            if "combat_start" not in hooks:
                continue
            for eff in list(relic.get("effects", []) or []):
                et = str(eff.get("type", "")).lower()
                amt = int(eff.get("amount", 0) or 0)
                if et in {"gain_energy", "energy", "gain_mana"}:
                    combat_state.player["energy"] = int(combat_state.player.get("energy", 0) or 0) + amt
                elif et == "draw":
                    combat_state.draw(max(0, amt))
                elif et in {"gain_block", "block"}:
                    combat_state.player["block"] = int(combat_state.player.get("block", 0) or 0) + max(0, amt)
                elif et == "heal":
                    combat_state.heal_player(max(0, amt))
                elif et == "rupture":
                    combat_state.player["rupture"] = int(combat_state.player.get("rupture", 0) or 0) + amt
                elif et == "harmony_delta":
                    cur = int(combat_state.player.get("harmony_current", 0) or 0)
                    hmax = int(combat_state.player.get("harmony_max", 10) or 10)
                    combat_state.player["harmony_current"] = max(0, min(hmax, cur + amt))
                elif et == "apply_break":
                    target = next((e for e in list(combat_state.enemies or []) if getattr(e, "alive", False)), None)
                    if target is not None and hasattr(target, "statuses"):
                        target.statuses["break"] = int(target.statuses.get("break", 0) or 0) + max(0, amt)
            print(f"[relic] hook=combat_start relic={rid}")

    def start_run_with_deck(self, starter_deck):
        base_deck = list(starter_deck or [])
        min_deck_size = 15
        max_deck_size = 20
        if not base_deck:
            base_deck = [c.get("id") for c in self.cards_data[:min_deck_size] if isinstance(c, dict) and c.get("id")]
        if not base_deck:
            base_deck = [DEFAULT_CARDS[0]["id"]]
        while len(base_deck) < min_deck_size:
            base_deck.append(base_deck[len(base_deck) % len(base_deck)])
        base_deck = base_deck[:max_deck_size]

        tutorial_enabled = bool(self.pending_tutorial_enabled)
        self.tutorial_flow.start_for_run(tutorial_enabled)

        run_map = self.generate_map()
        map_columns = max(1, len(run_map))
        self.run_state = {
            "gold": 80,
            "relics": ["violet_seal"],
            "player": {"hp": 60, "max_hp": 60, "block": 0, "energy": 3, "rupture": 0, "statuses": {}},
            "deck": list(base_deck),
            "sideboard": [],
            "map": run_map,
            "map_columns": map_columns,
            "biome_progression": self._biome_progression(),
            "biome_index": 0,
            "biome": self._biome_for_column(0, map_columns),
            "xp": 0,
            "level": 1,
            "combats_won": 0,
            "allow_defeat_continue": True,
            "settings": {
                "turn_timer_enabled": bool(self.user_settings.get("turn_timer_enabled", True)),
                "turn_timer_seconds": int(self.user_settings.get("turn_timer_seconds", 20)),
                "music_muted": bool(self.user_settings.get("music_muted", self.user_settings.get("music_mute", False))),
            },
        }
        self.current_node_id = None
        self.current_combat = None
        self._sync_tutorial_run_state()
        self._autosave_run("new_run_started")
        self.trigger_oracle("run_start")
        self.goto_map()

    def generate_map(self):
        layout = list(MAP_TEMPLATE)
        columns = len(layout)
        by_col = []
        self.node_lookup = {}
        path_cursor = 0

        x_margin = 180
        x_step = (INTERNAL_WIDTH - x_margin * 2) // max(1, (columns - 1))
        y_center = INTERNAL_HEIGHT // 2

        for col, spec in enumerate(layout):
            count = max(1, int(spec.get("count", 1)))
            col_nodes = []
            row_gap = 96 if count >= 3 else 120
            center_idx = (count - 1) / 2.0
            col_types = list(spec.get("types", []) or [])
            for row in range(count):
                node_id = f"{col}_{row}"
                y = y_center if count == 1 else int(y_center + (row - center_idx) * row_gap)

                if col_types:
                    node_type = str(col_types[min(row, len(col_types) - 1)] or spec.get("type", "combat"))
                else:
                    node_type = str(spec.get("type", "combat"))

                if node_type == "challenge" and self.rng.randint(0, 100) < 28:
                    node_type = "combat"
                node_biome = self._biome_for_column(col, columns)
                node = {
                    "id": node_id,
                    "col": col,
                    "x": x_margin + col * x_step,
                    "y": y,
                    "type": node_type,
                    "biome": node_biome,
                    "next": [],
                    "state": "available" if col == 0 else "locked",
                }
                if node_type == "path":
                    path = SEVEN_PATHS[path_cursor % len(SEVEN_PATHS)]
                    path_cursor += 1
                    node["path_id"] = str(path.get("id"))
                    node["path_name"] = str(path.get("title"))
                    node["path_lore"] = str(path.get("lore"))
                col_nodes.append(node)
                self.node_lookup[node_id] = node
            by_col.append(col_nodes)

        # Ritual routing: primary link + nearby alternate to avoid chaotic crossing.
        for col in range(columns - 1):
            cur_nodes = by_col[col]
            next_nodes = by_col[col + 1]
            if not next_nodes:
                continue
            for i, node in enumerate(cur_nodes):
                mapped = int(round((i / max(1, len(cur_nodes) - 1)) * max(0, len(next_nodes) - 1)))
                node["next"].append(next_nodes[mapped]["id"])
                if len(next_nodes) > 1:
                    alt_idx = mapped + (1 if (i % 2 == 0) else -1)
                    alt_idx = max(0, min(len(next_nodes) - 1, alt_idx))
                    alt_id = next_nodes[alt_idx]["id"]
                    if alt_id not in node["next"]:
                        node["next"].append(alt_id)

        return by_col

    def goto_map(self):
        self._migrate_legacy_shop_nodes()
        if self.run_state and self.run_state.get("levelup_pending", 0) > 0:
            self.sm.set(PackOpeningScreen(self))
            self.music.play_for("chest")
            return
        self._autosave_run("goto_map")
        self.debug["map_available_count"] = self.available_nodes_count() if self.node_lookup else 0
        self.debug["current_node_id"] = self.current_node_id or "-"
        biome_track = self.run_state.get("biome", "kaypacha") if self.run_state else "kaypacha"
        if self.last_biome_seen is None:
            self.last_biome_seen = biome_track
            self.sm.set(PachaTransitionScreen(self, "Comienza la Trama", lambda: self.sm.set(MapScreen(self)), lore_line="Chakana abrio su primer sendero.", hint="Pulsa cualquier tecla para caminar"))
        elif self.last_biome_seen != biome_track:
            self.last_biome_seen = biome_track
            self.sm.set(PachaTransitionScreen(self, f"Mapa: {str(biome_track).title()}", lambda: self.sm.set(MapScreen(self)), lore_line="un nuevo territorio abrio su geometria.", hint="Pulsa cualquier tecla para continuar"))
        else:
            self.sm.set(MapScreen(self))
        self.music.play_for(self.get_bgm_track("map", biome_track))

    def goto_combat(self, combat_state, is_boss=False):
        self.current_combat = combat_state
        self.trigger_oracle("combat_start")
        try:
            pc = combat_state.pile_counts() if hasattr(combat_state, "pile_counts") else {"draw": 0, "hand": len(getattr(combat_state, "hand", []) or []), "discard": 0}
            print(f"[boot] combat_engine piles: draw={pc.get('draw',0)} hand={pc.get('hand',0)} discard={pc.get('discard',0)}")
        except Exception:
            pass

        def _enter_combat():
            self.sm.set(CombatScreen(self, combat_state, is_boss=is_boss))
            if is_boss:
                self.play_stinger("stinger_boss_phase")
                self.music.play_for(self.get_bgm_track("boss"))
            else:
                biome_track = self.run_state.get("biome", "kaypacha") if self.run_state else "kaypacha"
                self.music.play_for(self.get_bgm_track("combat", biome_track))

        if is_boss:
            self.trigger_oracle("boss_reveal")
        title = "Umbral del Jefe" if is_boss else "Entrando en Combate"
        lore = "la sombra mayor desperto." if is_boss else "el pulso enemigo se hizo audible."
        self.sm.set(PachaTransitionScreen(self, title, _enter_combat, lore_line=lore, hint="Pulsa cualquier tecla para preparar tu mano"))

    def goto_reward(self, picks=None, gold=None, mode=None, relic=None, guide_reward=None):
        reward_mode = mode or "choose1of3"
        if reward_mode == "guide_choice":
            reward_data = guide_reward or build_reward_guide("guide", self.rng, self.cards_data, self.run_state or {})
            reward_data["type"] = "guide_choice"
            self.sm.set(RewardScreen(self, reward_data, gold=0, xp_gained=self.debug.get("xp_last_gain", 0)))
            self.play_stinger("stinger_reward")
            self.music.play_for(self.get_bgm_track("reward"))
            return

        if reward_mode == "boss_pack":
            reward_data = build_reward_boss(self.rng, self.cards_data, self.relics_data, self.run_state or {})
            if relic is not None:
                reward_data["relic"] = relic
            reward_data["type"] = "boss_pack"
            self.sm.set(RewardScreen(self, reward_data, gold=gold or 0, xp_gained=self.debug.get("xp_last_gain", 0)))
            self.play_stinger("stinger_reward")
            self.music.play_for(self.get_bgm_track("reward"))
            return

        if picks is None:
            unlock_level = self.run_state.get("level", 1) if self.run_state else 1
            rarities = {"basic", "common"} if unlock_level < 2 else {"common", "uncommon", "rare"}
            pool = [c for c in self.cards_data if c.get("rarity") in rarities] or self.cards_data
            reward_data = build_reward_normal(self.rng, pool, self.run_state or {})
        else:
            reward_data = {"type": "choose1of3", "cards": list(picks)}
        if gold is None:
            gold = int(round(self.rng.randint(20, 35) * 1.3))

        self.sm.set(RewardScreen(self, reward_data, gold, xp_gained=self.debug.get("xp_last_gain", 0)))
        self.play_stinger("stinger_reward")
        self.music.play_for(self.get_bgm_track("reward"))

    def goto_shop(self):
        pool = [c for c in self.cards_data if c.get("rarity") in {"common", "uncommon"}] or self.cards_data
        self.sm.set(ShopScreen(self, self.rng.choice(pool) or DEFAULT_CARDS[0]))
        self.music.play_for(self.get_bgm_track("shop"))

    def goto_event(self):
        biome = self._normalize_biome_id((self.run_state or {}).get("biome"))
        pool = self._event_pool_for_biome(biome)
        event = self.rng.choice(pool) if pool else {"title_key": "map_title", "body_key": "lore_tagline", "choices": [{"text_key": "event_continue", "effects": []}]}
        self.trigger_oracle("event_node", payload=event)
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
        biome = self._normalize_biome_id(node.get("biome"))
        if self.run_state is not None:
            self.run_state["biome"] = biome
            prog = list(self.run_state.get("biome_progression", []))
            self.run_state["biome_index"] = prog.index(biome) if biome in prog else max(0, int(node.get("col", 0)))
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
        self._autosave_run("node_completed")
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
        node_biome = self._normalize_biome_id((node or {}).get("biome") or (self.run_state or {}).get("biome"))
        biome_tokens = self._enemy_biome_tokens(node_biome)
        scoped = []
        if biome_tokens:
            scoped = [e for e in self.enemies_data if str(e.get("biome", "")).lower() in biome_tokens]
        source = scoped or list(self.enemies_data)
        commons = [e["id"] for e in source if e.get("id") and e.get("tier", "common") == "common"]
        elites = [e["id"] for e in source if e.get("id") and e.get("tier") == "elite"]
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
        raw_type = str(node.get("type", "combat") or "combat")
        node_type = raw_type
        if node_type == "relic":
            node_type = "treasure"
        if node_type == "elite":
            self.trigger_oracle("elite_encounter", payload=node)
            node_type = "challenge"
        if node_type in {"combat", "challenge", "boss"}:
            boss_ids = [b.get("id") for b in self.content.bosses if isinstance(b, dict) and b.get("id")]
            node_biome = self._normalize_biome_id(node.get("biome") or (self.run_state or {}).get("biome"))
            biome_boss = (self.biome_def_by_id.get(node_biome, {}) or {}).get("boss")
            if node_type == "boss" and boss_ids:
                if biome_boss in boss_ids:
                    enemy_ids = [biome_boss]
                else:
                    enemy_ids = [self.rng.choice(boss_ids)]
            else:
                enemy_ids = [self.rng.choice(self._enemy_pool(node))]
            self.run_state["last_node_type"] = node_type
            base_state = CombatState(self.rng, self.run_state, enemy_ids, cards_data=self.cards_data, enemies_data=self.enemies_data)
            self._apply_relic_combat_start_effects(base_state)
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
        elif node_type == "path":
            self.trigger_oracle("path_selected", payload=node)
            self._complete_current_node()
            if not node.get("path_id") or not node.get("path_name"):
                path = SEVEN_PATHS[self.rng.randint(0, len(SEVEN_PATHS) - 1)]
                node["path_id"] = str(path.get("id"))
                node["path_name"] = str(path.get("title"))
                node["path_lore"] = str(path.get("lore"))
            blessing = str(node.get("path_name") or "Camino")
            blessings = self.run_state.setdefault("path_blessings", [])
            if blessing not in blessings:
                blessings.append(blessing)
            self.goto_guide_reward(event_id=str(node.get("path_id") or "seven_paths"))
        elif node_type == "shop":
            self._complete_current_node()
            self.goto_shop()
        elif node_type == "sanctuary":
            self._complete_current_node()
            player = self.run_state.get("player", {}) if isinstance(self.run_state, dict) else {}
            max_hp = max(1, int(player.get("max_hp", 1) or 1))
            heal = max(2, int(round(max_hp * 0.12)))
            player["hp"] = min(max_hp, int(player.get("hp", max_hp) or max_hp) + heal)
            self.apply_run_rewards(xp=6, source="sanctuary_rest")
            print(f"[run] sanctuary heal +{heal} ({player.get('hp', 0)}/{max_hp})")
            self.goto_event()
        elif node_type == "treasure":
            self._complete_current_node()
            self.goto_reward(gold=self.rng.randint(22, 40))
        else:
            self.goto_event()

    def gain_xp(self, amount: int):
        levels = 0
        gain = max(0, int(amount or 0))
        self.debug["xp_last_gain"] = gain
        self.run_state["xp"] += gain
        while self.run_state["level"] < MAX_LEVEL and self.run_state["xp"] >= self.xp_needed_for_level(self.run_state["level"]):
            self.run_state["xp"] -= self.xp_needed_for_level(self.run_state["level"])
            self.run_state["level"] += 1
            levels += 1
        if self.run_state["level"] >= MAX_LEVEL:
            self.run_state["level"] = MAX_LEVEL
            self.run_state["xp"] = min(self.run_state["xp"], self.xp_needed_for_level(MAX_LEVEL))
        if levels:
            self.run_state["levelup_pending"] = self.run_state.get("levelup_pending", 0) + levels
        return levels

    def apply_run_rewards(self, *, gold=0, xp=0, cards=None, relics=None, source="unknown"):
        """Apply run rewards through one stable path with deterministic logging."""
        if not isinstance(self.run_state, dict):
            return {"gold": 0, "xp": 0, "levels": 0, "cards": 0, "relics": 0}

        granted_gold = max(0, int(gold or 0))
        granted_xp = max(0, int(xp or 0))
        card_ids = [str(cid) for cid in list(cards or []) if cid]
        relic_ids = [str(rid) for rid in list(relics or []) if rid]

        if granted_gold:
            self.run_state["gold"] = int(self.run_state.get("gold", 0) or 0) + granted_gold
        levels = self.gain_xp(granted_xp) if granted_xp else 0
        if card_ids:
            self.run_state.setdefault("sideboard", []).extend(card_ids)
        if relic_ids:
            owned = self.run_state.setdefault("relics", [])
            for rid in relic_ids:
                if rid not in owned:
                    owned.append(rid)

        print(
            f"[reward] source={source} gold=+{granted_gold} xp=+{granted_xp} "
            f"levels=+{levels} cards=+{len(card_ids)} relics=+{len(relic_ids)} "
            f"pending_packs={self.run_state.get('levelup_pending', 0)}"
        )
        self._autosave_run(f"rewards:{source}")
        return {"gold": granted_gold, "xp": granted_xp, "levels": levels, "cards": len(card_ids), "relics": len(relic_ids)}

    def on_combat_victory(self):
        self.play_stinger("stinger_victory")
        self._complete_current_node()
        node_type = self.run_state.get("last_node_type", "combat")
        perfect_bonus = 5 if self.current_combat and getattr(self.current_combat, "player_damage_taken", 0) <= 0 else 0

        if node_type == "boss":
            self.apply_run_rewards(xp=100 + perfect_bonus, source="combat_boss")
            self._apply_post_combat_recovery("boss")
            boss_gold = int(round(self.rng.randint(120, 180) * 1.3))
            self.goto_reward(mode="boss_pack", gold=boss_gold)
            return

        self.run_state["combats_won"] = int(self.run_state.get("combats_won", 0)) + 1
        if node_type == "challenge":
            bonus_gold = int(round(self.rng.randint(40, 70) * 1.3))
            xp_gain = 40 + perfect_bonus
        else:
            bonus_gold = int(round(self.rng.randint(20, 35) * 1.3))
            xp_gain = self.rng.randint(15, 25) + perfect_bonus

        self.apply_run_rewards(xp=xp_gain, source=f"combat_{node_type}")
        self._apply_post_combat_recovery(node_type)
        self._apply_relic_noncombat_hook("combat_win")
        enemy = self.current_combat.enemies[0] if self.current_combat and self.current_combat.enemies else None
        self.debug["last_lesson_key"] = getattr(enemy, "fable_lesson_key", "duda") if enemy else "duda"
        self.goto_reward(gold=bonus_gold)

    def consume_levelup_pending(self):
        pending = int(self.run_state.get("levelup_pending", 0) or 0)
        if pending > 0:
            self.run_state["levelup_pending"] = max(0, pending - 1)
        print(f"[reward] consume_levelup_pending remaining={self.run_state.get('levelup_pending', 0)}")
        if self.run_state.get("levelup_pending", 0) > 0:
            self.sm.set(PackOpeningScreen(self))
        else:
            self.goto_map()

    def apply_event_effects(self, effects):
        effects = list(effects or [])
        player = self.run_state["player"]
        rare = any(isinstance(e, dict) and e.get("type") == "gain_relic" for e in effects)
        event_xp = self.rng.randint(7, 8) if rare else self.rng.randint(4, 6)
        total_gold = 0
        total_xp = event_xp
        self.apply_run_rewards(xp=event_xp, source="event_base")
        for effect in effects:
            if not isinstance(effect, dict):
                continue
            effect_type = effect.get("type")
            if effect_type == "lose_gold":
                self.run_state["gold"] = max(0, self.run_state["gold"] - int(effect.get("amount", 0)))
            elif effect_type == "gain_gold":
                base_gain = int(effect.get("amount", 0) or 0)
                gain = int(round(base_gain * 1.2))
                total_gold += max(0, gain)
                self.apply_run_rewards(gold=gain, source="event_gain_gold")
            elif effect_type == "gain_xp":
                gain = int(effect.get("amount", 0) or 0)
                total_xp += max(0, gain)
                self.apply_run_rewards(xp=gain, source="event_gain_xp")
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
                self.apply_run_rewards(cards=[effect.get("card_id", "strike")], source="event_gain_card")
            elif effect_type == "gain_card_random":
                rarity = effect.get("rarity")
                pool = [c.get("id") for c in self.cards_data if c.get("rarity") == rarity and c.get("id")]
                if pool:
                    self.apply_run_rewards(cards=[self.rng.choice(pool)], source="event_gain_card_random")
            elif effect_type == "remove_card_from_deck" and self.run_state["deck"]:
                self.run_state["deck"].pop(0)
            elif effect_type == "gain_relic":
                rid = effect.get("relic_id")
                if rid:
                    self.apply_run_rewards(relics=[rid], source="event_gain_relic")
            elif effect_type == "gain_relic_random":
                rarity = effect.get("rarity")
                pool = [r.get("id") for r in self.relics_data if r.get("rarity") == rarity and r.get("id")]
                if pool:
                    self.apply_run_rewards(relics=[self.rng.choice(pool)], source="event_gain_relic_random")
            else:
                print(f"[events] warning: unsupported effect type '{effect_type}'")
        print(f"[events] applied total_gold=+{total_gold} total_xp=+{total_xp}")

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
            self._loading_step("Reset aplicado. Reiniciando...", 0.15)
            self.request_restart("regen")
            return

        self._draw_progress_splash("Regenerando Trama...", "Reset Autogen Total")
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
        self.visual_engine.ensure_core(force=bool(self.user_settings.get("force_regen_art", False)))
        self.user_settings["force_regen_music"] = False
        self.user_settings["update_manifests"] = False
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass
        self.music = MusicManager()
        self.sfx = SFXManager()
        self.sfx.set_volume(self.user_settings.get("sfx_volume", 0.7))
        self.music.set_volume(self.user_settings.get("music_volume", 0.5))
        self.music.set_muted(self.user_settings.get("music_muted", self.user_settings.get("music_mute", False)))
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
        self.user_settings["dev_skip_intro"] = bool(self.user_settings.get("dev_skip_intro", False))
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
        ok_enemies = f"OK({counts.get('enemies',0)})" if counts.get('enemies',0)==31 else f"FALLBACK({counts.get('enemies',0)})"
        ok_boss = f"OK({counts.get('bosses',0)})" if counts.get('bosses',0)==4 else f"FALLBACK({counts.get('bosses',0)})"
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
        self._loading_step("Reset aplicado. Regenerando Trama...", 0.02)
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
        self.biome_defs = self._load_biome_defs()
        self.biome_def_by_id = {str(b.get("id")).lower(): b for b in self.biome_defs if isinstance(b, dict) and b.get("id")}
        self.cards_data = self._load_cards_data()
        self.card_defs = {c["id"]: c for c in self.cards_data}
        self.enemies_data = self._load_enemies_data()
        self.ensure_assets(progress_cb=self._loading_step)
        self._log_card_art_status()
        content_report = self._validate_content_cached()
        self.debug["content_validation"] = content_report
        print(f"[boot] validate_content status={content_report.get('status')} cards={content_report.get('cards')} summary_ok={content_report.get('summary_ok')} can_play_ok={content_report.get('can_play_ok')} placeholders={content_report.get('placeholders')} issues={len(content_report.get('issues', []))}")
        self.audio_pipeline.ensure_music_assets(self.user_settings, progress_cb=self._loading_step)
        self.visual_engine.ensure_core(force=bool(self.user_settings.get("force_regen_art", False)))
        self._set_boot_screen()
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
            if hasattr(self, "oracle_ui") and self.oracle_ui is not None:
                self.oracle_ui.update(dt)
            self.sm.update(dt)
            self.renderer.internal.fill((8, 8, 14))
            self.sm.render(self.renderer.internal)
            if hasattr(self, "oracle_ui") and self.oracle_ui is not None:
                self.oracle_ui.render(self.renderer.internal, self)
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
                    if hasattr(app, "oracle_ui") and app.oracle_ui is not None:
                        app.oracle_ui.render(app.renderer.internal, app)
                    app.renderer.present()
                    app.clock.tick(FPS)
            except Exception:
                pass
        raise



