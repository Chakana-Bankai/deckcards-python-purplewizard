from __future__ import annotations

import traceback

import pygame

from game.audio.music_manager import MusicManager
from game.audio.sfx_manager import SFXManager
from game.combat.card import CardDef, CardInstance
from game.combat.combat_state import CombatState
from game.content.card_art_generator import CardArtGenerator, export_prompts
from game.core.bootstrap_assets import ensure_placeholder_assets
from game.core.localization import LocalizationManager
from game.core.paths import data_dir
from game.core.rng import SeededRNG
from game.core.safe_io import load_json
from game.core.state_machine import StateMachine
from game.settings import FPS
from game.ui.render import AssetManager, Renderer
from game.ui.screens.combat import CombatScreen
from game.ui.screens.deck import DeckScreen
from game.ui.screens.error import ErrorScreen
from game.ui.screens.event import EventScreen
from game.ui.screens.map import MapScreen
from game.ui.screens.menu import MenuScreen
from game.ui.screens.reward import RewardScreen
from game.ui.screens.settings import SettingsScreen
from game.ui.screens.shop import ShopScreen

DEFAULT_CARDS = [
    {"id": "strike", "name_key": "card_strike_name", "text_key": "card_strike_desc", "rarity": "basic", "cost": 1, "target": "enemy", "tags": ["attack"], "effects": [{"type": "damage", "amount": 6}]},
    {"id": "defend", "name_key": "card_defend_name", "text_key": "card_defend_desc", "rarity": "basic", "cost": 1, "target": "self", "tags": ["skill"], "effects": [{"type": "block", "amount": 5}]},
]
DEFAULT_ENEMY = {"id": "dummy", "name_key": "enemy_voidling_name", "hp": [20, 20], "pattern": [{"intent": "attack", "value": [5, 5]}]}


class App:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            print("[audio] mixer disabled")

        self.clock = pygame.time.Clock()
        self.running = True
        self.rng = SeededRNG(1337)
        self.loc = LocalizationManager("es")
        self.renderer = Renderer()
        self.assets = AssetManager()
        self.sfx = SFXManager()
        self.music = MusicManager()
        self.font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 18)
        self.tiny_font = pygame.font.SysFont("arial", 15)
        self.big_font = pygame.font.SysFont("arial", 42, bold=True)
        self.sm = StateMachine()
        self.run_state = None
        self.node_lookup = {}
        self.current_node_id = None

        self.cards_data = self._load_cards_data()
        self.card_defs = {c["id"]: c for c in self.cards_data}
        self.enemies_data = self._load_enemies_data()
        self.events_data = self._load_events_data()
        self.relics_data = self._load_relics_data()
        ensure_placeholder_assets([c.get("id", "strike") for c in self.cards_data], [e.get("id", "dummy") for e in self.enemies_data])
        self.art_gen = CardArtGenerator()
        for c in self.cards_data:
            self.art_gen.ensure_art(c.get("id", "strike"), c.get("tags", []))
        export_prompts(self.cards_data)

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

    def toggle_language(self):
        self.loc.load("en" if self.loc.current_lang == "es" else "es")
        pygame.display.set_caption(self.loc.t("game_title"))

    def goto_menu(self):
        self.sm.set(MenuScreen(self))
        self.music.play_for("menu")

    def goto_settings(self):
        self.sm.set(SettingsScreen(self))

    def goto_deck(self):
        self.sm.set(DeckScreen(self))

    def new_run(self):
        self.run_state = {
            "gold": 80,
            "relics": ["violet_seal"],
            "player": {"hp": 70, "max_hp": 70, "block": 0, "energy": 3, "rupture": 0, "statuses": {}},
            "deck": ["strike"] * 5 + ["defend"] * 5,
            "sideboard": [],
            "map": self.generate_map(),
            "xp": 0,
            "level": 1,
            "settings": {"timer_on": False, "turn_time": 30, "music_muted": False},
        }
        self.goto_map()

    def generate_map(self):
        columns = 6
        by_col = []
        self.node_lookup = {}
        type_cycle = ["combat", "event", "combat", "shop", "event", "boss"]
        for col in range(columns):
            count = 1 if col in (0, columns - 1) else 3
            col_nodes = []
            for row in range(count):
                node_id = f"{col}_{row}"
                y = 160 + row * 160 if count > 1 else 320
                node = {"id": node_id, "col": col, "x": 120 + col * 205, "y": y, "type": type_cycle[col], "next": [], "state": "available" if col == 0 else "locked"}
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
        self.sm.set(MapScreen(self))
        self.music.play_for("map")

    def select_map_node(self, node):
        self.current_node_id = node["id"]
        node["state"] = "current"
        self.enter_node(node)

    def _complete_current_node(self):
        if not self.current_node_id:
            return
        node = self.node_lookup.get(self.current_node_id)
        if not node:
            return
        node["state"] = "completed"
        for next_id in node.get("next", []):
            nxt = self.node_lookup.get(next_id)
            if nxt and nxt["state"] == "locked":
                nxt["state"] = "available"

    def _enemy_pool(self):
        ids = [e["id"] for e in self.enemies_data if e.get("id") != "inverse_weaver"]
        return ids or [DEFAULT_ENEMY["id"]]

    def enter_node(self, node):
        node_type = node.get("type", "combat")
        if node_type in {"combat", "boss"}:
            enemy_ids = ["inverse_weaver"] if node_type == "boss" else [self.rng.choice(self._enemy_pool())]
            self.current_combat = CombatState(self.rng, self.run_state, enemy_ids)
            self.sm.set(CombatScreen(self, self.current_combat, is_boss=node_type == "boss"))
            self.music.play_for("boss" if node_type == "boss" else "combat")
        elif node_type == "shop":
            pool = [c for c in self.cards_data if c.get("rarity") in {"common", "uncommon"}] or self.cards_data
            self.sm.set(ShopScreen(self, self.rng.choice(pool) or DEFAULT_CARDS[0]))
            self.music.play_for("event")
        else:
            event = self.rng.choice(self.events_data) if self.events_data else {"title_key": "map_title", "body_key": "lore_tagline", "choices": [{"text_key": "event_continue", "effects": []}]}
            self.sm.set(EventScreen(self, event))
            self.music.play_for("event")

    def gain_xp(self, amount: int):
        self.run_state["xp"] += amount
        needed = self.run_state["level"] * 20
        while self.run_state["xp"] >= needed:
            self.run_state["xp"] -= needed
            self.run_state["level"] += 1
            needed = self.run_state["level"] * 20

    def on_combat_victory(self):
        self._complete_current_node()
        self.gain_xp(12)
        unlock_level = self.run_state["level"]
        rarities = {"basic", "common"} if unlock_level < 2 else {"common", "uncommon", "rare"}
        pool = [c for c in self.cards_data if c.get("rarity") in rarities] or self.cards_data
        picks = [CardInstance(CardDef(**(self.rng.choice(pool) or DEFAULT_CARDS[0]))) for _ in range(3)]
        self.sm.set(RewardScreen(self, picks, self.rng.randint(10, 25)))

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
                else:
                    self.sm.handle_event(event)
            self.sm.update(dt)
            self.sm.render(self.renderer.internal)
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
