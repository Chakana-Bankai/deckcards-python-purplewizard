from __future__ import annotations

import traceback
import shutil
import json
import time

import pygame

from game.audio.music_manager import MusicManager
from game.audio.sfx_manager import SFXManager
from game.combat.card import CardDef, CardInstance
from game.combat.combat_state import CombatState
from game.content.card_art_generator import CardArtGenerator, export_prompts
from game.content.enemy_art_generator import EnemyArtGenerator
from game.content.background_generator import BackgroundGenerator
from game.core.bootstrap_assets import ensure_placeholder_assets, ensure_bgm_assets
from game.core.localization import LocalizationManager
from game.core.paths import data_dir, assets_dir
from game.core.rng import SeededRNG
from game.core.safe_io import load_json
from game.core.settings_store import load_settings, save_settings
from game.core.state_machine import StateMachine
from game.settings import FPS, INTERNAL_HEIGHT, INTERNAL_WIDTH
from game.qa.runner import QARunner
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
        # font pipeline
        fonts_dir = data_dir().parent / "assets" / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)
        font_target = fonts_dir / "DejaVuSans.ttf"
        if not font_target.exists():
            src = pygame.font.match_font("dejavusans") or pygame.font.match_font("arial")
            if src:
                try:
                    shutil.copy(src, font_target)
                except Exception:
                    pass
        font_path = str(font_target) if font_target.exists() else None
        self.font = pygame.font.Font(font_path, 24) if font_path else pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.Font(font_path, 22) if font_path else pygame.font.SysFont("arial", 22)
        self.tiny_font = pygame.font.Font(font_path, 18) if font_path else pygame.font.SysFont("arial", 18)
        self.big_font = pygame.font.Font(font_path, 34) if font_path else pygame.font.SysFont("arial", 34, bold=True)
        self.card_text_font = pygame.font.Font(font_path, 20) if font_path else pygame.font.SysFont("arial", 20)
        self.card_title_font = pygame.font.Font(font_path, 26) if font_path else pygame.font.SysFont("arial", 26, bold=True)
        self.map_font = pygame.font.Font(font_path, 24) if font_path else pygame.font.SysFont("arial", 24)
        self.sm = StateMachine()
        self.run_state = None
        self.node_lookup = {}
        self.current_node_id = None
        self.debug_overlay = False
        self.debug = {"last_ui_event": "-", "hovered_card_id": "-", "selected_card_id": "-", "target_mode": False, "combat_end_turn_button_visible": False, "combat_status_button_visible": False, "combat_end_turn_rect": "-", "combat_status_rect": "-", "enemy_intent": "-", "art_regenerated": 0}

        self.cards_data = self._load_cards_data()
        self.card_defs = {c["id"]: c for c in self.cards_data}
        self.enemies_data = self._load_enemies_data()
        self.events_data = self._load_events_data()
        self.relics_data = self._load_relics_data()
        self.lore_data = self._load_lore_data()
        self.design_doc = self._load_design_doc()
        self.canonical_design_source = str(data_dir() / "design" / "gdd_chakana_purple_wizard.txt")
        print(f"[load] cards={len(self.cards_data)} enemies={len(self.enemies_data)} events={len(self.events_data)} relics={len(self.relics_data)}")
        self.art_gen = CardArtGenerator()
        self.enemy_art_gen = EnemyArtGenerator()
        self.bg_gen = BackgroundGenerator()
        self.autogen_art_mode = self.user_settings.get("autogen_art_mode", "missing_only")
        self.ensure_assets()
        print("[load] card/enemy art verified")
        self.debug["art_regenerated"] = self.art_gen.generated_count + self.art_gen.replaced_count

        self.validate_navigation_methods()
        pygame.display.set_caption(self.loc.t("game_title"))
        self.sm.set(MenuScreen(self))
        self.music.play_for("menu")

    def _load_cards_data(self):
        cards = load_json(data_dir() / "cards.json", default=[])
        if not isinstance(cards, list):
            cards = []
        by_id = {c.get("id"): c for c in cards if isinstance(c, dict) and c.get("id")}
        for base in DEFAULT_CARDS:
            by_id.setdefault(base["id"], base)
        return list(by_id.values())

    def _load_enemies_data(self):
        enemies = load_json(data_dir() / "enemies.json", default=[DEFAULT_ENEMY])
        valid = [e for e in enemies if isinstance(e, dict) and e.get("id")] if isinstance(enemies, list) else []
        return valid or [DEFAULT_ENEMY]

    def _load_events_data(self):
        events = load_json(data_dir() / "events.json", default=[])
        return events if isinstance(events, list) else []

    def _load_relics_data(self):
        relics = load_json(data_dir() / "relics.json", default=[])
        return relics if isinstance(relics, list) else []

    def _load_lore_data(self):
        lore_dir = data_dir() / "lore"
        dialogues = load_json(lore_dir / "dialogues.json", default={})
        lore_txt = ""
        world_txt = ""
        lore_events = load_json(lore_dir / "events.json", default={})
        lore_enemies = load_json(lore_dir / "enemies.json", default={})
        try:
            lore_txt = (lore_dir / "chakana_lore.txt").read_text(encoding="utf-8")
        except Exception:
            lore_txt = ""
        try:
            world_txt = (lore_dir / "world.txt").read_text(encoding="utf-8")
        except Exception:
            world_txt = ""
        if not isinstance(dialogues, dict):
            dialogues = {}
        dialogues["lore_text"] = lore_txt
        dialogues["world_text"] = world_txt
        dialogues["event_fragments"] = lore_events.get("fragments", []) if isinstance(lore_events, dict) else []
        dialogues["enemy_lore"] = lore_enemies if isinstance(lore_enemies, dict) else {}
        return dialogues

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

    def ensure_assets(self):
        a = assets_dir()
        (a / "music").mkdir(parents=True, exist_ok=True)
        (a / "sprites" / "cards").mkdir(parents=True, exist_ok=True)
        (a / "backgrounds").mkdir(parents=True, exist_ok=True)
        ensure_placeholder_assets([c.get("id", "strike") for c in self.cards_data], [e.get("id", "dummy") for e in self.enemies_data])
        ensure_bgm_assets(force_regen=False)
        for c in self.cards_data:
            self.art_gen.ensure_art(c.get("id", "strike"), c.get("tags", []), c.get("rarity", "common"), self.autogen_art_mode)
        for e in self.enemies_data:
            self.enemy_art_gen.ensure_art(e.get("id", "dummy"), self.autogen_art_mode)
        for biome in self.bg_gen.BIOMES:
            self.bg_gen.get_layers(biome, 2026)

    def validate_navigation_methods(self):
        required = ["goto_menu", "goto_map", "goto_combat", "goto_reward", "goto_shop", "goto_event", "goto_deck", "goto_settings"]
        missing = [m for m in required if not hasattr(self, m)]
        if missing:
            raise RuntimeError(f"Missing navigation methods: {', '.join(missing)}")

    def toggle_language(self):
        self.loc.load("en" if self.loc.current_lang == "es" else "es")
        self.user_settings["language"] = self.loc.current_lang
        self.validate_navigation_methods()
        pygame.display.set_caption(self.loc.t("game_title"))

    def goto_menu(self):
        self.sm.set(MenuScreen(self))
        self.music.play_for("menu")

    def goto_settings(self):
        self.sm.set(SettingsScreen(self))

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
            "xp": 0,
            "level": 1,
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
        type_cycle = ["combat", "event", "challenge", "shop", "event", "boss"]
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
            self.music.play_for("event")
            return
        self.debug["map_available_count"] = self.available_nodes_count() if self.node_lookup else 0
        self.debug["current_node_id"] = self.current_node_id or "-"
        self.sm.set(MapScreen(self))
        self.music.play_for("map")

    def goto_combat(self, combat_state, is_boss=False):
        self.current_combat = combat_state
        self.sm.set(CombatScreen(self, combat_state, is_boss=is_boss))
        self.music.play_for("boss" if is_boss else "combat")

    def goto_reward(self, picks=None, gold=None):
        if picks is None or gold is None:
            unlock_level = self.run_state.get("level", 1) if self.run_state else 1
            rarities = {"basic", "common"} if unlock_level < 2 else {"common", "uncommon", "rare"}
            pool = [c for c in self.cards_data if c.get("rarity") in rarities] or self.cards_data
            picks = [CardInstance(CardDef(**(self.rng.choice(pool) or DEFAULT_CARDS[0]))) for _ in range(3)]
            gold = self.rng.randint(10, 25)
        self.sm.set(RewardScreen(self, picks, gold))

    def goto_shop(self):
        pool = [c for c in self.cards_data if c.get("rarity") in {"common", "uncommon"}] or self.cards_data
        self.sm.set(ShopScreen(self, self.rng.choice(pool) or DEFAULT_CARDS[0]))
        self.music.play_for("event")

    def goto_event(self):
        event = self.rng.choice(self.events_data) if self.events_data else {"title_key": "map_title", "body_key": "lore_tagline", "choices": [{"text_key": "event_continue", "effects": []}]}
        self.sm.set(EventScreen(self, event))
        self.music.play_for("event")

    def run_qa_mode(self):
        results = QARunner(self).run_all()
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
        node["state"] = "completed"
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

    def _enemy_pool(self):
        ids = [e["id"] for e in self.enemies_data if e.get("id") != "inverse_weaver"]
        return ids or [DEFAULT_ENEMY["id"]]

    def enter_node(self, node):
        node_type = node.get("type", "combat")
        if node_type in {"combat", "challenge", "boss"}:
            enemy_ids = ["inverse_weaver"] if node_type == "boss" else [self.rng.choice(self._enemy_pool())]
            self.run_state["last_node_type"] = node_type
            self.current_combat = CombatState(self.rng, self.run_state, enemy_ids)
            self.goto_combat(self.current_combat, is_boss=node_type == "boss")
        elif node_type == "shop":
            self.goto_shop()
        else:
            self.goto_event()

    def gain_xp(self, amount: int):
        levels = 0
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
            self.music.play_for("ending")
            self.sm.set(EndScreen(self))
            return
        bonus_gold = self.rng.randint(16, 30) if node_type == "challenge" else self.rng.randint(10, 25)
        self.gain_xp(12)
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
        self.gain_xp(6)
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
            if n.get("state") != "completed":
                n["state"] = "available"
                print("[map] recovery unlocked unfinished node", n.get("id"))
                return
        node_id = f"recovery_{len(self.node_lookup)}"
        new_node = {"id": node_id, "col": 0, "x": INTERNAL_WIDTH // 2, "y": INTERNAL_HEIGHT // 2, "type": "event", "next": [], "state": "available"}
        self.node_lookup[node_id] = new_node
        self.run_state["map"].append([new_node])
        print("[map] recovery created Camino Abierto")

    def regenerate_music(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        ensure_bgm_assets(force_regen=True)
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass
        self.music = MusicManager()
        self.music.set_volume(self.user_settings.get("music_volume", 0.5))
        self.music.set_muted(self.user_settings.get("music_muted", self.user_settings.get("music_mute", False)))
        self.music._checked_silence.clear()
        self.music.play_for("menu")

    def regenerate_card_art_with_cleanup(self):
        manifest_path = data_dir() / "art_manifest.json"
        manifest = load_json(manifest_path, default={})
        cards_dir = assets_dir() / "sprites" / "cards"
        if isinstance(manifest, dict):
            for cid in manifest.keys():
                p = cards_dir / f"{cid}.png"
                if p.exists():
                    p.unlink()
        self.regenerate_card_art()

    def set_debug(self, **kwargs):
        self.debug.update(kwargs)

    def regenerate_card_art(self):
        total = len(self.cards_data)
        manifest = {}
        for i, c in enumerate(self.cards_data, start=1):
            cid = c.get("id", "strike")
            self.art_gen.ensure_art(cid, c.get("tags", []), c.get("rarity", "common"), "force_regen")
            manifest[cid] = {
                "prompt_hash": str(abs(hash(cid))),
                "generated_at": int(time.time()),
                "seed": str(abs(hash(cid)) % 1000000),
            }
            self.set_debug(last_ui_event=f"regen_art:{i}/{total}")
        (data_dir() / "art_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
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
        save_settings(self.user_settings)

    def draw_debug_overlay(self):
        if not self.debug_overlay:
            return
        x,y,nw,nh,scale = self.renderer._viewport()
        lines = [
            f"screen={self.sm.current.__class__.__name__ if self.sm.current else '-'}",
            f"internal_res={INTERNAL_WIDTH}x{INTERNAL_HEIGHT}",
            f"scale={scale:.3f} letterbox=({x},{y})",
            f"hovered_card={self.debug.get('hovered_card_id','-')} target_mode={self.debug.get('target_mode','-')}",
            f"BGM track={self.music.debug_state()}",
            f"design={self.canonical_design_source}",
            f"enemy_hp={self.debug.get('enemies_hp','-')} intent={self.debug.get('enemy_intent','-')}",
            f"card_art_regenerated={self.debug.get('art_regenerated','0')}",
            f"map.available_count={self.debug.get('map_available_count','-')} current_node_id={self.debug.get('current_node_id','-')}",
            f"next_nodes={self.debug.get('next_nodes_ids','-')}",
        ]
        panel = pygame.Surface((980, 170), pygame.SRCALPHA)
        panel.fill((0,0,0,170))
        self.renderer.internal.blit(panel, (8,8))
        for i,line in enumerate(lines):
            self.renderer.internal.blit(self.tiny_font.render(line, True, (240,240,240)), (16, 16+i*20))

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
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
                    self.debug_overlay = not self.debug_overlay
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                    self.run_qa_mode()
                else:
                    self.sm.handle_event(event)
            self.sm.update(dt)
            self.sm.render(self.renderer.internal)
            self.draw_debug_overlay()
            self.renderer.present()
        pygame.quit()


if __name__ == "__main__":
    app = None
    try:
        app = App()
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
