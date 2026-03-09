from __future__ import annotations

import pygame

from game.ui.theme import UI_THEME


class SceneFusionScreen:
    """Lightweight scene presentation layer for lore/reveal transitions."""

    def __init__(
        self,
        app,
        title: str,
        dialogue: str,
        lore_line: str,
        next_fn,
        *,
        background: str = "Ruinas Chakana",
        biome_layer: str | None = None,
        portrait_key: str = "chakana_mage_portrait",
        portrait_group: str = "avatar",
        speaker_label: str = "CHAKANA",
        set_label: str = "",
        min_seconds: float = 0.8,
        auto_seconds: float = 4.2,
    ):
        self.app = app
        self.title = str(title or "Transicion")
        self.dialogue = str(dialogue or "")
        self.lore_line = str(lore_line or "")
        self.next_fn = next_fn
        self.background = str(background or "Ruinas Chakana")
        self.biome_layer = str(biome_layer) if biome_layer else None
        self.portrait_key = str(portrait_key or "chakana_mage_portrait")
        self.portrait_group = str(portrait_group or "avatar")
        self.speaker_label = str(speaker_label or "CHAKANA")
        self.set_label = str(set_label or "")
        self.min_seconds = float(min_seconds)
        self.auto_seconds = float(auto_seconds)
        self.t = 0.0
        self._ready = False

    def on_enter(self):
        self.t = 0.0
        self._ready = False

    def _finish(self):
        if self._ready:
            self.next_fn()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self._ready = self.t >= self.min_seconds
            self._finish()

    def update(self, dt):
        self.t += max(0.0, float(dt or 0.0))
        self._ready = self.t >= self.min_seconds
        if self.t >= self.auto_seconds:
            self.next_fn()

    def _alpha(self) -> int:
        fade_in = 0.45
        fade_out = 0.55
        if self.t < fade_in:
            a = self.t / max(0.01, fade_in)
        elif self.t > self.auto_seconds - fade_out:
            a = (self.auto_seconds - self.t) / max(0.01, fade_out)
        else:
            a = 1.0
        return max(0, min(255, int(255 * a)))

    def _fit(self, font, text: str, max_w: int) -> str:
        out = str(text or "").replace("\n", " ").strip()
        while out and font.size(out)[0] > max_w and len(out) > 4:
            out = out[:-4] + "..."
        return out

    def render(self, s):
        self.app.bg_gen.render_parallax(
            s,
            self.background,
            811,
            pygame.time.get_ticks() * 0.018,
            particles_on=bool(self.app.user_settings.get("fx_particles", True)),
        )
        if self.biome_layer:
            layer = self.app.assets.sprite("biomes", self.biome_layer, s.get_size(), fallback=(28, 24, 40))
            layer.set_alpha(48)
            s.blit(layer, (0, 0))

        alpha = self._alpha()
        veil = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        veil.fill((10, 8, 18, int(168 * (alpha / 255.0))))
        s.blit(veil, (0, 0))

        panel = pygame.Rect(240, 170, 1440, 520)
        box = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(box, (22, 18, 36, int(208 * (alpha / 255.0))), box.get_rect(), border_radius=18)
        pygame.draw.rect(box, (*UI_THEME["accent_violet"], int(210 * (alpha / 255.0))), box.get_rect(), 2, border_radius=18)
        s.blit(box, panel.topleft)

        avatar_slot = pygame.Rect(panel.x + 24, panel.y + 66, 240, 360)
        pygame.draw.rect(s, UI_THEME["panel_2"], avatar_slot, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], avatar_slot, 1, border_radius=12)
        avatar = self.app.assets.sprite(self.portrait_group, self.portrait_key, (avatar_slot.w - 16, avatar_slot.h - 16), fallback=(86, 56, 132)).copy()
        avatar.set_alpha(int(236 * (alpha / 255.0)))
        s.blit(avatar, avatar.get_rect(center=avatar_slot.center).topleft)

        for yy in range(avatar_slot.y + 8, avatar_slot.bottom - 8, 5):
            pygame.draw.line(s, (120, 216, 246, int(28 * (alpha / 255.0))), (avatar_slot.x + 6, yy), (avatar_slot.right - 6, yy), 1)

        text_panel = pygame.Rect(avatar_slot.right + 18, panel.y + 56, panel.w - avatar_slot.w - 52, panel.h - 100)
        pygame.draw.rect(s, UI_THEME["panel_2"], text_panel, border_radius=12)
        pygame.draw.rect(s, UI_THEME["gold"], text_panel, 1, border_radius=12)

        title = self._fit(self.app.big_font, self.title, text_panel.w - 24)
        title_s = self.app.big_font.render(title, True, UI_THEME["gold"])
        title_s.set_alpha(alpha)
        s.blit(title_s, (text_panel.x + 12, text_panel.y + 12))

        speaker = self.app.small_font.render(self.speaker_label[:22], True, UI_THEME["text"])
        speaker.set_alpha(alpha)
        s.blit(speaker, (text_panel.right - speaker.get_width() - 12, text_panel.y + 18))

        dialogue = self._fit(self.app.font, self.dialogue, text_panel.w - 24)
        dia = self.app.font.render(dialogue, True, UI_THEME["text"])
        dia.set_alpha(alpha)
        s.blit(dia, (text_panel.x + 12, text_panel.y + 104))

        lore = self._fit(self.app.small_font, self.lore_line, text_panel.w - 24)
        lore_s = self.app.small_font.render(lore, True, UI_THEME["muted"])
        lore_s.set_alpha(alpha)
        s.blit(lore_s, (text_panel.x + 12, text_panel.y + 154))

        if self.set_label:
            chip = pygame.Rect(text_panel.x + 12, text_panel.bottom - 46, 320, 30)
            pygame.draw.rect(s, UI_THEME["panel"], chip, border_radius=8)
            pygame.draw.rect(s, UI_THEME["gold"], chip, 1, border_radius=8)
            chip_txt = self.app.tiny_font.render(self._fit(self.app.tiny_font, self.set_label, chip.w - 14), True, UI_THEME["gold"])
            chip_txt.set_alpha(alpha)
            s.blit(chip_txt, (chip.x + 7, chip.y + 8))

        hint = "Pulsa para continuar" if self._ready else "..."
        hint_s = self.app.small_font.render(hint, True, UI_THEME["good"] if self._ready else UI_THEME["muted"])
        hint_s.set_alpha(alpha)
        s.blit(hint_s, (panel.centerx - hint_s.get_width() // 2, panel.bottom - 38))


