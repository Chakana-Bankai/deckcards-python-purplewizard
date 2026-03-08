from __future__ import annotations

import pygame

from game.ui.theme import UI_THEME


class TutorialScreen:
    def __init__(self, app, next_fn):
        self.app = app
        self.next_fn = next_fn
        self.index = 0
        self.slides = [
            {
                "title": "Energia y cartas",
                "body": "Cada turno recibes energia para jugar cartas. Prioriza costo-impacto: no todas las cartas deben jugarse siempre.",
            },
            {
                "title": "Bloqueo e intencion enemiga",
                "body": "El chip de intencion muestra cuanto golpeara el enemigo. Tu Bloqueo reduce ese dano directamente.",
            },
            {
                "title": "Armonia y sello",
                "body": "La Armonia crece con jugadas de control/ritual. Cuando alcanzas el umbral, habilitas el estado de sello.",
            },
            {
                "title": "Flujo de recompensas",
                "body": "Tras combate eliges recompensa: carta, pack, reliquia u opcion de guia. Elige por sinergia de build, no por brillo aislado.",
            },
            {
                "title": "Estructura de run",
                "body": "La run es finita y progresa por biomas hasta el arconte final. La vida persiste entre combates y puedes continuar desde autosave.",
            },
        ]

    def on_enter(self):
        self.index = 0

    def _next(self):
        self.index += 1
        if self.index >= len(self.slides):
            self.next_fn()

    def _prev(self):
        self.index = max(0, self.index - 1)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_RIGHT):
                self._next()
            elif event.key in (pygame.K_LEFT, pygame.K_BACKSPACE):
                self._prev()
            elif event.key == pygame.K_ESCAPE:
                self.next_fn()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._next()

    def update(self, dt):
        return

    def render(self, s):
        self.app.bg_gen.render_parallax(
            s,
            "Ruinas Chakana",
            777,
            pygame.time.get_ticks() * 0.018,
            particles_on=self.app.user_settings.get("fx_particles", True),
        )

        panel = pygame.Rect(220, 170, 1480, 740)
        pygame.draw.rect(s, UI_THEME["deep_purple"], panel, border_radius=18)
        pygame.draw.rect(s, UI_THEME["accent_violet"], panel, 2, border_radius=18)

        slide = self.slides[self.index]
        step = self.app.small_font.render(f"Tutorial {self.index + 1}/{len(self.slides)}", True, UI_THEME["gold"])
        title = self.app.big_font.render(slide["title"], True, UI_THEME["text"])
        s.blit(step, (panel.x + 28, panel.y + 24))
        s.blit(title, (panel.x + 28, panel.y + 64))

        max_w = panel.w - 56
        words = slide["body"].split()
        lines = []
        cur = ""
        for word in words:
            test = (cur + " " + word).strip()
            if self.app.font.size(test)[0] <= max_w:
                cur = test
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)

        y = panel.y + 164
        for line in lines:
            s.blit(self.app.font.render(line, True, UI_THEME["muted"]), (panel.x + 28, y))
            y += 34

        hint = "Click / Enter: siguiente • ←: anterior • Esc: omitir"
        hint_txt = self.app.tiny_font.render(hint, True, UI_THEME["muted"])
        s.blit(hint_txt, (panel.centerx - hint_txt.get_width() // 2, panel.bottom - 42))
