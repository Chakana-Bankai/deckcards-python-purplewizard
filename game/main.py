from __future__ import annotations

import json
import sys
import pygame

from game.combat.card import CardDef, CardInstance
from game.combat.combat_state import CombatState
from game.core.localization import LocalizationManager
from game.core.rng import SeededRNG
from game.core.state_machine import StateMachine
from game.settings import DATA_DIR, FPS
from game.ui.render import Renderer, SoundManager
from game.ui.screens.combat import CombatScreen
from game.ui.screens.event import EventScreen
from game.ui.screens.map import MapScreen
from game.ui.screens.menu import MenuScreen
from game.ui.screens.reward import RewardScreen
from game.ui.screens.shop import ShopScreen


class App:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            print("[audio] mixer disabled")
        self.renderer = Renderer()
        pygame.display.set_caption("CHAKANA")
        self.clock = pygame.time.Clock()
        self.running = True
        self.rng = SeededRNG(1337)
        self.loc = LocalizationManager("es")
        self.sfx = SoundManager()
        self.font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 18)
        self.big_font = pygame.font.SysFont("arial", 42, bold=True)
        self.sm = StateMachine()
        self.run_state = None
        self.cards_data = json.loads((DATA_DIR / "cards.json").read_text(encoding="utf-8"))
        self.events_data = json.loads((DATA_DIR / "events.json").read_text(encoding="utf-8"))
        self.relics_data = json.loads((DATA_DIR / "relics.json").read_text(encoding="utf-8"))
        self.sm.set(MenuScreen(self))

    def toggle_language(self):
        self.loc.load("en" if self.loc.current_lang == "es" else "es")

    def goto_menu(self):
        self.sm.set(MenuScreen(self))

    def new_run(self):
        self.run_state = {
            "gold": 80,
            "relics": ["violet_seal"],
            "player": {"hp": 70, "max_hp": 70, "block": 0, "energy": 3, "rupture": 0, "statuses": {}},
            "deck": ["strike"] * 5 + ["defend"] * 5,
            "map": self.generate_map(),
            "map_index": 0,
        }
        self.goto_map()

    def generate_map(self):
        cols = 10
        graph = []
        node_types = ["combat", "combat", "event", "combat", "shop", "combat", "event", "combat", "combat", "boss"]
        for c in range(cols):
            count = 1 if c in (0, cols - 1) else 2
            col = []
            for r in range(count):
                nid = f"{c}_{r}"
                y = 180 + r * 220
                col.append({"id": nid, "x": 120 + c * 115, "y": y, "type": node_types[c], "next": [], "available": c == 0})
            graph.append(col)
        for c in range(cols - 1):
            next_ids = [n["id"] for n in graph[c + 1]]
            for n in graph[c]:
                n["next"] = next_ids
        return graph

    def goto_map(self):
        self.sm.set(MapScreen(self))

    def enter_node(self, node):
        if node["type"] in {"combat", "boss"}:
            eid = ["inverse_weaver"] if node["type"] == "boss" else [self.rng.choice([e["id"] for e in json.loads((DATA_DIR / "enemies.json").read_text(encoding='utf-8')) if e["id"] != "inverse_weaver"])]
            self.current_combat = CombatState(self.rng, self.run_state, eid)
            self.sm.set(CombatScreen(self, self.current_combat))
        elif node["type"] == "shop":
            pool = [c for c in self.cards_data if c["rarity"] in {"common", "uncommon"}]
            self.sm.set(ShopScreen(self, self.rng.choice(pool)))
        else:
            self.sm.set(EventScreen(self, self.rng.choice(self.events_data)))

    def on_combat_victory(self):
        pool = [c for c in self.cards_data if c["rarity"] != "basic"]
        picks = [CardInstance(CardDef(**self.rng.choice(pool))) for _ in range(3)]
        gold = self.rng.randint(10, 25)
        self.sm.set(RewardScreen(self, picks, gold))

    def apply_event_effects(self, effects):
        p = self.run_state["player"]
        for e in effects:
            t = e["type"]
            if t == "lose_gold":
                self.run_state["gold"] = max(0, self.run_state["gold"] - e["amount"])
            elif t == "gain_gold":
                self.run_state["gold"] += e["amount"]
            elif t == "heal":
                p["hp"] = min(p["max_hp"], p["hp"] + e["amount"])
            elif t == "lose_hp":
                p["hp"] = max(1, p["hp"] - e["amount"])
            elif t == "gain_max_hp":
                p["max_hp"] += e["amount"]
                p["hp"] += e["amount"]
            elif t == "gain_rupture":
                p["rupture"] += e["amount"]
            elif t == "reduce_rupture":
                p["rupture"] = max(0, p["rupture"] - e["amount"])
            elif t == "gain_card":
                self.run_state["deck"].append(e["card_id"])
            elif t == "gain_card_random":
                pool = [c["id"] for c in self.cards_data if c["rarity"] == e["rarity"]]
                if pool:
                    self.run_state["deck"].append(self.rng.choice(pool))
            elif t == "upgrade_random_card":
                pass
            elif t == "remove_card_from_deck":
                if self.run_state["deck"]:
                    self.run_state["deck"].pop(0)
            elif t == "gain_relic":
                self.run_state["relics"].append(e["relic_id"])
            elif t == "gain_relic_random":
                pool = [r["id"] for r in self.relics_data if r["rarity"] == e["rarity"]]
                if pool:
                    self.run_state["relics"].append(self.rng.choice(pool))

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
    try:
        App().run()
    except Exception as exc:
        print("Fatal:", exc)
        pygame.quit()
        sys.exit(1)
