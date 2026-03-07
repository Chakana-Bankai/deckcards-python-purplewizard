import math
import pygame

from game.settings import INTERNAL_WIDTH
from game.ui.components.pixel_icons import draw_icon_with_value
from game.ui.components.card_renderer import render_card_small
from game.ui.theme import UI_THEME
from game.ui.system.components import UIPanel, UIButton
from game.ui.system.modals import ChoiceModal


class PathSelectScreen:
    def __init__(self, app):
        self.app = app
        self.hover_index = None
        self.choice_modal = ChoiceModal()
        self.choice_modal.selected_index = None
        self.anim = {}
        self.confirm_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 280, 904, 380, 56)
        self.cancel_rect = pygame.Rect(self.confirm_rect.right + 18, 904, 210, 56)
        self.options = [
            {
                "id": "cosmic_warrior",
                "name": "Cosmic Warrior",
                "icon": "sword",
                "lore": "Guerreros del Hanan Pacha que rompen la Trama con embates astrales.",
                "identity": "Alta presion ofensiva con remates de ruptura.",
                "traits": ["Burst alto", "Ruptura estable", "Cierre rapido"],
                "legendary": "chakana_de_luz",
                "profile": {"ataque": 5, "defensa": 2, "control": 2, "ritual": 3, "tempo": 4},
                "deck": [
                    "filo_astral", "filo_astral", "estallido_arcano", "pulso_cosmico", "garra_espiritual", "fragmento_celeste",
                    "invocacion_astral", "vision_del_condor", "lectura_del_destino", "sello_protector", "guardia_terrenal", "escudo_de_luz",
                    "embate_del_jaguar", "filo_en_cadena", "resistencia_ancestral", "vinculo_de_energia", "silencio_interior", "portal_de_la_chakana", "fusion_espiritual",
                    "chakana_de_luz",
                ],
            },
            {
                "id": "harmony_guardian",
                "name": "Harmony Guardian",
                "icon": "shield",
                "lore": "Custodios del Kay Pacha; bloquean, sostienen y equilibran cada combate.",
                "identity": "Arquetipo defensivo con escalado de armonia.",
                "traits": ["Mitigacion alta", "Plan estable", "Contraataque"],
                "legendary": "chakana_de_luz",
                "profile": {"ataque": 2, "defensa": 5, "control": 3, "ritual": 4, "tempo": 2},
                "deck": [
                    "sello_protector", "sello_protector", "muralla_de_piedra", "escudo_de_luz", "escudo_del_chaman", "espiritu_guardian",
                    "firmeza_del_cuerpo", "guardia_terrenal", "observacion_sagrada", "vision_del_condor", "lectura_del_destino", "mantra_del_umbral",
                    "campo_protector", "resistencia_ancestral", "silencio_interior", "vinculo_de_energia", "portal_de_la_chakana", "embate_del_jaguar", "piedra_ritual",
                    "chakana_de_luz",
                ],
            },
            {
                "id": "oracle_of_fate",
                "name": "Oracle of Fate",
                "icon": "eye",
                "lore": "Videntes del Ukhu Pacha que leen destinos y activan rituales inevitables.",
                "identity": "Control de flujo con scry y valor ritual.",
                "traits": ["Lectura de mano", "Ritual tactico", "Escalado"],
                "legendary": "ritual_de_la_trama",
                "profile": {"ataque": 2, "defensa": 3, "control": 5, "ritual": 5, "tempo": 3},
                "deck": [
                    "lectura_del_destino", "lectura_del_destino", "observacion_sagrada", "vision_del_condor", "invocacion_astral", "fragmento_celeste",
                    "mantra_del_umbral", "sello_protector", "guardia_terrenal", "pulso_cosmico", "filo_astral", "espiritu_guardian",
                    "revelacion_astral", "vinculo_de_energia", "portal_de_la_chakana", "silencio_interior", "campo_protector", "fusion_espiritual", "eco_de_sabiduria",
                    "ritual_de_la_trama",
                ],
            },
        ]

    def on_enter(self):
        self._validate_options()
        # Defensive reset to avoid stale modal chrome leaking into archetype flow.
        self.choice_modal.hide()
        self.choice_modal.title = ""
        self.choice_modal.message = ""
        self.choice_modal.selected_index = None
        self.choice_modal.hover_index = None
        self.choice_modal.choices = [{"title": opt.get("name", "Arquetipo"), "subtitle": opt.get("identity", "")} for opt in self.options]
    def _validate_options(self):
        cards = self.app.card_defs if isinstance(self.app.card_defs, dict) else {}
        for opt in self.options:
            deck = list(opt.get("deck", []))
            if len(deck) != 20:
                raise ValueError(f"Archetype '{opt.get('name')}' must have exactly 20 cards")
            commons = 0
            rares = 0
            legendary = 0
            for cid in deck:
                rarity = str(cards.get(cid, {}).get("rarity", "")).lower()
                if rarity == "common":
                    commons += 1
                elif rarity in {"uncommon", "rare"}:
                    rares += 1
                elif rarity == "legendary":
                    legendary += 1
            if (commons, rares, legendary) != (12, 7, 1):
                raise ValueError(
                    f"Archetype '{opt.get('name')}' invalid 12-7-1 distribution: {(commons, rares, legendary)}"
                )

    def _confirm_enabled(self) -> bool:
        return self.choice_modal.selected_index is not None

    def _confirm_selection(self):
        if not self._confirm_enabled():
            try:
                self.app.sfx.play("deny")
            except Exception:
                pass
            return
        opt = self.options[self.choice_modal.selected_index]
        self.app.sfx.play("ui_click")
        self.app.start_run_with_deck(opt["deck"])

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.goto_menu()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._confirm_selection()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.confirm_rect.collidepoint(pos):
                self._confirm_selection()
                return
            if self.cancel_rect.collidepoint(pos):
                self.app.sfx.play("ui_click")
                self.app.goto_menu()
                return
            for i, _ in enumerate(self.options):
                r = self._option_rect(i)
                if r.collidepoint(pos):
                    if self.choice_modal.selected_index == i:
                        self.choice_modal.selected_index = None
                    else:
                        self.choice_modal.selected_index = i
                    self.app.sfx.play("ui_click")
                    return

    def update(self, dt):
        pass

    def _option_rect(self, index: int) -> pygame.Rect:
        cols = 3
        card_w, card_h = 540, 620
        gap_x = 34
        col = index % cols
        total_w = cols * card_w + (cols - 1) * gap_x
        x0 = (INTERNAL_WIDTH - total_w) // 2
        y0 = 182
        return pygame.Rect(x0 + col * (card_w + gap_x), y0, card_w, card_h)

    def _fit(self, font, text: str, max_w: int) -> str:
        out = str(text or "").replace("\n", " ").strip()
        while font.size(out)[0] > max_w and len(out) > 4:
            out = out[:-4] + "..."
        return out

    def _draw_radar(self, s: pygame.Surface, center: tuple[int, int], radius: int, profile: dict[str, int], color):
        keys = ["ataque", "defensa", "control", "ritual", "tempo"]
        pts = []
        for i, k in enumerate(keys):
            a = -math.pi / 2 + (2 * math.pi * i / len(keys))
            v = max(1, min(5, int(profile.get(k, 1)))) / 5.0
            pts.append((center[0] + int(math.cos(a) * radius * v), center[1] + int(math.sin(a) * radius * v)))

        for ring in range(1, 6):
            rr = int(radius * (ring / 5.0))
            pygame.draw.circle(s, (74, 70, 96), center, rr, 1)
        for i in range(len(keys)):
            a = -math.pi / 2 + (2 * math.pi * i / len(keys))
            x = center[0] + int(math.cos(a) * radius)
            y = center[1] + int(math.sin(a) * radius)
            pygame.draw.line(s, (78, 74, 102), center, (x, y), 1)

        poly = pygame.Surface((radius * 2 + 16, radius * 2 + 16), pygame.SRCALPHA)
        shift = [(x - center[0] + radius + 8, y - center[1] + radius + 8) for x, y in pts]
        pygame.draw.polygon(poly, (*color, 92), shift)
        pygame.draw.polygon(poly, color, shift, 2)
        s.blit(poly, (center[0] - radius - 8, center[1] - radius - 8))

    def _draw_featured_legendary(self, s: pygame.Surface, rect: pygame.Rect, legendary_id: str):
        card = self.app.card_defs.get(legendary_id, {})
        box = pygame.Rect(rect.x + 18, rect.y + rect.h - 164, rect.w - 36, 124)
        pygame.draw.rect(s, (56, 42, 30), box, border_radius=12)
        pygame.draw.rect(s, UI_THEME["gold"], box, 2, border_radius=12)

        art_rect = pygame.Rect(box.x + 10, box.y + 10, 110, box.h - 20)
        render_card_small(
            s,
            art_rect,
            card,
            theme=UI_THEME,
            state={"app": self.app, "ctx": None, "selected": False, "hovered": False},
        )

        title = self.app.loc.t(card.get("name_key", legendary_id))
        text = self.app.loc.t(card.get("text_key", ""))
        s.blit(self.app.tiny_font.render("Legendaria", True, UI_THEME["gold"]), (box.x + 130, box.y + 12))
        s.blit(self.app.small_font.render(self._fit(self.app.small_font, str(title), box.w - 144), True, UI_THEME["text"]), (box.x + 130, box.y + 34))
        s.blit(self.app.tiny_font.render(self._fit(self.app.tiny_font, str(text), box.w - 144), True, UI_THEME["muted"]), (box.x + 130, box.y + 70))


    def _ensure_starter_banner(self, option: dict):
        # Stabilization pass: avoid runtime asset writes from UI rendering.
        return

    def render(self, s):
        self.confirm_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 280, 904, 380, 56)
        self.cancel_rect = pygame.Rect(self.confirm_rect.right + 18, 904, 210, 56)
        s.fill(UI_THEME["bg"])
        title = self.app.big_font.render("Elige tu Arquetipo", True, UI_THEME["text"])
        sub = self.app.small_font.render("Selecciona un mazo inicial para comenzar.", True, UI_THEME["muted"])
        s.blit(title, title.get_rect(center=(INTERNAL_WIDTH // 2, 56)))
        s.blit(sub, sub.get_rect(center=(INTERNAL_WIDTH // 2, 94)))

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.hover_index = None

        accents = [(214, 86, 132), (126, 198, 180), (168, 140, 244)]
        for i, opt in enumerate(self.options):
            r = self._option_rect(i)
            hover = r.collidepoint(mouse)
            if hover:
                self.hover_index = i

            selected = self.choice_modal.selected_index == i
            target = 1.02 if (hover or selected) else 1.0
            cur = self.anim.get(i, 1.0)
            cur = cur + (target - cur) * 0.18
            self.anim[i] = cur
            rr = r.inflate(int((cur - 1.0) * r.w), int((cur - 1.0) * r.h))
            rr.center = r.center

            accent = accents[i % len(accents)]
            UIPanel(rr, variant="alt" if selected else "default").draw(s)
            border = UI_THEME["gold"] if selected else accent
            bw = 4 if selected else 2
            pygame.draw.rect(s, border, rr, bw, border_radius=14)
            if selected:
                glow = pygame.Surface((rr.w + 16, rr.h + 16), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*UI_THEME["gold"], 44), glow.get_rect(), border_radius=18)
                s.blit(glow, (rr.x - 8, rr.y - 8))

            hero = pygame.Rect(rr.x + 16, rr.y + 14, rr.w - 32, 170)
            pygame.draw.rect(s, (30, 26, 40), hero, border_radius=12)
            pygame.draw.rect(s, accent, hero, 2, border_radius=12)

            banner_rect = pygame.Rect(hero.x + 4, hero.y + 4, hero.w - 8, 88)
            self._ensure_starter_banner(opt)
            banner = self.app.assets.sprite("starters", opt["id"], (banner_rect.w, banner_rect.h), fallback=(78, 52, 114))
            s.blit(banner, banner_rect.topleft)
            pygame.draw.rect(s, UI_THEME["gold"], banner_rect, 1, border_radius=8)

            draw_icon_with_value(s, opt["icon"], 1, UI_THEME["gold"], self.app.small_font, hero.x + 10, hero.y + 102, size=2)
            s.blit(self.app.map_font.render(opt["name"], True, UI_THEME["gold"]), (hero.x + 52, hero.y + 100))
            s.blit(self.app.small_font.render(self._fit(self.app.small_font, opt["lore"], hero.w - 20), True, UI_THEME["muted"]), (hero.x + 10, hero.y + 136))

            summary_box = pygame.Rect(rr.x + 18, rr.y + 196, rr.w - 36, 68)
            pygame.draw.rect(s, UI_THEME["panel_2"], summary_box, border_radius=10)
            pygame.draw.rect(s, accent, summary_box, 1, border_radius=10)
            s.blit(self.app.tiny_font.render("Estrategia", True, UI_THEME["gold"]), (summary_box.x + 10, summary_box.y + 8))
            s.blit(self.app.tiny_font.render(self._fit(self.app.tiny_font, opt["identity"], summary_box.w - 20), True, UI_THEME["text"]), (summary_box.x + 10, summary_box.y + 32))

            radar_box = pygame.Rect(rr.x + 18, rr.y + 276, rr.w - 36, 190)
            pygame.draw.rect(s, (28, 24, 38), radar_box, border_radius=10)
            pygame.draw.rect(s, accent, radar_box, 1, border_radius=10)
            s.blit(self.app.tiny_font.render("Geometria de mazo", True, UI_THEME["gold"]), (radar_box.x + 10, radar_box.y + 8))
            self._draw_radar(s, (radar_box.centerx, radar_box.y + 108), 68, opt.get("profile", {}), accent)

            self._draw_featured_legendary(s, rr, opt["legendary"])

        confirm_enabled = self._confirm_enabled()
        confirm_fill = UI_THEME["violet"] if confirm_enabled else (84, 76, 106)
        confirm_border = UI_THEME["gold"] if confirm_enabled else UI_THEME["muted"]
        if confirm_enabled:
            chosen = self.options[self.choice_modal.selected_index]["name"]
            ctext = f"Confirmar mazo: {chosen}"
        else:
            ctext = "Selecciona un mazo para confirmar"
        ctext = self._fit(self.app.small_font, ctext, self.confirm_rect.w - 20)

        confirm_btn = UIButton(self.confirm_rect, ctext, role="seal", premium=True)
        confirm_btn.disabled = not confirm_enabled
        confirm_btn.draw(s, self.app.small_font)

        cancel_btn = UIButton(self.cancel_rect, "Cancelar", role="default", premium=False)
        cancel_btn.draw(s, self.app.small_font)

