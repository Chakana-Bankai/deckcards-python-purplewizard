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
from game.core.lore_service import LoreService
from game.core.content_service import ContentService
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
from game.version import VERSION
from game.art.gen_art32 import GEN_ART_VERSION, GEN_BIOME_VERSION

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
        self.debug = {"last_ui_event": "-", "hovered_card_id": "-", "selected_card_id": "-", "target_mode": False, "combat_end_turn_button_visible": False, "combat_status_button_visible": False, "combat_end_turn_rect": "-", "combat_status_rect": "-", "enemy_intent": "-", "art_regenerated": 0, "xp_last_gain": 0}

        self.content = ContentService()
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
        self.lore_data = self.lore_service.data
        self.debug["lore_status"] = self.lore_service.status
        self.debug["lore_paths"] = ",".join(str(v) for v in self.lore_service.paths.values())
        self.design_doc = self._load_design_doc()
        self.canonical_design_source = str(data_dir() / "design" / "gdd_chakana_purple_wizard.txt")
        print(f"[load] cards={len(self.cards_data)} enemies={len(self.enemies_data)} events={len(self.events_data)} relics={len(self.relics_data)}")
        self.art_gen = CardArtGenerator()
        self.enemy_art_gen = EnemyArtGenerator()
        self.bg_gen = BackgroundGenerator()
        self.autogen_art_mode = self.user_settings.get("autogen_art_mode", "missing_only")
        self._apply_dev_reset_if_enabled()
        self.ensure_assets()
        print("[load] card/enemy art verified")
        self.debug["art_regenerated"] = self.art_gen.generated_count + self.art_gen.replaced_count

        self.validate_navigation_methods()
        pygame.display.set_caption(self.loc.t("game_title"))
        self.sm.set(MenuScreen(self))
        self.music.play_for("menu")

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
                "target": "enemy",
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

    def ensure_assets(self):
        a = assets_dir()
        (a / "music").mkdir(parents=True, exist_ok=True)
        (a / "sprites" / "cards").mkdir(parents=True, exist_ok=True)
        (a / "sprites" / "enemies").mkdir(parents=True, exist_ok=True)
        (a / "sprites" / "biomes").mkdir(parents=True, exist_ok=True)
        (a / "sfx" / "generated").mkdir(parents=True, exist_ok=True)
        ensure_placeholder_assets([c.get("id", "strike") for c in self.cards_data], [e.get("id", "dummy") for e in self.enemies_data])
        ensure_bgm_assets(force_regen=False)

        prompt_data = load_json(data_dir() / "card_prompts.json", default={})
        if not isinstance(prompt_data, dict) or len(prompt_data) != len(self.cards_data):
            export_prompts(self.cards_data, self.enemies_data)
            prompt_data = load_json(data_dir() / "card_prompts.json", default={}) if isinstance(load_json(data_dir() / "card_prompts.json", default={}), dict) else {}

        art_manifest = load_json(data_dir() / "art_manifest.json", default={})
        if not isinstance(art_manifest, dict):
            art_manifest = {}
        for c in self.cards_data:
            cid = c.get("id", "unknown")
            path = a / "sprites" / "cards" / f"{cid}.png"
            mode = "missing_only"
            if self.user_settings.get("force_regen_art", False):
                mode = "force_regen"
            if not path.exists() or cid not in art_manifest:
                pentry = prompt_data.get(cid, {}) if isinstance(prompt_data, dict) else {}
                self.art_gen.ensure_art(cid, c.get("tags", []), c.get("rarity", "common"), mode, family=pentry.get("family"), symbol=pentry.get("symbol"))
            art_manifest[cid] = {"path": str(path), "hash": str(abs(hash(cid))), "generator_version": GEN_ART_VERSION}

        for e in self.enemies_data:
            eid = e.get("id", "dummy")
            ep = a / "sprites" / "enemies" / f"{eid}.png"
            emode = "force_regen" if self.user_settings.get("force_regen_art", False) else "missing_only"
            if not ep.exists() or self.user_settings.get("force_regen_art", False):
                self.enemy_art_gen.ensure_art(eid, emode, tier=e.get("tier", "common"), biome=e.get("biome", "ukhu"))
            art_manifest[f"enemy:{eid}"] = {"path": str(ep), "hash": str(abs(hash(eid))), "generator_version": GEN_ART_VERSION}

        biome_manifest = {}
        for biome in self.bg_gen.BIOMES:
            self.bg_gen.get_layers(biome, 2026)
            bdir = a / "sprites" / "biomes" / biome.lower().replace(" ", "_")
            biome_manifest[biome] = {
                "bg": str(bdir / "bg.png"), "mg": str(bdir / "mg.png"), "fg": str(bdir / "fg.png"),
                "generator_version": GEN_BIOME_VERSION,
            }

        (data_dir() / "art_manifest.json").write_text(json.dumps(art_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (data_dir() / "biome_manifest.json").write_text(json.dumps(biome_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (data_dir() / "prompt_manifest.json").write_text(json.dumps({"count": len(self.cards_data), "generator_version": GEN_ART_VERSION}, ensure_ascii=False, indent=2), encoding="utf-8")
        self.user_settings["force_regen_art"] = False

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
            self.music.play_for("reward")
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
        self.sm.set(RewardScreen(self, picks, gold, xp_gained=self.debug.get("xp_last_gain", 0)))
        self.music.play_for("reward")

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
        ids = [e["id"] for e in self.enemies_data if e.get("id") and e.get("tier") != "boss"]
        return ids or [DEFAULT_ENEMY["id"]]

    def enter_node(self, node):
        node_type = node.get("type", "combat")
        if node_type in {"combat", "challenge", "boss"}:
            boss_ids = [b.get("id") for b in self.content.bosses if isinstance(b, dict) and b.get("id")]
            enemy_ids = [self.rng.choice(boss_ids)] if node_type == "boss" and boss_ids else [self.rng.choice(self._enemy_pool())]
            self.run_state["last_node_type"] = node_type
            self.current_combat = CombatState(self.rng, self.run_state, enemy_ids, cards_data=self.cards_data, enemies_data=self.enemies_data)
            self.goto_combat(self.current_combat, is_boss=node_type == "boss")
        elif node_type == "shop":
            self.goto_shop()
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
            self.music.play_for("ending")
            self.sm.set(EndScreen(self))
            return
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
            if n.get("state") != "completed":
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
        regen_flag = data_dir() / "flags" / "regen_on_boot.flag"
        if self.user_settings.get("dev_reset_autogen_on_boot", False) or regen_flag.exists():
            self.reset_autogen_total(mark_only=False)
            if regen_flag.exists():
                regen_flag.unlink()
            self.user_settings["dev_reset_autogen_on_boot"] = False
            self.user_settings["force_regen_art"] = True
            save_settings(self.user_settings)

    def reset_autogen_total(self, mark_only: bool = True):
        flags_dir = data_dir() / "flags"
        flags_dir.mkdir(parents=True, exist_ok=True)
        if mark_only:
            (flags_dir / "regen_on_boot.flag").write_text("1", encoding="utf-8")
            return
        self._draw_progress_splash("Regenerando Trama…", "Reset Autogen Total")
        targets = [
            assets_dir() / "sprites" / "cards",
            assets_dir() / "sprites" / "enemies",
            assets_dir() / "sprites" / "biomes",
            assets_dir() / "music",
            assets_dir() / "sfx" / "generated",
        ]
        for td in targets:
            if td.exists():
                for f in td.rglob("*"):
                    if f.is_file():
                        f.unlink()
        for p in [data_dir() / "art_manifest.json", data_dir() / "biome_manifest.json", data_dir() / "bgm_manifest.json", data_dir() / "prompt_manifest.json", data_dir() / "card_prompts.json"]:
            if p.exists():
                p.unlink()

    def regenerate_art_all(self):
        self.user_settings["force_regen_art"] = True
        self.ensure_assets()
        self.assets._cache.clear()

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
        self.music._manifest = self.music._load_manifest()
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
        self.user_settings["dev_reset_autogen_on_boot"] = bool(self.user_settings.get("dev_reset_autogen_on_boot", False))
        self.user_settings["fx_vignette"] = bool(self.user_settings.get("fx_vignette", True))
        self.user_settings["fx_scanlines"] = bool(self.user_settings.get("fx_scanlines", False))
        self.user_settings["fx_glow"] = bool(self.user_settings.get("fx_glow", True))
        self.user_settings["fx_particles"] = bool(self.user_settings.get("fx_particles", True))
        self.user_settings["force_regen_art"] = bool(self.user_settings.get("force_regen_art", False))
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
            self.music.tick()
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
