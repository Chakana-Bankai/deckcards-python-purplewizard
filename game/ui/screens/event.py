import pygame

from game.ui.anim import TypewriterBanner
from game.ui.system.modals import LoreModal


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
        self.event_type = str(event.get("event_type") or "lore")
        self.event_tags = [str(t) for t in list(event.get("tags", []) or []) if t]
        self.stage = "lore"
        self.lore_modal = LoreModal()
        self.selected_index = None
        self.hover_index = None
        self.choice_rects = []
        self._setup_modals()

    def _setup_modals(self):
        self.lore_modal.confirm_label = "Continuar"
        self.lore_modal.cancel_label = "Volver"
        self.lore_modal.on_confirm = self._go_to_choices
        self.lore_modal.on_cancel = self._cancel_event

    def _choice_outcome(self, choice: dict) -> str:
        effects = [e for e in list(choice.get("effects", [])) if isinstance(e, dict)]
        if not effects:
            return "Continua la Trama sin costo."
        bits = []
        for ef in effects[:3]:
            et = str(ef.get("type", "")).lower()
            amt = int(ef.get("amount", 0) or 0)
            if et == "gain_gold":
                bits.append(f"+{amt} oro")
            elif et == "lose_gold":
                bits.append(f"-{amt} oro")
            elif et == "gain_harmony_perm":
                bits.append(f"+{amt} armonia maxima")
            elif et == "heal_percent" or et == "heal":
                bits.append("curacion")
            elif et == "gain_cards" or et == "gain_card" or et == "gain_card_random":
                bits.append("cartas")
            elif et == "gain_relic" or et == "gain_relic_random":
                bits.append("reliquia")
            elif et == "lose_random_deck_card" or et == "remove_card_from_deck":
                bits.append("purga")
            elif et == "gain_rupture":
                bits.append(f"+{amt} ruptura")
            elif et == "reduce_rupture":
                bits.append(f"-{amt} ruptura")
            elif et == "upgrade_random_card":
                bits.append("mejora ritual")
            else:
                bits.append(et.replace("_", " "))
        return " | ".join(bits) if bits else "Resultado variable."

    def _choice_lore(self, idx: int) -> str:
        lore = [
            "El Umbral recompensa a quien arriesga.",
            "Todo pacto guarda una renuncia.",
            "La geometria del destino se vuelve visible.",
        ]
        return lore[idx % len(lore)]

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

    def _confirm_choice_index(self, idx: int):
        choices = list(self.event.get("choices", [])[:3])
        if not (0 <= idx < len(choices)):
            return
        ch = choices[idx]
        effects = ch.get("effects", [])
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
        self.lore_modal.message = "Encuentro ritual"
        self.lore_modal.lines = lines
        self.lore_modal.portrait_group = "guides"
        self.lore_modal.portrait_id = self.guide_type

    def _layout_choices(self, surface):
        panel = pygame.Rect(260, 220, 1400, 620)
        count = max(1, min(3, len(self.event.get("choices", [])[:3])))
        gap = 18
        item_h = max(132, min(176, (panel.h - (count - 1) * gap) // count))
        rects = []
        for i in range(count):
            rects.append(pygame.Rect(panel.x + 24, panel.y + 80 + i * (item_h + gap), panel.w - 48, item_h))
        self.choice_rects = rects
        return panel, rects

    def handle_event(self, event):
        mapped_pos = self.app.renderer.map_mouse(getattr(event, "pos", pygame.mouse.get_pos()))
        surface = pygame.display.get_surface()
        if surface is None:
            return

        self._sync_lore_modal()

        if self.stage == "lore":
            self.lore_modal.handle_event(event, mapped_pos, surface)
            return

        _panel, rects = self._layout_choices(surface)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.goto_map()
            return
        if event.type == pygame.MOUSEMOTION:
            self.hover_index = None
            for i, rr in enumerate(rects):
                if rr.collidepoint(mapped_pos):
                    self.hover_index = i
                    break
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rr in enumerate(rects):
                if rr.collidepoint(mapped_pos):
                    self.selected_index = i
                    self.app.sfx.play("ui_click")
                    self._confirm_choice_index(i)
                    return

    def update(self, dt):
        self.t += dt

    def render(self, s):
        self.app.bg_gen.render_parallax(s, "Pampa Astral", 2048, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))

        badge = pygame.Rect(26, 20, 760, 116)
        pygame.draw.rect(s, (24, 20, 36), badge, border_radius=12)
        pygame.draw.rect(s, (164, 132, 232), badge, 2, border_radius=12)
        title = self.app.loc.t(self.event.get("title_key", "event_title"))
        subtitle = self.app.loc.t(self.event.get("body_key", "lore_tagline"))
        tags_txt = ", ".join(self.event_tags[:3]) if self.event_tags else self.event_type
        guide = self.guide_names.get(self.guide_type, "Guia del Umbral")
        s.blit(self.app.small_font.render(title, True, (238, 226, 186)), (badge.x + 14, badge.y + 10))
        s.blit(self.app.tiny_font.render(f"Guia: {guide}", True, (190, 176, 224)), (badge.x + 14, badge.y + 40))
        s.blit(self.app.tiny_font.render(subtitle[:74], True, (214, 208, 236)), (badge.x + 14, badge.y + 66))
        s.blit(self.app.tiny_font.render(f"Tipo: {self.event_type.upper()} | {tags_txt}", True, (186, 216, 236)), (badge.x + 14, badge.y + 88))
        art = self.app.assets.sprite("guides", self.guide_type, (88, 88), fallback=(74, 58, 106))
        s.blit(art, art.get_rect(center=(badge.right - 56, badge.centery)).topleft)

        self._sync_lore_modal()

        if self.stage == "lore":
            self.lore_modal.render(s, self.app)
        else:
            panel, rects = self._layout_choices(s)
            pygame.draw.rect(s, (18, 16, 30), panel, border_radius=18)
            pygame.draw.rect(s, (164, 132, 232), panel, 2, border_radius=18)
            s.blit(self.app.big_font.render("Tres visiones", True, (238, 226, 186)), (panel.x + 24, panel.y + 18))
            s.blit(self.app.small_font.render("Elige una senda. El efecto se aplicara de inmediato.", True, (214, 208, 236)), (panel.x + 24, panel.y + 48))
            choices = list(self.event.get("choices", [])[:3])
            for i, rr in enumerate(rects):
                ch = choices[i] if i < len(choices) else {}
                hovered = i == self.hover_index
                selected = i == self.selected_index
                fill = (40, 34, 60) if hovered else (28, 24, 44)
                border = (236, 212, 148) if selected or hovered else (118, 102, 156)
                pygame.draw.rect(s, fill, rr, border_radius=14)
                pygame.draw.rect(s, border, rr, 2, border_radius=14)
                text = self.app.loc.t(ch.get("text_key", "event_continue"))
                outcome = self._choice_outcome(ch)
                lore = self._choice_lore(i)
                s.blit(self.app.small_font.render(text[:48], True, (236, 226, 240)), (rr.x + 16, rr.y + 14))
                s.blit(self.app.tiny_font.render(outcome[:88], True, (214, 208, 236)), (rr.x + 16, rr.y + 48))
                s.blit(self.app.tiny_font.render(lore[:88], True, (186, 216, 236)), (rr.x + 16, rr.y + 76))
                s.blit(self.app.tiny_font.render('Click para aceptar el destino', True, (236, 212, 148)), (rr.x + 16, rr.bottom - 26))

        if self.msg:
            s.blit(self.app.small_font.render(self.msg, True, (180, 240, 200)), (100, 1000))
