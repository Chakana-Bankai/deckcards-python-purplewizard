import pygame

from game.settings import INTERNAL_WIDTH
from game.ui.components.pixel_icons import draw_icon_with_value
from game.ui.theme import UI_THEME


class PathSelectScreen:
    def __init__(self, app):
        self.app = app
        self.hover_index = None
        self.selected_index = 0
        self.anim = {}
        self.options = [
            {
                "name": "Cosmic Warrior",
                "icon": "sword",
                "lore": "Guerreros del Hanan Pacha que rompen la Trama con embates astrales.",
                "legendary": "chakana_de_luz",
                "deck": [
                    # 12 common
                    "filo_astral", "filo_astral", "estallido_arcano", "pulso_cosmico", "garra_espiritual", "fragmento_celeste",
                    "invocacion_astral", "vision_del_condor", "lectura_del_destino", "sello_protector", "guardia_terrenal", "escudo_de_luz",
                    # 7 rare (rare + uncommon tier)
                    "embate_del_jaguar", "filo_en_cadena", "resistencia_ancestral", "vinculo_de_energia", "silencio_interior", "portal_de_la_chakana", "fusion_espiritual",
                    # 1 legendary
                    "chakana_de_luz",
                ],
            },
            {
                "name": "Harmony Guardian",
                "icon": "shield",
                "lore": "Custodios del Kay Pacha; bloquean, sostienen y equilibran cada combate.",
                "legendary": "chakana_de_luz",
                "deck": [
                    # 12 common
                    "sello_protector", "sello_protector", "muralla_de_piedra", "escudo_de_luz", "escudo_del_chaman", "espiritu_guardian",
                    "firmeza_del_cuerpo", "guardia_terrenal", "observacion_sagrada", "vision_del_condor", "lectura_del_destino", "mantra_del_umbral",
                    # 7 rare (rare + uncommon tier)
                    "campo_protector", "resistencia_ancestral", "silencio_interior", "vinculo_de_energia", "portal_de_la_chakana", "embate_del_jaguar", "piedra_ritual",
                    # 1 legendary
                    "chakana_de_luz",
                ],
            },
            {
                "name": "Oracle of Fate",
                "icon": "eye",
                "lore": "Videntes del Ukhu Pacha que leen destinos y activan rituales inevitables.",
                "legendary": "ritual_de_la_trama",
                "deck": [
                    # 12 common
                    "lectura_del_destino", "lectura_del_destino", "observacion_sagrada", "vision_del_condor", "invocacion_astral", "fragmento_celeste",
                    "mantra_del_umbral", "sello_protector", "guardia_terrenal", "pulso_cosmico", "filo_astral", "espiritu_guardian",
                    # 7 rare (rare + uncommon tier)
                    "revelacion_astral", "vinculo_de_energia", "portal_de_la_chakana", "silencio_interior", "campo_protector", "fusion_espiritual", "eco_de_sabiduria",
                    # 1 legendary
                    "ritual_de_la_trama",
                ],
            },
        ]

    def on_enter(self):
        self._validate_options()

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

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.goto_menu()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            opt = self.options[self.selected_index]
            self.app.sfx.play("ui_click")
            self.app.start_run_with_deck(opt["deck"])
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for i, _ in enumerate(self.options):
                r = self._option_rect(i)
                if r.collidepoint(pos):
                    self.selected_index = i
                    self.app.sfx.play("ui_click")
                    self.app.start_run_with_deck(self.options[i]["deck"])
                    return

    def update(self, dt):
        pass

    def _option_rect(self, index: int) -> pygame.Rect:
        cols = 3
        card_w, card_h = 585, 620
        gap_x = 42
        col = index % cols
        total_w = cols * card_w + (cols - 1) * gap_x
        x0 = (INTERNAL_WIDTH - total_w) // 2
        y0 = 180
        return pygame.Rect(x0 + col * (card_w + gap_x), y0, card_w, card_h)

    def _card_icons(self, card_def: dict) -> list[str]:
        tags = set(card_def.get("tags", []) or [])
        effects = list(card_def.get("effects", []) or [])
        icons = []
        if "attack" in tags:
            icons.append("sword")
        if "skill" in tags or any(str(e.get("type", "")) in {"block", "gain_block"} for e in effects if isinstance(e, dict)):
            icons.append("shield")
        if any(str(e.get("type", "")) == "draw" for e in effects if isinstance(e, dict)):
            icons.append("scroll")
        if any(str(e.get("type", "")) == "scry" for e in effects if isinstance(e, dict)):
            icons.append("eye")
        if any(str(e.get("type", "")) in {"energy", "gain_mana"} for e in effects if isinstance(e, dict)):
            icons.append("bolt")
        if "ritual" in tags:
            icons.append("star")
        return icons[:2] or ["star"]

    def _draw_deck_preview(self, s: pygame.Surface, rect: pygame.Rect, deck: list[str]):
        preview = deck[:5]
        for idx, cid in enumerate(preview):
            cd = self.app.card_defs.get(cid, {})
            pr = pygame.Rect(rect.x + 18 + idx * 112, rect.y + 190, 102, 146)
            pygame.draw.rect(s, (50, 44, 61), pr, border_radius=8)
            pygame.draw.rect(s, UI_THEME["accent_violet"], pr, 1, border_radius=8)
            name = self.app.loc.t(cd.get("name_key", cid)) if isinstance(cd, dict) else str(cid)
            s.blit(self.app.tiny_font.render(str(name)[:12], True, UI_THEME["text"]), (pr.x + 6, pr.y + 8))
            x = pr.x + 6
            for icon in self._card_icons(cd if isinstance(cd, dict) else {}):
                x = draw_icon_with_value(s, icon, 1, UI_THEME["gold"], self.app.tiny_font, x, pr.y + 34, size=1)
            cost = int(cd.get("cost", 1)) if isinstance(cd, dict) else 1
            pygame.draw.circle(s, UI_THEME["energy"], (pr.right - 12, pr.y + 12), 10)
            s.blit(self.app.tiny_font.render(str(cost), True, UI_THEME["text_dark"]), (pr.right - 15, pr.y + 6))

    def _draw_legendary_preview(self, s: pygame.Surface, rect: pygame.Rect, legendary_id: str):
        card = self.app.card_defs.get(legendary_id, {})
        box = pygame.Rect(rect.x + 18, rect.y + 370, rect.w - 36, 190)
        pygame.draw.rect(s, (61, 50, 34), box, border_radius=12)
        pygame.draw.rect(s, UI_THEME["gold"], box, 2, border_radius=12)
        title = self.app.loc.t(card.get("name_key", legendary_id))
        text = self.app.loc.t(card.get("text_key", ""))
        s.blit(self.app.small_font.render("Legendary Preview", True, UI_THEME["gold"]), (box.x + 14, box.y + 12))
        s.blit(self.app.small_font.render(str(title), True, UI_THEME["text"]), (box.x + 14, box.y + 44))
        s.blit(self.app.tiny_font.render(str(text)[:72], True, UI_THEME["muted"]), (box.x + 14, box.y + 78))
        s.blit(self.app.tiny_font.render("Deck: 12 Common • 7 Rare • 1 Legendary", True, UI_THEME["text"]), (box.x + 14, box.y + 154))

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render("Choose Your Archetype", True, UI_THEME["text"]), (INTERNAL_WIDTH // 2 - 240, 52))
        s.blit(self.app.small_font.render("Tesla 3-6-9 Model • v0.9 = 3 archetypes", True, UI_THEME["muted"]), (INTERNAL_WIDTH // 2 - 210, 90))
        s.blit(self.app.tiny_font.render("Roadmap: v1.0 → 6 archetypes • Future → 9 archetypes", True, UI_THEME["accent_violet"]), (INTERNAL_WIDTH // 2 - 230, 122))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())

        for i, opt in enumerate(self.options):
            r = self._option_rect(i)
            hover = r.collidepoint(mouse)
            if hover:
                self.hover_index = i
                self.selected_index = i

            target = 1.02 if (hover or self.selected_index == i) else 1.0
            cur = self.anim.get(i, 1.0)
            cur = cur + (target - cur) * 0.18
            self.anim[i] = cur
            rr = r.inflate(int((cur - 1.0) * r.w), int((cur - 1.0) * r.h))
            rr.center = r.center

            pygame.draw.rect(s, UI_THEME["panel"], rr, border_radius=12)
            if self.selected_index == i:
                pygame.draw.rect(s, UI_THEME["gold"], rr, 3, border_radius=12)
            elif hover:
                pygame.draw.rect(s, UI_THEME["accent_violet"], rr, 2, border_radius=12)

            draw_icon_with_value(s, opt["icon"], 1, UI_THEME["gold"], self.app.small_font, rr.x + 16, rr.y + 14, size=2)
            s.blit(self.app.map_font.render(opt["name"], True, UI_THEME["gold"]), (rr.x + 56, rr.y + 14))
            s.blit(self.app.small_font.render(opt["lore"], True, UI_THEME["muted"]), (rr.x + 16, rr.y + 58))
            self._draw_deck_preview(s, rr, opt["deck"])
            self._draw_legendary_preview(s, rr, opt["legendary"])
            s.blit(self.app.tiny_font.render("Enter or click to start run", True, UI_THEME["accent_violet"]), (rr.x + 16, rr.bottom - 24))
