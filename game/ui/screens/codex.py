from __future__ import annotations

import json
from pathlib import Path

import pygame

from game.core.paths import data_dir
from game.ui.theme import UI_THEME
from game.ui.system.components import UIButton, UIPanel, UILabel


SECTION_ORDER = [
    "lore",
    "systems",
    "rules",
    "cards",
    "enemies",
    "archons",
    "biomes",
    "relics",
    "builds",
    "tips_help",
]


class CodexScreen:
    def __init__(self, app):
        self.app = app
        self.sections = self._load_sections()
        self.section_by_id = {str(s.get("id", "")): s for s in self.sections}
        self.active_section_id = self.sections[0].get("id", "lore") if self.sections else "lore"

        self.back_btn = pygame.Rect(42, 1008, 220, 52)
        self.tutorial_btn = pygame.Rect(280, 1008, 340, 52)
        self.left_panel = pygame.Rect(34, 120, 420, 860)
        self.right_panel = pygame.Rect(474, 120, 1412, 860)

        self.section_buttons = []
        self._build_section_buttons()

    def _load_sections(self) -> list[dict]:
        path = data_dir() / "codex.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            payload = {}
        raw = payload.get("sections", []) if isinstance(payload, dict) else []
        out = []
        for sid in SECTION_ORDER:
            found = next((x for x in raw if isinstance(x, dict) and str(x.get("id", "")) == sid), None)
            if isinstance(found, dict):
                out.append(found)
        for extra in raw:
            if not isinstance(extra, dict):
                continue
            if str(extra.get("id", "")) not in {str(x.get("id", "")) for x in out}:
                out.append(extra)
        return out

    def _build_section_buttons(self):
        self.section_buttons = []
        y = self.left_panel.y + 16
        for section in self.sections:
            r = pygame.Rect(self.left_panel.x + 14, y, self.left_panel.w - 28, 52)
            self.section_buttons.append((r, str(section.get("id", ""))))
            y += 58

    def _active_section(self) -> dict:
        return self.section_by_id.get(self.active_section_id, self.sections[0] if self.sections else {})

    def _dynamic_hints_for_section(self, sid: str) -> list[str]:
        run = self.app.run_state if isinstance(self.app.run_state, dict) else {}
        if sid == "cards":
            total = len(getattr(self.app, "cards_data", []) or [])
            roles = sorted({str(c.get("role", "")).lower() for c in (getattr(self.app, "cards_data", []) or []) if isinstance(c, dict) and c.get("role")})
            return [f"Cartas cargadas: {total}", f"Roles detectados: {', '.join(roles) if roles else 'sin datos'}"]
        if sid == "enemies":
            total = len(getattr(self.app, "enemies_data", []) or [])
            return [f"Enemigos cargados: {total}"]
        if sid == "archons":
            bosses = [b.get("name_es", b.get("id", "-")) for b in list(getattr(self.app, "content", {}).bosses or []) if isinstance(b, dict)] if hasattr(getattr(self.app, "content", None), "bosses") else []
            if bosses:
                return [f"Arcontes activos: {', '.join(bosses[:4])}"]
            return []
        if sid == "biomes":
            biomes = [str(b.get("name", b.get("id", ""))) for b in (getattr(self.app, "biome_defs", []) or []) if isinstance(b, dict)]
            if biomes:
                return [f"Ruta actual 1.0: {' -> '.join(biomes[:4])}"]
            return []
        if sid == "relics":
            relics = list(getattr(self.app, "relics_data", []) or [])
            tiers = sorted({str(r.get("tier", r.get("rarity", ""))).lower() for r in relics if isinstance(r, dict)})
            return [f"Reliquias: {len(relics)}", f"Tiers: {', '.join(tiers) if tiers else 'sin datos'}"]
        if sid == "rules":
            lvl = int(run.get("level", 1) or 1)
            xp = int(run.get("xp", 0) or 0)
            return [f"Run actual: nivel {lvl}, xp {xp}"]
        return []

    def _wrap(self, text: str, width: int, max_lines: int = 3) -> list[str]:
        font = self.app.font
        words = str(text or "").split()
        if not words:
            return []
        lines = []
        cur = ""
        for word in words:
            test = (cur + " " + word).strip()
            if font.size(test)[0] <= width:
                cur = test
            else:
                lines.append(cur)
                cur = word
                if len(lines) >= max_lines:
                    break
        if cur and len(lines) < max_lines:
            lines.append(cur)
        return lines[:max_lines]

    def on_enter(self):
        self._build_section_buttons()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.goto_menu()
                return
            if event.key == pygame.K_F1:
                self.app.toggle_language()
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.back_btn.collidepoint(pos):
                self.app.sfx.play("ui_click")
                self.app.goto_menu()
                return
            if self.tutorial_btn.collidepoint(pos):
                self.app.sfx.play("ui_click")
                self.app.goto_tutorial()
                return
            for rect, sid in self.section_buttons:
                if rect.collidepoint(pos):
                    self.app.sfx.play("ui_click")
                    self.active_section_id = sid
                    return

    def update(self, dt):
        _ = dt

    def render(self, s):
        self.app.bg_gen.render_parallax(
            s,
            "Ruinas Chakana",
            1201,
            pygame.time.get_ticks() * 0.016,
            particles_on=self.app.user_settings.get("fx_particles", True),
        )

        UIPanel(self.left_panel, variant="panel", title="Codex").draw(s, self.app.small_font)
        UIPanel(self.right_panel, variant="alt", title="Contenido").draw(s, self.app.small_font)

        portrait = self.app.assets.sprite("avatar", "codex", (84, 84), fallback=(86, 56, 132))
        s.blit(portrait, (self.left_panel.x + self.left_panel.w - 106, self.left_panel.y + 10))

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for rect, sid in self.section_buttons:
            sec = self.section_by_id.get(sid, {})
            label = str(sec.get("title", sid)).strip() or sid
            role = "execute" if sid == self.active_section_id else "default"
            UIButton(rect, label, role=role, premium=(sid == self.active_section_id)).draw(
                s,
                self.app.tiny_font,
                hovered=rect.collidepoint(mouse),
            )

        active = self._active_section()
        title = str(active.get("title", "Codex"))
        s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (self.right_panel.x + 20, self.right_panel.y + 20))

        y = self.right_panel.y + 84
        for line in list(active.get("items", [])):
            for wrapped in self._wrap(f"- {line}", self.right_panel.w - 40, max_lines=3):
                s.blit(self.app.font.render(wrapped, True, UI_THEME["text"]), (self.right_panel.x + 20, y))
                y += 30
            y += 8

        for hint in self._dynamic_hints_for_section(str(active.get("id", ""))):
            txt = UILabel.clamp(hint, self.app.small_font, self.right_panel.w - 40)
            s.blit(self.app.small_font.render(txt, True, UI_THEME["muted"]), (self.right_panel.x + 20, y))
            y += 28

        UIButton(self.back_btn, "Volver", role="default", premium=False).draw(s, self.app.font, hovered=self.back_btn.collidepoint(mouse))
        UIButton(self.tutorial_btn, "Iniciar Tutorial Guiado", role="end_turn", premium=True).draw(s, self.app.font, hovered=self.tutorial_btn.collidepoint(mouse))
