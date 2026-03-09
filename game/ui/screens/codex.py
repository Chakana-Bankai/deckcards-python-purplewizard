from __future__ import annotations

import json

import pygame

from game.core.paths import data_dir
from game.ui.components.card_renderer import render_card_preview
from game.ui.theme import UI_THEME
from game.ui.system.components import UIButton, UIPanel, UILabel
from game.ui.system.safety import wrap_lines, clamp_single_line


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
        self.lore_set_cards = self._load_lore_set_cards()
        self.lore_set_relics = self._load_lore_set_relics()
        self.active_section_id = self.sections[0].get("id", "lore") if self.sections else "lore"
        self.gallery_index = 0
        self.card_set_tab = "all"
        self.card_tab_rects: list[tuple[pygame.Rect, str]] = []

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

    def _load_lore_set_cards(self) -> dict:
        path = data_dir() / "codex_cards_lore_set1.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            return {}
        return {}

    def _load_lore_set_relics(self) -> dict:
        path = data_dir() / "codex_relics_lore_set1.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            return {}
        return {}

    def _build_section_buttons(self):
        self.section_buttons = []
        y = self.left_panel.y + 16
        for section in self.sections:
            r = pygame.Rect(self.left_panel.x + 14, y, self.left_panel.w - 28, 52)
            self.section_buttons.append((r, str(section.get("id", ""))))
            y += 58

    def _active_section(self) -> dict:
        return self.section_by_id.get(self.active_section_id, self.sections[0] if self.sections else {})

    def _codex_cards(self) -> list[dict]:
        payload = self.lore_set_cards if isinstance(self.lore_set_cards, dict) else {}
        items = payload.get("cards", []) if isinstance(payload.get("cards", []), list) else []
        if not items:
            return []
        defs = self.app.card_defs if isinstance(self.app.card_defs, dict) else {}
        out = []
        for c in items:
            cid = str(c.get("id", ""))
            full = dict(defs.get(cid, {})) if cid in defs else {}
            if not full:
                full = {
                    "id": cid,
                    "name_key": str(c.get("name", cid)),
                    "text_key": str(c.get("gameplay_text", "")),
                    "role": str(c.get("role", "control")),
                    "rarity": str(c.get("rarity", "common")),
                    "cost": 1,
                    "tags": list(c.get("tags", []) or []),
                    "effects": [],
                    "archetype": str(c.get("archetype", "")),
                    "lore_text": str(c.get("lore_text", "")),
                }
            full.setdefault("id", cid)
            full.setdefault("name_key", str(c.get("name", cid)))
            full.setdefault("text_key", str(c.get("gameplay_text", "")))
            full.setdefault("archetype", str(c.get("archetype", "")))
            full.setdefault("lore_text", str(c.get("lore_text", "")))
            full.setdefault("artwork", str(full.get("id", cid)))
            if str(full.get("id", "")).lower().startswith("hip_"):
                full.setdefault("set", "hiperboria")
                full["artwork"] = str(full.get("id", cid))
            out.append(full)

        tab = str(getattr(self, "card_set_tab", "all") or "all").lower()
        if tab == "base":
            out = [c for c in out if not (str(c.get("id", "")).lower().startswith("hip_") or "hiperboria" in str(c.get("set", "")).lower())]
        elif tab == "hiperborea":
            out = [c for c in out if (str(c.get("id", "")).lower().startswith("hip_") or "hiperboria" in str(c.get("set", "")).lower())]
        return out

    def _codex_relics(self) -> list[dict]:
        payload = self.lore_set_relics if isinstance(self.lore_set_relics, dict) else {}
        items = payload.get("relics", []) if isinstance(payload.get("relics", []), list) else []
        if items:
            return [dict(x) for x in items if isinstance(x, dict) and x.get("id")]
        return [dict(x) for x in list(getattr(self.app, "relics_data", []) or []) if isinstance(x, dict) and x.get("id")]

    def _dynamic_hints_for_section(self, sid: str) -> list[str]:
        run = self.app.run_state if isinstance(self.app.run_state, dict) else {}
        if sid == "cards":
            total = len(getattr(self.app, "cards_data", []) or [])
            roles = sorted({str(c.get("role", "")).lower() for c in (getattr(self.app, "cards_data", []) or []) if isinstance(c, dict) and c.get("role")})
            lore_payload = self.lore_set_cards if isinstance(self.lore_set_cards, dict) else {}
            set_total = int(lore_payload.get("total_cards", 0) or 0)
            arcs = lore_payload.get("archetypes", []) if isinstance(lore_payload.get("archetypes", []), list) else []
            arc_line = ", ".join(f"{str(a.get('name','?'))}: {int(a.get('count',0) or 0)}" for a in arcs[:3])
            hints = [f"Cartas cargadas: {total}", f"Roles detectados: {', '.join(roles) if roles else 'sin datos'}"]
            if set_total:
                hints.append(f"Lore Set 1: {set_total} cartas")
            if arc_line:
                hints.append(arc_line)
            hints.append("Usa flechas izquierda/derecha para explorar la galeria.")
            return hints
        if sid == "relics":
            relics = self._codex_relics()
            tiers = sorted({str(r.get("tier", r.get("rarity", ""))).lower() for r in relics if isinstance(r, dict)})
            return [f"Reliquias: {len(relics)}", f"Tiers: {', '.join(tiers) if tiers else 'sin datos'}", "Navega con flechas o rueda del mouse."]
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
        return wrap_lines(font, text, width, max_lines)

    def _draw_gallery_shell(self, s: pygame.Surface) -> pygame.Rect:
        gallery = pygame.Rect(self.right_panel.x + 18, self.right_panel.y + 86, self.right_panel.w - 36, self.right_panel.h - 190)
        pygame.draw.rect(s, UI_THEME["panel_2"], gallery, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], gallery, 1, border_radius=12)
        return gallery

    def _draw_cards_gallery(self, s: pygame.Surface):
        cards = self._codex_cards()
        if not cards:
            s.blit(self.app.font.render("Sin cartas en Lore Set 1.", True, UI_THEME["muted"]), (self.right_panel.x + 20, self.right_panel.y + 90))
            return

        self.gallery_index = max(0, min(len(cards) - 1, int(self.gallery_index)))
        gallery = self._draw_gallery_shell(s)

        center_rect = pygame.Rect(0, 0, 520, 720)
        center_rect.center = (gallery.centerx, gallery.centery + 12)
        left_rect = pygame.Rect(0, 0, 290, 410)
        left_rect.center = (gallery.centerx - 380, gallery.centery + 26)
        right_rect = pygame.Rect(0, 0, 290, 410)
        right_rect.center = (gallery.centerx + 380, gallery.centery + 26)

        def _draw_card_slot(card, target_rect, angle=0):
            tmp = pygame.Surface((target_rect.w, target_rect.h), pygame.SRCALPHA)
            render_card_preview(tmp, tmp.get_rect(), card, theme=UI_THEME, state={"app": self.app, "ctx": None, "selected": False, "hovered": False, "render_context": "codex_view"})
            if angle != 0:
                tmp = pygame.transform.rotozoom(tmp, angle, 1.0)
            tr = tmp.get_rect(center=target_rect.center)
            s.blit(tmp, tr.topleft)

        if self.gallery_index > 0:
            _draw_card_slot(cards[self.gallery_index - 1], left_rect, angle=8)
        if self.gallery_index < len(cards) - 1:
            _draw_card_slot(cards[self.gallery_index + 1], right_rect, angle=-8)
        _draw_card_slot(cards[self.gallery_index], center_rect, angle=0)

        current = cards[self.gallery_index]
        label = f"{self.gallery_index + 1}/{len(cards)}  {current.get('name_key', current.get('id', ''))}"
        s.blit(self.app.small_font.render(label, True, UI_THEME["gold"]), (gallery.x + 16, gallery.bottom - 74))
        s.blit(self.app.tiny_font.render(str(current.get("archetype", "")).replace("_", " "), True, UI_THEME["muted"]), (gallery.x + 16, gallery.bottom - 48))

    def _draw_relics_gallery(self, s: pygame.Surface):
        relics = self._codex_relics()
        if not relics:
            s.blit(self.app.font.render("Sin reliquias cargadas.", True, UI_THEME["muted"]), (self.right_panel.x + 20, self.right_panel.y + 90))
            return

        self.gallery_index = max(0, min(len(relics) - 1, int(self.gallery_index)))
        gallery = self._draw_gallery_shell(s)

        center_rect = pygame.Rect(0, 0, 520, 690)
        center_rect.center = (gallery.centerx, gallery.centery + 4)
        left_rect = pygame.Rect(0, 0, 280, 380)
        left_rect.center = (gallery.centerx - 360, gallery.centery + 24)
        right_rect = pygame.Rect(0, 0, 280, 380)
        right_rect.center = (gallery.centerx + 360, gallery.centery + 24)

        def _draw_relic_slot(item: dict, target_rect: pygame.Rect, angle: float = 0.0):
            tmp = pygame.Surface((target_rect.w, target_rect.h), pygame.SRCALPHA)
            panel = tmp.get_rect()
            pygame.draw.rect(tmp, UI_THEME["panel"], panel, border_radius=12)
            pygame.draw.rect(tmp, UI_THEME["gold"], panel, 2, border_radius=12)
            rid = str(item.get("id", "relic"))
            name = self.app.loc.t(item.get("name_key", "")) if item.get("name_key") else str(item.get("name", rid))
            desc = self.app.loc.t(item.get("text_key", "")) if item.get("text_key") else str(item.get("effect", ""))
            lore = str(item.get("lore_text") or item.get("lore") or "")
            tier = str(item.get("tier", item.get("rarity", "common"))).title()

            art_slot = pygame.Rect(panel.x + 18, panel.y + 42, panel.w - 36, int(panel.h * 0.42))
            pygame.draw.rect(tmp, UI_THEME["panel_2"], art_slot, border_radius=8)
            pygame.draw.rect(tmp, UI_THEME["accent_violet"], art_slot, 1, border_radius=8)
            art = self.app.assets.sprite("relics", rid, (192, 192), fallback=(96, 76, 124))
            iw, ih = art.get_size()
            if iw > 0 and ih > 0:
                scale = min((art_slot.w - 10) / float(iw), (art_slot.h - 10) / float(ih))
                tw, th = max(1, int(iw * scale)), max(1, int(ih * scale))
                img = pygame.transform.scale(art, (tw, th))
                tmp.blit(img, img.get_rect(center=art_slot.center).topleft)

            tmp.blit(self.app.tiny_font.render(tier, True, UI_THEME["gold"]), (panel.x + 18, panel.y + 12))
            tmp.blit(self.app.small_font.render(UILabel.clamp(name, self.app.small_font, panel.w - 34), True, UI_THEME["text"]), (panel.x + 18, art_slot.bottom + 10))
            y = art_slot.bottom + 40
            for line in self._wrap(desc or "Reliquia ancestral.", panel.w - 34, max_lines=2):
                tmp.blit(self.app.tiny_font.render(line, True, UI_THEME["muted"]), (panel.x + 18, y))
                y += 20
            if lore:
                tmp.blit(self.app.tiny_font.render(UILabel.clamp(lore, self.app.tiny_font, panel.w - 34), True, UI_THEME["text"]), (panel.x + 18, min(panel.bottom - 26, y + 8)))

            if angle != 0:
                tmp = pygame.transform.rotozoom(tmp, angle, 1.0)
            tr = tmp.get_rect(center=target_rect.center)
            s.blit(tmp, tr.topleft)

        if self.gallery_index > 0:
            _draw_relic_slot(relics[self.gallery_index - 1], left_rect, angle=7)
        if self.gallery_index < len(relics) - 1:
            _draw_relic_slot(relics[self.gallery_index + 1], right_rect, angle=-7)
        _draw_relic_slot(relics[self.gallery_index], center_rect, angle=0)

        current = relics[self.gallery_index]
        name = self.app.loc.t(current.get("name_key", "")) if current.get("name_key") else str(current.get("name", current.get("id", "-")))
        label = f"{self.gallery_index + 1}/{len(relics)}  {name}"
        s.blit(self.app.small_font.render(clamp_single_line(self.app.small_font, label, gallery.w - 40), True, UI_THEME["gold"]), (gallery.x + 16, gallery.bottom - 74))

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
            if self.active_section_id in {"cards", "relics"}:
                items = self._codex_cards() if self.active_section_id == "cards" else self._codex_relics()
                if items:
                    if event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.gallery_index = min(len(items) - 1, self.gallery_index + 1)
                        return
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        self.gallery_index = max(0, self.gallery_index - 1)
                        return

        if event.type == pygame.MOUSEWHEEL and self.active_section_id in {"cards", "relics"}:
            items = self._codex_cards() if self.active_section_id == "cards" else self._codex_relics()
            if items:
                self.gallery_index = max(0, min(len(items) - 1, self.gallery_index - int(event.y)))
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
            if self.active_section_id == "cards":
                for tr, tab_id in self.card_tab_rects:
                    if tr.collidepoint(pos):
                        self.app.sfx.play("ui_click")
                        self.card_set_tab = tab_id
                        self.gallery_index = 0
                        return

            for rect, sid in self.section_buttons:
                if rect.collidepoint(pos):
                    self.app.sfx.play("ui_click")
                    self.active_section_id = sid
                    self.gallery_index = 0
                    if sid != "cards":
                        self.card_set_tab = "all"
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

        portrait = self.app.assets.sprite("avatar", "chakana_mage_concept", (84, 84), fallback=(86, 56, 132))
        s.blit(portrait, (self.left_panel.x + self.left_panel.w - 106, self.left_panel.y + 10))

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for rect, sid in self.section_buttons:
            sec = self.section_by_id.get(sid, {})
            label = str(sec.get("title", sid)).strip() or sid
            role = "execute" if sid == self.active_section_id else "default"
            UIButton(rect, label, role=role, premium=(sid == self.active_section_id)).draw(s, self.app.tiny_font, hovered=rect.collidepoint(mouse))

        active = self._active_section()
        active_id = str(active.get("id", ""))
        title = str(active.get("title", "Codex"))
        s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (self.right_panel.x + 20, self.right_panel.y + 20))

        if active_id == "cards":
            tabs = [("all", "Todo"), ("base", "Base"), ("hiperborea", "Hiperborea"), ("relics", "Relics"), ("lore", "Lore")]
            self.card_tab_rects = []
            tx = self.right_panel.x + 20
            ty = self.right_panel.y + 58
            for tid, lbl in tabs:
                tw = 116 if tid != "hiperborea" else 154
                tr = pygame.Rect(tx, ty, tw, 28)
                self.card_tab_rects.append((tr, tid))
                on = (tid == self.card_set_tab)
                pygame.draw.rect(s, UI_THEME["panel_2"], tr, border_radius=8)
                pygame.draw.rect(s, UI_THEME["gold"] if on else UI_THEME["accent_violet"], tr, 2 if on else 1, border_radius=8)
                s.blit(self.app.tiny_font.render(lbl, True, UI_THEME["gold"] if on else UI_THEME["muted"]), (tr.x + 8, tr.y + 6))
                tx += tr.w + 8
            self._draw_cards_gallery(s)
            y = self.right_panel.bottom - 86
            for hint in self._dynamic_hints_for_section("cards")[:3]:
                txt = UILabel.clamp(hint, self.app.tiny_font, self.right_panel.w - 40)
                s.blit(self.app.tiny_font.render(txt, True, UI_THEME["muted"]), (self.right_panel.x + 20, y))
                y += 20
        elif active_id == "relics":
            self._draw_relics_gallery(s)
            y = self.right_panel.bottom - 86
            for hint in self._dynamic_hints_for_section("relics")[:3]:
                txt = UILabel.clamp(hint, self.app.tiny_font, self.right_panel.w - 40)
                s.blit(self.app.tiny_font.render(txt, True, UI_THEME["muted"]), (self.right_panel.x + 20, y))
                y += 20
        else:
            y = self.right_panel.y + 84
            for line in list(active.get("items", [])):
                for wrapped in self._wrap(f"- {line}", self.right_panel.w - 40, max_lines=3):
                    s.blit(self.app.font.render(wrapped, True, UI_THEME["text"]), (self.right_panel.x + 20, y))
                    y += 30
                y += 8

            for hint in self._dynamic_hints_for_section(active_id):
                txt = UILabel.clamp(hint, self.app.small_font, self.right_panel.w - 40)
                s.blit(self.app.small_font.render(txt, True, UI_THEME["muted"]), (self.right_panel.x + 20, y))
                y += 28

        UIButton(self.back_btn, "Volver", role="default", premium=False).draw(s, self.app.font, hovered=self.back_btn.collidepoint(mouse))
        UIButton(self.tutorial_btn, "Iniciar Tutorial Guiado", role="end_turn", premium=True).draw(s, self.app.font, hovered=self.tutorial_btn.collidepoint(mouse))




