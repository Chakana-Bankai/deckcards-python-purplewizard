from __future__ import annotations

import traceback

import pygame

from game.combat.card import CardDef, CardInstance
from game.combat.combat_state import CombatState
from game.core.localization import LocalizationManager
from game.core.paths import data_dir
from game.core.rng import SeededRNG
from game.core.safe_io import load_json
from game.core.state_machine import StateMachine
from game.settings import FPS
from game.ui.render import Renderer, SoundManager
from game.ui.screens.combat import CombatScreen
from game.ui.screens.error import ErrorScreen
from game.ui.screens.event import EventScreen
from game.ui.screens.map import MapScreen
from game.ui.screens.menu import MenuScreen
from game.ui.screens.reward import RewardScreen
from game.ui.screens.shop import ShopScreen

DEFAULT_LOCALIZATION_KEYS = [
    "game_title",
    "menu_play",
    "menu_exit",
    "map_title",
    "button_end_turn",
    "reward_title",
    "shop_title",
]

DEFAULT_CARDS = [
    {
        "id": "strike",
        "name_key": "card_strike_name",
        "text_key": "card_strike_desc",
        "rarity": "basic",
        "cost": 1,
        "target": "enemy",
        "tags": ["attack"],
        "effects": [{"type": "damage", "amount": 6}],
    },
    {
        "id": "defend",
        "name_key": "card_defend_name",
        "text_key": "card_defend_desc",
        "rarity": "basic",
        "cost": 1,
        "target": "self",
        "tags": ["skill"],
        "effects": [{"type": "block", "amount": 5}],
    },
]

DEFAULT_ENEMY = {
    "id": "dummy",
    "name_key": "enemy_voidling_name",
    "hp": [20, 20],
    "pattern": [{"intent": "attack", "value": [5, 5]}],
}


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
        self.sfx = SoundManager()
        self.font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 18)
        self.big_font = pygame.font.SysFont("arial", 42, bold=True)
        self.sm = StateMachine()
        self.run_state = None

        self.cards_data = self._load_cards_data()
        self.enemies_data = self._load_enemies_data()
        self.events_data = self._load_events_data()
        self.relics_data = self._load_relics_data()
        self._sanity_check()

        pygame.display.set_caption(self.loc.t("game_title"))
        self.sm.set(MenuScreen(self))

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
        if not isinstance(enemies, list) or not enemies:
            return [DEFAULT_ENEMY]
        valid = [e for e in enemies if isinstance(e, dict) and e.get("id")]
        return valid or [DEFAULT_ENEMY]

    def _load_events_data(self):
        events = load_json(data_dir() / "events.json", default=[])
        return events if isinstance(events, list) else []

    def _load_relics_data(self):
        relics = load_json(data_dir() / "relics.json", default=[])
        return relics if isinstance(relics, list) else []

    def _sanity_check(self):
        missing = [k for k in DEFAULT_LOCALIZATION_KEYS if self.loc.t(k) == k]
        if missing:
            print(f"[sanity] localization missing keys: {missing}")
        card_ids = {c.get("id") for c in self.cards_data if isinstance(c, dict)}
        for required in ("strike", "defend"):
            if required not in card_ids:
                fallback = next(c for c in DEFAULT_CARDS if c["id"] == required)
                self.cards_data.append(fallback)
                print(f"[sanity] injected missing card '{required}'")

    def toggle_language(self):
        self.loc.load("en" if self.loc.current_lang == "es" else "es")
        pygame.display.set_caption(self.loc.t("game_title"))

    def goto_menu(self):
        self.sm.set(MenuScreen(self))

    def new_run(self):
        starter = ["strike"] * 5 + ["defend"] * 5
        self.run_state = {
            "gold": 80,
            "relics": ["violet_seal"],
            "player": {"hp": 70, "max_hp": 70, "block": 0, "energy": 3, "rupture": 0, "statuses": {}},
            "deck": starter,
            "map": self.generate_map(),
            "map_index": 0,
        }
        self.goto_map()

    def generate_map(self):
        columns = 10
        graph = []
        node_types = ["combat", "combat", "event", "combat", "shop", "combat", "event", "combat", "combat", "boss"]
        for col_idx in range(columns):
            count = 1 if col_idx in (0, columns - 1) else 2
            col_nodes = []
            for row_idx in range(count):
                node_id = f"{col_idx}_{row_idx}"
                y = 180 + row_idx * 220
                col_nodes.append({"id": node_id, "x": 120 + col_idx * 115, "y": y, "type": node_types[col_idx], "next": [], "available": col_idx == 0})
            graph.append(col_nodes)
        for col_idx in range(columns - 1):
            next_ids = [n["id"] for n in graph[col_idx + 1]]
            for node in graph[col_idx]:
                node["next"] = next_ids
        return graph

    def goto_map(self):
        self.sm.set(MapScreen(self))

    def _enemy_pool(self):
        ids = [e["id"] for e in self.enemies_data if e.get("id") != "inverse_weaver"]
        return ids or [DEFAULT_ENEMY["id"]]

    def enter_node(self, node):
        node_type = node.get("type", "combat")
        if node_type in {"combat", "boss"}:
            enemy_ids = ["inverse_weaver"] if node_type == "boss" else [self.rng.choice(self._enemy_pool())]
            self.current_combat = CombatState(self.rng, self.run_state, enemy_ids)
            self.sm.set(CombatScreen(self, self.current_combat))
        elif node_type == "shop":
            pool = [c for c in self.cards_data if c.get("rarity") in {"common", "uncommon"}] or self.cards_data
            self.sm.set(ShopScreen(self, self.rng.choice(pool) or DEFAULT_CARDS[0]))
        else:
            event = self.rng.choice(self.events_data) if self.events_data else {"title_key": "map_title", "body_key": "lore_tagline", "choices": [{"text_key": "event_continue", "effects": []}]}
            self.sm.set(EventScreen(self, event))

    def on_combat_victory(self):
        pool = [c for c in self.cards_data if c.get("rarity") != "basic"] or self.cards_data
        picks = [CardInstance(CardDef(**(self.rng.choice(pool) or DEFAULT_CARDS[0]))) for _ in range(3)]
        gold = self.rng.randint(10, 25)
        self.sm.set(RewardScreen(self, picks, gold))

    def apply_event_effects(self, effects):
        player = self.run_state["player"]
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
                amount = int(effect.get("amount", 0))
                player["max_hp"] += amount
                player["hp"] += amount
            elif effect_type == "gain_rupture":
                player["rupture"] += int(effect.get("amount", 0))
            elif effect_type == "reduce_rupture":
                player["rupture"] = max(0, player["rupture"] - int(effect.get("amount", 0)))
            elif effect_type == "gain_card":
                card_id = effect.get("card_id", "strike")
                self.run_state["deck"].append(card_id)
            elif effect_type == "gain_card_random":
                rarity = effect.get("rarity")
                pool = [c.get("id") for c in self.cards_data if c.get("rarity") == rarity and c.get("id")]
                if pool:
                    self.run_state["deck"].append(self.rng.choice(pool))
            elif effect_type == "upgrade_random_card":
                pass
            elif effect_type == "remove_card_from_deck":
                if self.run_state["deck"]:
                    self.run_state["deck"].pop(0)
            elif effect_type == "gain_relic":
                relic_id = effect.get("relic_id")
                if relic_id:
                    self.run_state["relics"].append(relic_id)
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
