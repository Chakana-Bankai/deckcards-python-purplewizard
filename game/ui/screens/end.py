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
        self.idx = 0
        self.t = 0.0
        self.rng = random.Random(1337)
        self._particles = []
        self.victory_phase = "lore"

        self.victory_lore = [
            "El Monolito Fracturado cae ante Chakana.",
            "La grieta astral cede y el pulso del mundo regresa.",
            "La Trama recuerda tu nombre en silencio.",
        ]
        self.defeat_lore = [
            "La Trama se fractura bajo tus pies.",
            "Las sombras reclaman el sendero por un instante.",
            "Aun queda una ruta: vuelve a levantarte.",
        ]

        self.credits_lines = [
            "CHAKANA : PURPLE WIZARD",
            "",
            "CHAKANA STUDIO",
            "",
            "Creado por:",
            "Mauricio Olivares Chacana",
            "",
            "Inspirado en la Cosmovisión Andina",
            "",
            "Dedicado a Tomás",
        ]

        self.buttons = {
            "primary": pygame.Rect(760, 760, 400, 68),
            "secondary": pygame.Rect(760, 842, 400, 68),
            "menu": pygame.Rect(760, 924, 400, 68),
        }
        self.can_continue_defeat = False

    def on_enter(self):
        self.t = 0.0
        self.idx = 0
        self.can_continue_defeat = bool((not self.victory) and getattr(self.app, "run_state", None))
        if self.victory:
            self.victory_phase = "lore"
            self.banner.set(self.victory_lore[0], 2.0)
        else:
            self.banner.set(self.defeat_lore[0], 2.0)
        self._reset_particles()

    def _reset_particles(self):
        self._particles = []
        for _ in range(56):
            self._particles.append(
                {
                    "x": float(self.rng.randint(0, 1919)),
                    "y": float(self.rng.randint(0, 1079)),
                    "r": float(self.rng.randint(1, 3)),
                    "vy": float(self.rng.uniform(14.0, 42.0)),
                    "phase": float(self.rng.uniform(0.0, math.pi * 2.0)),
                }
            )

    def _advance_victory_phase(self):
        if self.victory_phase == "lore":
            self.victory_phase = "credits"
            self.banner.set("", 0.1)
        else:
            self.app.goto_menu()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.buttons["primary"].collidepoint(pos):
                if self.victory:
                    self._advance_victory_phase()
                else:
                    if self.app.run_state:
                        self.app.goto_map()
                    else:
                        self.app.new_run()
            elif self.buttons["secondary"].collidepoint(pos):
                if self.victory:
                    self.app.goto_menu()
                else:
                    self.app.new_run()
            elif self.buttons["menu"].collidepoint(pos):
                self.app.goto_menu()

    def update(self, dt):
        self.t += dt
        if self.t > 3.2:
            self.t = 0.0
            self.idx += 1
            if self.victory and self.victory_phase == "lore" and self.idx < len(self.victory_lore):
                self.banner.set(self.victory_lore[self.idx], 2.8)
            if (not self.victory) and self.idx < len(self.defeat_lore):
                self.banner.set(self.defeat_lore[self.idx], 2.8)

        if not self.victory:
            for p in self._particles:
                p["y"] += p["vy"] * dt
                p["x"] += math.sin(self.t * 0.6 + p["phase"]) * 6.0 * dt
                if p["y"] > 1110:
                    p["y"] = -12.0
                    p["x"] = float(self.rng.randint(0, 1919))

    def _draw_defeat_bg(self, s):
        self.app.bg_gen.render_parallax(s, "Caverna Umbral", 777, pygame.time.get_ticks() * 0.02, particles_on=True)
        veil = pygame.Surface((s.get_width(), s.get_height()), pygame.SRCALPHA)
        veil.fill((10, 6, 18, 170))
        s.blit(veil, (0, 0))
        for p in self._particles:
            alpha = 70 + int(40 * (0.5 + 0.5 * math.sin(self.t * 1.1 + p["phase"])))
            pygame.draw.circle(s, (166, 132, 214, alpha), (int(p["x"]), int(p["y"])), int(p["r"]))

    def render(self, s):
        if self.victory:
            self.app.bg_gen.render_parallax(s, "Templo Obsidiana", 777, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))
        else:
            self._draw_defeat_bg(s)

        panel = pygame.Rect(360, 170, 1200, 560)
        pygame.draw.rect(s, UI_THEME["panel"], panel, border_radius=18)
        pygame.draw.rect(s, UI_THEME["gold"] if self.victory else UI_THEME["accent_violet"], panel, 2, border_radius=18)

        if self.victory:
            if self.victory_phase == "lore":
                title = "Victoria"
                body = self.banner.current or self.victory_lore[min(self.idx, len(self.victory_lore) - 1)]
                s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (840, 230))
                s.blit(self.app.font.render(body, True, UI_THEME["text"]), (430, 318))
                labels = {"primary": "Ver creditos", "secondary": "Volver al menu", "menu": "Volver al menu"}
            else:
                title = "Creditos"
                s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (840, 230))
                for i, line in enumerate(self.credits_lines):
                    col = UI_THEME["gold"] if line in {"CHAKANA : PURPLE WIZARD", "CHAKANA STUDIO", "Creado por:", "Inspirado en la Cosmovisión Andina", "Dedicado a Tomás"} else UI_THEME["text"]
                    s.blit(self.app.font.render(line, True, col), (620, 308 + i * 42))
                labels = {"primary": "Finalizar", "secondary": "Volver al menu", "menu": "Volver al menu"}
        else:
            title = "Derrota"
            body = self.banner.current or self.defeat_lore[min(self.idx, len(self.defeat_lore) - 1)]
            s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (860, 230))
            s.blit(self.app.font.render(body, True, UI_THEME["text"]), (430, 318))
            labels = {"primary": "Reintentar" if self.can_continue_defeat else "Nueva run", "secondary": "Nueva run", "menu": "Volver al menu"}

        draw_keys = ["primary", "secondary"] if self.victory else ["primary", "secondary", "menu"]
        for k in draw_keys:
            r = self.buttons[k]
            base = UI_THEME["violet"] if self.victory else (102, 62, 150) if k == "primary" else (84, 52, 122) if k == "secondary" else (66, 42, 102)
            pygame.draw.rect(s, base, r, border_radius=12)
            pygame.draw.rect(s, UI_THEME["gold"] if self.victory else UI_THEME["accent_violet"], r, 2, border_radius=12)
            txt = self.app.small_font.render(labels[k], True, UI_THEME["text"])
            s.blit(txt, txt.get_rect(center=r.center))

