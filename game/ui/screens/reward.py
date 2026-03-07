import pygame

from game.ui.system.modals import CardGridModal, ChoiceModal


class RewardScreen:
    def __init__(self, app, reward_data, gold, xp_gained=0):
        self.app = app
        self.reward_data = reward_data if isinstance(reward_data, dict) else {"type": "choose1of3", "cards": list(reward_data or [])}
        self.mode = str(self.reward_data.get("type", "choose1of3"))
        self.cards = list(self.reward_data.get("cards", []))
        self.picks = self.cards
        self.relic = self.reward_data.get("relic")
        self.options = list(self.reward_data.get("options", []))
        self.gold = int(gold or 0)
        self.xp_gained = int(xp_gained or 0)
        self.msg = ""
        self.selected_idx = None
        self.hover_card = None

        self.card_modal = CardGridModal()
        self.choice_modal = ChoiceModal()
        self._setup_modals()

    def _setup_modals(self):
        self.card_modal.confirm_label = "Confirmar"
        self.card_modal.cancel_label = "Volver"
        self.card_modal.on_confirm = self._modal_confirm_card
        self.card_modal.on_cancel = self._modal_cancel

        self.choice_modal.confirm_label = "Continuar"
        self.choice_modal.cancel_label = "Volver"
        self.choice_modal.on_confirm = self._modal_confirm_choice
        self.choice_modal.on_cancel = self._modal_cancel

    def on_enter(self):
        pass

    def _mode_title_subtitle(self):
        title = {
            "choose1of3": "Recompensa",
            "boss_pack": "Botin del Jefe",
            "guide_choice": "Eleccion del Guia",
        }.get(self.mode, "Recompensa")
        subtitle = {
            "choose1of3": f"Selecciona 1 carta. +{self.gold} oro, +{self.xp_gained} XP.",
            "boss_pack": f"Has vencido al jefe. Tomas todo el lote (+{self.gold} oro, +{self.xp_gained} XP).",
            "guide_choice": "Sabiduria, Poder o Sacrificio: elige tu destino.",
        }.get(self.mode, "")
        return title, subtitle

    def _sync_card_modal(self):
        title, subtitle = self._mode_title_subtitle()
        self.card_modal.open = True
        self.card_modal.title = title
        self.card_modal.message = subtitle
        self.card_modal.cards = list(self.cards)
        self.card_modal.selected_index = self.selected_idx
        self.card_modal.allow_empty_confirm = self.mode == "boss_pack"
        self.card_modal.confirm_label = "Tomar recompensas" if self.mode == "boss_pack" else "Confirmar"

    def _sync_choice_modal(self):
        title, subtitle = self._mode_title_subtitle()
        self.choice_modal.open = True
        self.choice_modal.title = title
        self.choice_modal.message = subtitle
        self.choice_modal.choices = [
            {
                "title": opt.get("title", f"Opcion {i+1}"),
                "subtitle": opt.get("effect_label", ""),
            }
            for i, opt in enumerate(self.options[:3])
        ]
        self.choice_modal.selected_index = self.selected_idx

    def _apply_guide_option(self, idx: int):
        option = self.options[idx]
        effects = list(option.get("effects", []))
        player = self.app.run_state.get("player", {})
        for effect in effects:
            typ = effect.get("type")
            if typ == "gain_harmony_perm":
                cur = int(player.get("harmony_max", 10))
                player["harmony_max"] = cur + int(effect.get("amount", 1))
            elif typ == "gain_cards":
                for cid in effect.get("cards", []):
                    self.app.run_state["sideboard"].append(cid)
            elif typ == "heal_percent":
                amount = float(effect.get("amount", 0.25))
                heal = int(player.get("max_hp", 60) * amount)
                player["hp"] = min(player.get("max_hp", 60), player.get("hp", 1) + max(1, heal))
            elif typ == "lose_random_deck_card":
                deck = self.app.run_state.get("deck", [])
                if deck:
                    deck.pop(self.app.rng.randint(0, len(deck) - 1))
        self.app.goto_map()

    def confirm(self):
        if self.mode == "choose1of3":
            if self.selected_idx is None:
                self.app.sfx.play("ui_click")
                return
            card = self.cards[self.selected_idx]
            self.app.run_state["sideboard"].append(card.definition.id)
            self.app.run_state["gold"] += self.gold
            self.app.goto_map()
            return

        if self.mode == "boss_pack":
            for c in self.cards:
                self.app.run_state["sideboard"].append(c.definition.id)
            if isinstance(self.relic, dict) and self.relic.get("id"):
                self.app.run_state.setdefault("relics", []).append(self.relic["id"])
            self.app.run_state["gold"] += self.gold
            self.app.goto_end(victory=True)
            return

        if self.mode == "guide_choice":
            if self.selected_idx is None:
                self.app.sfx.play("ui_click")
                return
            self._apply_guide_option(self.selected_idx)

    def claim(self, index: int) -> bool:
        if self.mode != "choose1of3":
            return False
        if not (0 <= index < len(self.cards)):
            return False
        self.selected_idx = index
        self.confirm()
        return True

    def _modal_confirm_card(self):
        self.selected_idx = self.card_modal.selected_index
        self.confirm()

    def _modal_confirm_choice(self):
        self.selected_idx = self.choice_modal.selected_index
        self.confirm()

    def _modal_cancel(self):
        self.app.goto_map()

    def handle_event(self, event):
        mapped_pos = self.app.renderer.map_mouse(getattr(event, "pos", pygame.mouse.get_pos()))
        surface = pygame.display.get_surface()
        if surface is None:
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.goto_map()
            return

        if self.mode in {"choose1of3", "boss_pack"}:
            self._sync_card_modal()
            self.card_modal.handle_event(event, mapped_pos, surface)
            self.selected_idx = self.card_modal.selected_index
            self.hover_card = self.card_modal.hover_index
            return

        if self.mode == "guide_choice":
            self._sync_choice_modal()
            self.choice_modal.handle_event(event, mapped_pos, surface)
            self.selected_idx = self.choice_modal.selected_index

    def update(self, dt):
        _ = dt

    def render(self, s):
        if self.mode in {"choose1of3", "boss_pack"}:
            self._sync_card_modal()
            self.card_modal.render(s, self.app)
            return

        if self.mode == "guide_choice":
            self._sync_choice_modal()
            self.choice_modal.render(s, self.app.big_font, self.app.small_font)
            return
