from __future__ import annotations

import json
from pathlib import Path

import pygame

from game.core.paths import data_dir
from game.ui.components.card_renderer import render_card_preview
from game.ui.theme import UI_THEME
from game.ui.system.components import UIButton, UIPanel, UILabel
from game.ui.system.safety import wrap_lines, clamp_single_line
from game.ui.system.set_emblems import draw_set_emblem, normalize_set_id


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
        self.hiperboria_set_cards = self._load_hiperboria_set_cards()
        self.arconte_set_cards = self._load_arconte_set_cards()
        self.lore_set_relics = self._load_lore_set_relics()
        self.archon_profiles = self._load_archon_profiles()
        self.active_section_id = self.sections[0].get("id", "lore") if self.sections else "lore"
        self.gallery_index = 0
        self.card_set_tab = "all"
        self.card_rarity_tab = "all"
        self.card_archetype_tab = "all"
        self.card_tab_rects: list[tuple[pygame.Rect, str]] = []
        self.card_rarity_tab_rects: list[tuple[pygame.Rect, str]] = []
        self.card_archetype_tab_rects: list[tuple[pygame.Rect, str]] = []

        self.back_btn = pygame.Rect(42, 1008, 220, 52)
        self.tutorial_btn = pygame.Rect(280, 1008, 340, 52)
        self.left_panel = pygame.Rect(34, 120, 420, 860)
        self.right_panel = pygame.Rect(474, 120, 1412, 860)

        self.section_buttons = []
        self._build_section_buttons()
        self._canon_docs = self._load_canon_docs()

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

    def _load_hiperboria_set_cards(self) -> dict:
        path = data_dir() / "codex_cards_hiperboria.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            return {}
        return {}

    def _load_arconte_set_cards(self) -> dict:
        path = data_dir() / "codex_cards_arconte.json"
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

    def _load_archon_profiles(self) -> list[dict]:
        candidates = [data_dir() / 'archons_1_0.json', data_dir() / 'enemies' / 'bosses_3.json']
        for path in candidates:
            try:
                payload = json.loads(path.read_text(encoding='utf-8-sig'))
            except Exception:
                continue
            items = payload if isinstance(payload, list) else payload.get('archons', []) if isinstance(payload, dict) else []
            out = []
            for row in items:
                if not isinstance(row, dict):
                    continue
                rid = str(row.get('id') or row.get('enemy_proxy_id') or '').strip()
                if not rid:
                    continue
                out.append(dict(row))
            if out:
                return out
        return []

    def _build_section_buttons(self):
        self.section_buttons = []
        y = self.left_panel.y + 16
        for section in self.sections:
            r = pygame.Rect(self.left_panel.x + 14, y, self.left_panel.w - 28, 52)
            self.section_buttons.append((r, str(section.get("id", ""))))
            y += 58

    def _active_section(self) -> dict:
        return self.section_by_id.get(self.active_section_id, self.sections[0] if self.sections else {})

    def _to_roman(self, value: int) -> str:
        table = {
            1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
            6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X",
            11: "XI", 12: "XII", 13: "XIII", 14: "XIV", 15: "XV",
            16: "XVI", 17: "XVII", 18: "XVIII", 19: "XIX", 20: "XX",
        }
        return table.get(int(value), str(value))

    def _display_text(self, value: str) -> str:
        return self.app.loc.t(str(value or ""))

    def _display_card_name(self, card: dict, fallback: str = "") -> str:
        raw = str(card.get("name_key") or card.get("name") or fallback or card.get("id") or "").strip()
        if (str(card.get("set", "")).lower() == "arconte" or str(card.get("id", "")).lower().startswith("arc_")) and raw.lower().startswith("arcano del vacio"):
            suffix = raw.split()[-1]
            raw = f"Arcano del Vac\u00edo {self._to_roman(int(suffix))}" if suffix.isdigit() else raw.replace("Vacio", "Vac\u00edo")
        return self._display_text(raw)

    def _codex_cards(self) -> list[dict]:
        base_payload = self.lore_set_cards if isinstance(self.lore_set_cards, dict) else {}
        base_items = base_payload.get("cards", []) if isinstance(base_payload.get("cards", []), list) else []

        hip_payload = self.hiperboria_set_cards if isinstance(self.hiperboria_set_cards, dict) else {}
        hip_items = hip_payload.get("cards", []) if isinstance(hip_payload.get("cards", []), list) else []
        arc_payload = self.arconte_set_cards if isinstance(self.arconte_set_cards, dict) else {}
        arc_items = arc_payload.get("cards", []) if isinstance(arc_payload.get("cards", []), list) else []

        # Codex must expose expansion encyclopedia regardless of acquisition gating.
        items = list(base_items)
        items.extend(list(hip_items))
        items.extend(list(arc_items))
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
            full["name_key"] = self._display_card_name(full, str(c.get("name", cid)))
            full.setdefault("text_key", str(c.get("gameplay_text", "")))
            full.setdefault("archetype", str(c.get("archetype", "")))
            full.setdefault("lore_text", str(c.get("lore_text", "")))
            full.setdefault("artwork", str(full.get("id", cid)))
            if str(full.get("id", "")).lower().startswith("hip_"):
                full.setdefault("set", "hiperboria")
                full["artwork"] = str(full.get("id", cid))
            if str(full.get("id", "")).lower().startswith("arc_"):
                full.setdefault("set", "arconte")
                full["artwork"] = str(full.get("id", cid))
            out.append(full)

        tab = str(getattr(self, "card_set_tab", "all") or "all").lower()
        if tab == "base":
            out = [c for c in out if not (str(c.get("id", "")).lower().startswith("hip_") or "hiperboria" in str(c.get("set", "")).lower() or "hiperborea" in str(c.get("set", "")).lower())]
        elif tab == "hiperborea":
            out = [c for c in out if (str(c.get("id", "")).lower().startswith("hip_") or "hiperboria" in str(c.get("set", "")).lower() or "hiperborea" in str(c.get("set", "")).lower())]
        elif tab == "arconte":
            out = [c for c in out if (str(c.get("id", "")).lower().startswith("arc_") or "arconte" in str(c.get("set", "")).lower())]

        rarity_tab = str(getattr(self, "card_rarity_tab", "all") or "all").lower()
        if rarity_tab != "all":
            out = [c for c in out if str(c.get("rarity", "")).lower() == rarity_tab]

        arch_tab = str(getattr(self, "card_archetype_tab", "all") or "all").lower()
        if arch_tab != "all":
            out = [c for c in out if str(c.get("archetype", "")).lower() == arch_tab]
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
            bosses = [self._display_text(b.get("name_es") or b.get("name_key") or b.get("id", "-")) for b in list(getattr(self.app, "content", {}).bosses or []) if isinstance(b, dict)] if hasattr(getattr(self.app, "content", None), "bosses") else []
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

    def _load_canon_docs(self) -> dict[str, dict]:
        mapping = {
            "lore": ("Lore del Universo", Path("docs/canon/lore/LORE_ATLAS.md")),
            "systems": ("Sistemas Chakana", Path("docs/canon/reference/GAME_SYSTEMS_REFERENCE.md")),
            "rules": ("Manual de Run", Path("docs/canon/manual/CHAKANA_MANUAL_1_0.md")),
            "atlas": ("Atlas de Chakana", Path("docs/canon/lore/LORE_ATLAS.md")),
            "history": ("Historia y Biblia", Path("docs/canon/manual/CHAKANA_MASTER_GAME_BIBLE_1_0.md")),
            "symbols": ("Simbolos Sagrados", Path("docs/canon/direction/ART_STYLE_GUIDE.md")),
            "tips_help": ("Tutorial y Ayuda", Path("docs/canon/manual/CHAKANA_MANUAL_1_0.md")),
        }
        out = {}
        for sid, (title, rel) in mapping.items():
            try:
                text = rel.read_text(encoding="utf-8")
            except Exception:
                continue
            paragraphs = []
            for raw in text.splitlines():
                line = str(raw).strip()
                if not line:
                    continue
                if line.startswith('#'):
                    paragraphs.append(line.lstrip('#').strip())
                elif line.startswith('- '):
                    paragraphs.append(line[2:].strip())
                elif line[0].isdigit() and '. ' in line:
                    paragraphs.append(line.split('. ', 1)[1].strip())
                else:
                    paragraphs.append(line)
            if paragraphs:
                out[sid] = {"title": title, "paragraphs": paragraphs[:18]}
        return out

    def _draw_canon_text_panel(self, s: pygame.Surface, active_id: str, title: str):
        gallery = self._draw_gallery_shell(s, top_offset=86)
        doc = dict(self._canon_docs.get(active_id, {}))
        fallback_items = [str(x) for x in list(self._active_section().get("items", []))]
        panel_title = str(doc.get("title") or title or "Codex")
        paragraphs = list(doc.get("paragraphs", [])) or fallback_items

        header_font = getattr(self.app, 'big_font', self.app.small_font)
        section_font = getattr(self.app, 'small_font', self.app.font)
        body_font = getattr(self.app, 'font', self.app.tiny_font)
        tiny_font = getattr(self.app, 'tiny_font', body_font)

        title_surf = header_font.render(panel_title, True, UI_THEME['gold'])
        s.blit(title_surf, title_surf.get_rect(center=(gallery.centerx, gallery.y + 36)).topleft)

        intro = 'Universo Chakana, reglas de run y memoria ritual en una sola vista.' if active_id in {'lore','atlas','history','symbols'} else 'Resumen canonico y tutorial jugable del sistema actual.'
        intro_lines = wrap_lines(section_font, intro, gallery.w - 120, 2)
        iy = gallery.y + 68
        for line in intro_lines:
            surf = section_font.render(line, True, UI_THEME['muted'])
            s.blit(surf, surf.get_rect(center=(gallery.centerx, iy)).topleft)
            iy += surf.get_height() + 4

        text_x = gallery.x + 90
        text_w = gallery.w - 180
        y = iy + 18
        for idx, paragraph in enumerate(paragraphs[:10]):
            if y > gallery.bottom - 120:
                break
            font = section_font if idx == 0 else body_font
            color = UI_THEME['text'] if idx < 3 else UI_THEME['muted']
            lines = wrap_lines(font, str(paragraph), text_w, 3 if idx < 3 else 2)
            for line in lines:
                surf = font.render(line, True, color)
                s.blit(surf, surf.get_rect(center=(gallery.centerx, y)).topleft)
                y += surf.get_height() + 4
            y += 10

        tips = self._dynamic_hints_for_section(active_id)[:3]
        fy = gallery.bottom - 86
        for tip in tips:
            surf = tiny_font.render(clamp_single_line(tiny_font, tip, gallery.w - 60), True, UI_THEME['gold'])
            s.blit(surf, surf.get_rect(center=(gallery.centerx, fy)).topleft)
            fy += 18

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

    def _draw_gallery_shell(self, s: pygame.Surface, top_offset: int = 86) -> pygame.Rect:
        gallery = pygame.Rect(self.right_panel.x + 18, self.right_panel.y + top_offset, self.right_panel.w - 36, self.right_panel.h - (top_offset + 104))
        pygame.draw.rect(s, UI_THEME["panel_2"], gallery, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], gallery, 1, border_radius=12)
        return gallery

    def _draw_cards_gallery(self, s: pygame.Surface):
        cards = self._codex_cards()
        if not cards:
            s.blit(self.app.font.render("Sin cartas en Lore Set 1.", True, UI_THEME["muted"]), (self.right_panel.x + 20, self.right_panel.y + 90))
            return

        self.gallery_index = max(0, min(len(cards) - 1, int(self.gallery_index)))
        gallery = self._draw_gallery_shell(s, top_offset=148)

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
        cname = self._display_card_name(current)
        label = f"{self.gallery_index + 1}/{len(cards)}  {cname}"
        label_pos = (gallery.x + 16, gallery.bottom - 74)
        s.blit(self.app.small_font.render(clamp_single_line(self.app.small_font, label, gallery.w - 88), True, UI_THEME["gold"]), label_pos)
        emblem_rect = pygame.Rect(gallery.right - 44, gallery.bottom - 80, 22, 22)
        draw_set_emblem(s, emblem_rect, normalize_set_id(current))
        s.blit(self.app.tiny_font.render(str(current.get("archetype", "")).replace("_", " "), True, UI_THEME["muted"]), (gallery.x + 16, gallery.bottom - 48))

    def _draw_archons_gallery(self, s: pygame.Surface):
        gallery = self._draw_gallery_shell(s, top_offset=86)
        archons = list(self.archon_profiles or [])
        if not archons:
            s.blit(self.app.font.render("Sin arcontes cargados.", True, UI_THEME["muted"]), (self.right_panel.x + 20, self.right_panel.y + 90))
            return

        title = self.app.big_font.render("Arcontes Activos", True, UI_THEME["gold"])
        s.blit(title, title.get_rect(center=(gallery.centerx, gallery.y + 36)).topleft)
        subtitle = self.app.small_font.render("Presencias mayores del Vacio y la corrupcion ritual.", True, UI_THEME["muted"])
        s.blit(subtitle, subtitle.get_rect(center=(gallery.centerx, gallery.y + 70)).topleft)

        card_w, card_h = 286, 280
        gap = 26
        total_w = card_w * min(4, len(archons)) + gap * max(0, min(4, len(archons)) - 1)
        start_x = gallery.centerx - total_w // 2
        y = gallery.y + 126
        for i, archon in enumerate(archons[:4]):
            rr = pygame.Rect(start_x + i * (card_w + gap), y, card_w, card_h)
            pygame.draw.rect(s, UI_THEME["panel"], rr, border_radius=16)
            pygame.draw.rect(s, UI_THEME["gold"], rr, 2, border_radius=16)
            rid = str(archon.get('enemy_proxy_id') or archon.get('id') or '')
            art_slot = pygame.Rect(rr.x + 16, rr.y + 18, rr.w - 32, 154)
            pygame.draw.rect(s, UI_THEME["panel_2"], art_slot, border_radius=10)
            pygame.draw.rect(s, UI_THEME["accent_violet"], art_slot, 1, border_radius=10)
            art = self.app.assets.sprite('avatar', f'enemy__{rid}__portrait', (art_slot.w, art_slot.h), fallback=(82, 62, 116))
            s.blit(art, art.get_rect(center=art_slot.center).topleft)
            name = self._display_text(archon.get('name_es') or archon.get('name_key') or rid)
            line1 = self.app.small_font.render(clamp_single_line(self.app.small_font, name, rr.w - 24), True, UI_THEME['text'])
            s.blit(line1, line1.get_rect(center=(rr.centerx, art_slot.bottom + 26)).topleft)
            lore = str(archon.get('lore_text') or archon.get('title') or 'Entidad mayor de la Trama quebrada.')
            lines = wrap_lines(self.app.tiny_font, lore, rr.w - 28, 3)
            ly = art_slot.bottom + 52
            for line in lines:
                surf = self.app.tiny_font.render(line, True, UI_THEME['muted'])
                s.blit(surf, surf.get_rect(center=(rr.centerx, ly)).topleft)
                ly += 18

        fy = gallery.bottom - 82
        for tip in self._dynamic_hints_for_section('archons')[:3]:
            surf = self.app.tiny_font.render(clamp_single_line(self.app.tiny_font, tip, gallery.w - 60), True, UI_THEME['gold'])
            s.blit(surf, surf.get_rect(center=(gallery.centerx, fy)).topleft)
            fy += 18

    def _draw_relics_gallery(self, s: pygame.Surface):
        relics = self._codex_relics()
        if not relics:
            s.blit(self.app.font.render("Sin reliquias cargadas.", True, UI_THEME["muted"]), (self.right_panel.x + 20, self.right_panel.y + 90))
            return

        self.gallery_index = max(0, min(len(relics) - 1, int(self.gallery_index)))
        gallery = self._draw_gallery_shell(s, top_offset=86)

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
                for tr, tab_id in self.card_rarity_tab_rects:
                    if tr.collidepoint(pos):
                        self.app.sfx.play("ui_click")
                        self.card_rarity_tab = tab_id
                        self.gallery_index = 0
                        return
                for tr, tab_id in self.card_archetype_tab_rects:
                    if tr.collidepoint(pos):
                        self.app.sfx.play("ui_click")
                        self.card_archetype_tab = tab_id
                        self.gallery_index = 0
                        return

            for rect, sid in self.section_buttons:
                if rect.collidepoint(pos):
                    self.app.sfx.play("ui_click")
                    self.active_section_id = sid
                    self.gallery_index = 0
                    if sid != "cards":
                        self.card_set_tab = "all"
                        self.card_rarity_tab = "all"
                        self.card_archetype_tab = "all"
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

        reg = getattr(self.app, "font_registry", {}) or {}
        modal_title_font = reg.get("modal_title", self.app.small_font)
        modal_label_font = reg.get("modal_label", self.app.tiny_font)
        codex_header_font = reg.get("codex_header", self.app.big_font)
        pixel_label_font = reg.get("special_pixel_label", self.app.tiny_font)

        UIPanel(self.left_panel, variant="panel", title="Codex").draw(s, modal_title_font)
        UIPanel(self.right_panel, variant="alt", title="Contenido").draw(s, modal_title_font)

        portrait = self.app.assets.sprite("avatar", "chakana_mage_concept", (84, 84), fallback=(86, 56, 132))
        s.blit(portrait, (self.left_panel.x + self.left_panel.w - 106, self.left_panel.y + 10))

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for rect, sid in self.section_buttons:
            sec = self.section_by_id.get(sid, {})
            label = str(sec.get("title", sid)).strip() or sid
            role = "execute" if sid == self.active_section_id else "default"
            UIButton(rect, label, role=role, premium=(sid == self.active_section_id)).draw(s, modal_label_font, hovered=rect.collidepoint(mouse))

        active = self._active_section()
        active_id = str(active.get("id", ""))
        title = str(active.get("title", "Codex"))
        s.blit(codex_header_font.render(title, True, UI_THEME["gold"]), (self.right_panel.x + 20, self.right_panel.y + 20))

        if active_id == "cards":
            run = self.app.run_state if isinstance(self.app.run_state, dict) else {}
            discovered = {str(x).strip().lower() for x in list(run.get("discovered_sets", []) or []) if x}
            _ = discovered
            tabs = [("all", "Todo"), ("base", "Base"), ("hiperborea", "Hiperborea"), ("arconte", "Arconte")]
            rarity_tabs = [("all", "Rareza: Todo"), ("common", "Comun"), ("uncommon", "Infrec."), ("rare", "Rara"), ("legendary", "Legend.")]
            arch_tabs = [("all", "Arquetipo: Todo"), ("cosmic_warrior", "Guerrero"), ("harmony_guardian", "Guardian"), ("oracle_of_fate", "Oraculo"), ("archon_war", "Arconte")]

            tab_ids = {tid for tid, _lbl in tabs}
            if self.card_set_tab not in tab_ids:
                self.card_set_tab = "all"
            rarity_ids = {tid for tid, _lbl in rarity_tabs}
            if self.card_rarity_tab not in rarity_ids:
                self.card_rarity_tab = "all"
            arch_ids = {tid for tid, _lbl in arch_tabs}
            if self.card_archetype_tab not in arch_ids:
                self.card_archetype_tab = "all"

            self.card_tab_rects = []
            self.card_rarity_tab_rects = []
            self.card_archetype_tab_rects = []

            tx = self.right_panel.x + 20
            ty = self.right_panel.y + 58
            for tid, lbl in tabs:
                tw = 116 if tid != "hiperborea" else 154
                tr = pygame.Rect(tx, ty, tw, 28)
                self.card_tab_rects.append((tr, tid))
                on = (tid == self.card_set_tab)
                pygame.draw.rect(s, UI_THEME["panel_2"], tr, border_radius=8)
                pygame.draw.rect(s, UI_THEME["gold"] if on else UI_THEME["accent_violet"], tr, 2 if on else 1, border_radius=8)
                s.blit(pixel_label_font.render(lbl, True, UI_THEME["gold"] if on else UI_THEME["muted"]), (tr.x + 8, tr.y + 6))
                tx += tr.w + 8

            tx = self.right_panel.x + 20
            ty = self.right_panel.y + 90
            for tid, lbl in rarity_tabs:
                tw = 164 if tid == "all" else 118
                tr = pygame.Rect(tx, ty, tw, 24)
                self.card_rarity_tab_rects.append((tr, tid))
                on = (tid == self.card_rarity_tab)
                pygame.draw.rect(s, UI_THEME["panel_2"], tr, border_radius=7)
                pygame.draw.rect(s, UI_THEME["gold"] if on else UI_THEME["accent_violet"], tr, 2 if on else 1, border_radius=7)
                s.blit(self.app.tiny_font.render(lbl, True, UI_THEME["gold"] if on else UI_THEME["muted"]), (tr.x + 7, tr.y + 5))
                tx += tr.w + 6

            tx = self.right_panel.x + 20
            ty = self.right_panel.y + 118
            for tid, lbl in arch_tabs:
                tw = 178 if tid == "all" else 128
                tr = pygame.Rect(tx, ty, tw, 24)
                self.card_archetype_tab_rects.append((tr, tid))
                on = (tid == self.card_archetype_tab)
                pygame.draw.rect(s, UI_THEME["panel_2"], tr, border_radius=7)
                pygame.draw.rect(s, UI_THEME["gold"] if on else UI_THEME["accent_violet"], tr, 2 if on else 1, border_radius=7)
                s.blit(self.app.tiny_font.render(lbl, True, UI_THEME["gold"] if on else UI_THEME["muted"]), (tr.x + 7, tr.y + 5))
                tx += tr.w + 6

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
        elif active_id == "archons":
            self._draw_archons_gallery(s)
        else:
            self._draw_canon_text_panel(s, active_id, title)

        UIButton(self.back_btn, "Volver", role="default", premium=False).draw(s, self.app.font, hovered=self.back_btn.collidepoint(mouse))
        UIButton(self.tutorial_btn, "Iniciar Tutorial Guiado", role="end_turn", premium=True).draw(s, self.app.font, hovered=self.tutorial_btn.collidepoint(mouse))










