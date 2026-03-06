import math
import random

import pygame

from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME


class EndScreen:
    def __init__(self, app, victory=True):
        self.app = app
        self.victory = victory
        self.banner = TypewriterBanner()
        self.lines = app.lore_data.get("ending_lines", ["La Trama respira en paz.", "Un ciclo termina, otro nace."])
        self.idx = 0
        self.t = 0
        self.rng = random.Random(1337)
        self._particles = []
        self.buttons = {
            "primary": pygame.Rect(760, 760, 400, 68),
            "menu": pygame.Rect(760, 842, 400, 68),
        }

    def on_enter(self):
        if self.victory:
            msg = self.lines[0]
        else:
            msg = "La trama se rompe..."
        self.banner.set(msg, 2.0)
        self._reset_particles()

    def _reset_particles(self):
        self._particles = []
        for i in range(56):
            self._particles.append(
                {
                    "x": float(self.rng.randint(0, 1919)),
                    "y": float(self.rng.randint(0, 1079)),
                    "r": float(self.rng.randint(1, 3)),
                    "vy": float(self.rng.uniform(14.0, 42.0)),
                    "phase": float(self.rng.uniform(0.0, math.pi * 2.0)),
                }
            )

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.buttons["primary"].collidepoint(pos):
                if self.victory:
                    if self.app.run_state:
                        self.app.goto_map()
                else:
                    if self.app.run_state:
                        self.app.goto_map()
                    else:
                        self.app.new_run()
            elif self.buttons["menu"].collidepoint(pos):
                if self.victory:
                    self.app.goto_menu()
                else:
                    self.app.new_run()

    def update(self, dt):
        self.t += dt
        if self.victory and self.t > 3.3:
            self.t = 0
            self.idx = (self.idx + 1) % len(self.lines)
            self.banner.set(self.lines[self.idx], 2.8)

        if not self.victory:
            for p in self._particles:
                p["y"] += p["vy"] * dt
                p["x"] += math.sin(self.t * 0.6 + p["phase"]) * 6.0 * dt
                if p["y"] > 1110:
                    p["y"] = -12.0
                    p["x"] = float(self.rng.randint(0, 1919))

    def _draw_defeat_bg(self, s):
        self.app.bg_gen.render_parallax(s, "umbral", 777, pygame.time.get_ticks() * 0.02, particles_on=True)
        veil = pygame.Surface((s.get_width(), s.get_height()), pygame.SRCALPHA)
        veil.fill((10, 6, 18, 170))
        s.blit(veil, (0, 0))
        for p in self._particles:
            alpha = 70 + int(40 * (0.5 + 0.5 * math.sin(self.t * 1.1 + p["phase"])))
            pygame.draw.circle(s, (166, 132, 214, alpha), (int(p["x"]), int(p["y"])), int(p["r"]))

    def render(self, s):
        if self.victory:
            sky, silhouettes, fog = self.app.bg_gen.get_layers("Templo Obsidiana", 777)
            s.blit(sky, (0, 0))
            s.blit(silhouettes, (0, 0))
            s.blit(fog, (0, 0))
        else:
            self._draw_defeat_bg(s)

        panel = pygame.Rect(360, 170, 1200, 560)
        pygame.draw.rect(s, UI_THEME["panel"], panel, border_radius=18)
        pygame.draw.rect(s, UI_THEME["gold"] if self.victory else UI_THEME["accent_violet"], panel, 2, border_radius=18)

        title = "Victoria" if self.victory else "Derrota"
        s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (860, 230))

        body = self.banner.current if self.victory else "La trama se rompe..."
        s.blit(self.app.font.render(body, True, UI_THEME["text"]), (430, 318))

        labels = {
            "primary": "Continuar" if self.victory else "Volver al mapa",
            "menu": "Volver al Menú" if self.victory else "Nueva run",
        }
        for k, r in self.buttons.items():
            base = UI_THEME["violet"] if self.victory else (96, 58, 144) if k == "primary" else (72, 48, 112)
            pygame.draw.rect(s, base, r, border_radius=12)
            pygame.draw.rect(s, UI_THEME["gold"] if self.victory else UI_THEME["accent_violet"], r, 2, border_radius=12)
            txt = self.app.small_font.render(labels[k], True, UI_THEME["text"])
            s.blit(txt, txt.get_rect(center=r.center))
