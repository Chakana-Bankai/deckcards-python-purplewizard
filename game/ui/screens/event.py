import pygame

from game.systems.reward_system import build_reward_guide
from game.ui.anim import TypewriterBanner
from game.ui.system.modals import ChoiceModal, LoreModal


class EventScreen:
    def __init__(self, app, event):
        self.app = app
        self.event = event
        self.writer = TypewriterBanner()
        self.t = 0.0
        self.guide_type = self._pick_guide_type(event.get("id", "default"))
        lore = getattr(self.app, "lore_data", {}) or {}
        defaults = lore.get("event_fragments", ["Toda ruta trae aprendizaje.", "Escucha al guia."])
        self.parabola = defaults[:3] if defaults else ["La Trama te observa."]
        self.moraleja = defaults[0] if defaults else "Moraleja: cada decision pesa."
        self.msg = ""
        self.guide_names = {"angel": "Oraculo Solar", "shaman": "Amauta de Ceniza", "demon": "Custodio del Vacio", "arcane_hacker": "Arquitecto del Umbral"}
        self._resolved_guide_reward = None

        self.stage = "lore"
        self.lore_modal = LoreModal()
        self.choice_modal = ChoiceModal()
        self._setup_modals()

    def _setup_modals(self):
        self.lore_modal.confirm_label = "Continuar"
        self.lore_modal.cancel_label = "Volver"
        self.lore_modal.on_confirm = self._go_to_choices
        self.lore_modal.on_cancel = self._cancel_event

        self.choice_modal.confirm_label = "Elegir"
        self.choice_modal.cancel_label = "Volver"
        self.choice_modal.on_confirm = self._confirm_choice
        self.choice_modal.on_cancel = self._cancel_event

    def on_enter(self):
        self.writer.set("\n".join(self.parabola[:3]), 1.8)
        self.stage = "lore"

    def _pick_guide_type(self, event_id: str) -> str:
        eid = (event_id or "").lower()
        if any(k in eid for k in ["oracle", "angel", "luz"]):
            return "angel"
        if any(k in eid for k in ["tribu", "apacheta", "ritual", "shaman"]):
            return "shaman"
        if any(k in eid for k in ["demon", "sangre", "abyss", "void"]):
            return "demon"
        return "arcane_hacker"

    def _go_to_choices(self):
        self.stage = "choice"

    def _cancel_event(self):
        self.app.goto_map()

    def _confirm_choice(self):
        idx = self.choice_modal.selected_index
        if idx is None:
            return
        ch = self.event.get("choices", [])[:3][idx]
        effects = ch.get("effects", [])
        if str(self.event.get("id", "")) in {"chakana_crossroads", "condor_vision"}:
            if self._resolved_guide_reward is None:
                self._resolved_guide_reward = build_reward_guide(str(self.event.get("id", "guide")), self.app.rng, self.app.cards_data, self.app.run_state or {})
            self.app.goto_reward(mode="guide_choice", guide_reward=self._resolved_guide_reward)
            return
        self.app.apply_event_effects(effects)
        self.msg = self.app.loc.t(ch.get("text_key", "event_continue"))
        self.app._complete_current_node()
        self.app.goto_map()

    def _sync_lore_modal(self):
        title = self.app.loc.t(self.event.get("title_key", "event_title"))
        guide_name = self.guide_names.get(self.guide_type, "Guia")
        lines = [guide_name, "", *self.writer.current.split("\n")[:6], "", self.moraleja]
        self.lore_modal.open = self.stage == "lore"
        self.lore_modal.title = title
        self.lore_modal.message = "Encuentro"
        self.lore_modal.lines = lines
        self.lore_modal.portrait_group = "guides"
        self.lore_modal.portrait_id = self.guide_type

    def _sync_choice_modal(self):
        self.choice_modal.open = self.stage == "choice"
        self.choice_modal.title = "Tres caminos"
        self.choice_modal.message = "Selecciona una opcion para continuar."
        self.choice_modal.choices = [
            {
                "title": self.app.loc.t(ch.get("text_key", "event_continue")),
                "subtitle": "",
            }
            for ch in self.event.get("choices", [])[:3]
        ]

    def handle_event(self, event):
        mapped_pos = self.app.renderer.map_mouse(getattr(event, "pos", pygame.mouse.get_pos()))
        surface = pygame.display.get_surface()
        if surface is None:
            return

        self._sync_lore_modal()
        self._sync_choice_modal()

        if self.stage == "lore":
            self.lore_modal.handle_event(event, mapped_pos, surface)
            return
        self.choice_modal.handle_event(event, mapped_pos, surface)

    def update(self, dt):
        self.t += dt

    def render(self, s):
        self.app.bg_gen.render_parallax(s, "Pampa Astral", 2048, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))

        self._sync_lore_modal()
        self._sync_choice_modal()

        if self.stage == "lore":
            self.lore_modal.render(s, self.app)
        else:
            self.choice_modal.render(s, self.app.big_font, self.app.small_font)

        if self.msg:
            s.blit(self.app.small_font.render(self.msg, True, (180, 240, 200)), (100, 1000))
