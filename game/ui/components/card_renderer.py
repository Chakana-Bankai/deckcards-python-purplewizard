from __future__ import annotations

import random

import pygame

from game.ui.components.card_effect_summary import infer_card_role, summarize_card_effect
from game.ui.components.card_framework import to_card_framework_model
from game.ui.system.icons import draw_icon_with_value
from game.ui.theme import UI_THEME


ROLE_COLORS = {
    "attack": (222, 120, 112),
    "defense": (124, 184, 238),
    "energy": (116, 220, 252),
    "control": (174, 154, 238),
    "ritual": (228, 196, 116),
    "combo": (212, 164, 236),
}

ROLE_LABELS = {
    "attack": "ATAQUE",
    "defense": "DEFENSA",
    "energy": "ENERGIA",
    "control": "CONTROL",
    "ritual": "RITUAL",
    "combo": "COMBO",
}


def _payload(card):
    if card is None:
        return None, None
    if hasattr(card, "definition"):
        definition = getattr(card, "definition", None)
        payload = {
            "id": getattr(definition, "id", "card"),
            "name_key": getattr(definition, "name_key", "card"),
            "text_key": getattr(definition, "text_key", ""),
            "rarity": getattr(definition, "rarity", "common"),
            "cost": getattr(card, "cost", getattr(definition, "cost", 0)),
            "tags": list(getattr(definition, "tags", []) or []),
            "effects": list(getattr(definition, "effects", []) or []),
            "role": str(getattr(definition, "role", "") or ""),
            "family": str(getattr(definition, "family", "") or ""),
            "author": str(getattr(definition, "author", "") or ""),
            "lore_text": str(getattr(definition, "lore_text", "") or ""),
        }
        return payload, card
    if isinstance(card, dict):
        payload = {
            "id": str(card.get("id", "card")),
            "name_key": str(card.get("name_key", card.get("id", "card"))),
            "text_key": str(card.get("text_key", card.get("effect_text", ""))),
            "rarity": str(card.get("rarity", "common")),
            "cost": int(card.get("cost", 0) or 0),
            "tags": list(card.get("tags", []) or []),
            "effects": list(card.get("effects", []) or []),
            "role": str(card.get("role", "") or ""),
            "family": str(card.get("family", card.get("archetype", "")) or ""),
            "author": str(card.get("author", "") or ""),
            "lore_text": str(card.get("lore_text", card.get("lore", "")) or ""),
            "artwork": str(card.get("artwork", card.get("id", "card")) or card.get("id", "card")),
        }
        return payload, None
    return None, None

def _seed_from_id(card_id: str) -> int:
    return sum((i + 1) * ord(ch) for i, ch in enumerate(str(card_id or "card"))) % 1000003


def _card_tier(payload: dict) -> str:
    tags = set(payload.get("tags", []) or [])
    rarity = str(payload.get("rarity", "common")).lower()
    if "ritual" in tags:
        return "ritual"
    if rarity in {"legendary", "epic"}:
        return "legendary"
    if rarity in {"rare", "uncommon"}:
        return "rare"
    return "normal"


def _font(app, fallback_name: str):
    if app is None:
        return None
    return getattr(app, fallback_name, None)


def _safe_theme(theme: dict | None) -> dict:
    out = dict(UI_THEME)
    if isinstance(theme, dict):
        out.update(theme)
    return out


def _accent(theme: dict, state: dict | None) -> tuple[int, int, int]:
    family = str((state or {}).get("family", "violet_arcane"))
    return {
        "crimson_chaos": (220, 108, 84),
        "emerald_spirit": (88, 198, 154),
        "azure_cosmic": (112, 152, 228),
        "violet_arcane": (176, 126, 240),
        "solar_gold": (226, 190, 112),
    }.get(family, theme.get("accent_violet", (176, 126, 240)))


def _fallback_card_art(app, size: tuple[int, int], tier: str, accent: tuple[int, int, int]) -> pygame.Surface:
    w, h = max(24, int(size[0])), max(24, int(size[1]))
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    base_map = {
        "normal": (90, 78, 60),
        "rare": (86, 66, 124),
        "legendary": (118, 84, 36),
        "ritual": (68, 46, 98),
    }
    base = base_map.get(tier, (82, 60, 96))
    for y in range(h):
        f = y / max(1, h - 1)
        row = (int(base[0] * (0.72 + 0.28 * f)), int(base[1] * (0.72 + 0.28 * f)), int(base[2] * (0.72 + 0.28 * f)))
        pygame.draw.line(surf, row, (0, y), (w, y))
    pygame.draw.rect(surf, accent, surf.get_rect(), 1, border_radius=7)
    font = _font(app, "small_font")
    if font is not None:
        glyph = "*" if tier in {"legendary", "ritual"} else "+"
        txt = font.render(glyph, True, (232, 220, 170))
        surf.blit(txt, txt.get_rect(center=surf.get_rect().center))
    return surf


def _draw_card_background(surface, rect: pygame.Rect, payload: dict, tier: str, accent_color: tuple[int, int, int]):
    rng = random.Random(_seed_from_id(payload.get("id", "card")))
    base_map = {
        "normal": (70, 60, 48),
        "rare": (62, 48, 92),
        "legendary": (96, 66, 30),
        "ritual": (58, 38, 86),
    }
    border_map = {
        "normal": (166, 140, 102),
        "rare": (186, 142, 244),
        "legendary": (248, 212, 118),
        "ritual": (210, 154, 255),
    }
    base = base_map.get(tier, base_map["normal"])
    border = border_map.get(tier, border_map["normal"])
    for y in range(rect.y, rect.bottom):
        f = (y - rect.y) / max(1, rect.h - 1)
        row = (int(base[0] * (0.86 + 0.18 * f)), int(base[1] * (0.86 + 0.18 * f)), int(base[2] * (0.86 + 0.18 * f)))
        pygame.draw.line(surface, row, (rect.x, y), (rect.right, y))

    if tier == "normal":
        for _ in range(max(20, rect.w * rect.h // 900)):
            px = rng.randint(rect.x + 2, rect.right - 3)
            py = rng.randint(rect.y + 2, rect.bottom - 3)
            n = rng.randint(-10, 12)
            col = (max(0, min(255, base[0] + n)), max(0, min(255, base[1] + n)), max(0, min(255, base[2] + n)))
            surface.set_at((px, py), col)
    elif tier == "rare":
        aura = pygame.Surface((rect.w + 24, rect.h + 24), pygame.SRCALPHA)
        pygame.draw.rect(aura, (*accent_color, 88), aura.get_rect(), border_radius=18)
        surface.blit(aura, (rect.x - 12, rect.y - 12))
    elif tier == "legendary":
        glow = pygame.Surface((rect.w + 30, rect.h + 30), pygame.SRCALPHA)
        pygame.draw.rect(glow, (246, 212, 128, 72), glow.get_rect(), border_radius=20)
        surface.blit(glow, (rect.x - 15, rect.y - 15))

    pygame.draw.rect(surface, border, rect, 3, border_radius=12)


def _collect_kpis(summary: dict, payload: dict) -> list[tuple[str, int]]:
    stats = summary.get("stats", {}) if isinstance(summary, dict) else {}
    ordered = [
        ("damage", "damage"),
        ("block", "block"),
        ("energy_delta", "energy"),
        ("harmony_delta", "harmony"),
        ("rupture", "rupture"),
        ("consume_harmony", "seal"),
        ("draw", "draw"),
        ("scry", "scry"),
        ("ritual", "ritual"),
        ("gold", "gold"),
        ("xp", "xp"),
    ]
    out = []
    for key, icon in ordered:
        val = int(stats.get(key, 0) or 0)
        if val <= 0:
            continue
        out.append((icon, val))
    if out:
        return out[:3]

    tags = {str(t).lower() for t in (payload.get("tags", []) or [])}
    role = str(payload.get("role", "") or "").lower()
    semantic = []
    if role == "combo" or "combo" in tags:
        semantic.append(("combo", 1))
    if role == "control" or "control" in tags or "scry" in tags or "draw" in tags:
        semantic.append(("control", 1))
    if role == "defense" or "support" in tags or "heal" in tags or "debuff" in tags:
        semantic.append(("support", 1))
    if role == "ritual" or "ritual" in tags:
        semantic.append(("ritual", 1))
    if not semantic:
        semantic.append(("support", 1))
    return semantic[:3]


def _fit_one_line(font, text: str, max_w: int) -> str:
    out = str(text or "").replace("\n", " ").strip()
    if not out:
        return ""
    while font.size(out)[0] > max_w and len(out) > 4:
        out = out[:-4] + "..."
    return out


def _draw_core(surface, rect, card, theme, state, preset: str):
    theme = _safe_theme(theme)
    state = state or {}
    payload, inst = _payload(card)
    if payload is None:
        pygame.draw.rect(surface, theme["panel"], rect, border_radius=12)
        pygame.draw.rect(surface, theme["accent_violet"], rect, 2, border_radius=12)
        return

    app = state.get("app")
    ctx = state.get("ctx")
    selected = bool(state.get("selected", False))
    hovered = bool(state.get("hovered", False))
    accent_color = _accent(theme, state)
    tier = _card_tier(payload)

    title_font = _font(app, "small_font")
    tiny_font = _font(app, "tiny_font")
    cost_font = _font(app, "big_font")
    if title_font is None or tiny_font is None or cost_font is None:
        return

    _draw_card_background(surface, rect, payload, tier, accent_color)

    art_ratio = 0.50 if preset in {"small", "medium"} else 0.54
    art_frame = pygame.Rect(rect.x + 8, rect.y + 32, rect.w - 16, int(rect.h * art_ratio))
    pygame.draw.rect(surface, (24, 20, 30), art_frame, border_radius=9)
    pygame.draw.rect(surface, accent_color, art_frame, 2, border_radius=9)
    art_inner = art_frame.inflate(-6, -6)
    pygame.draw.rect(surface, (12, 12, 16), art_inner, border_radius=7)

    art = None
    if app is not None:
        try:
            art = app.assets.sprite("cards", payload.get("id", ""), (art_inner.w, art_inner.h), fallback=(70, 44, 105))
        except Exception:
            art = None
    if art is None or art.get_width() < 8 or art.get_height() < 8:
        art = _fallback_card_art(app, (art_inner.w, art_inner.h), tier, accent_color)
    surface.blit(art, art_inner.topleft)

    if tier == "legendary":
        pygame.draw.rect(surface, (250, 226, 156), art_frame.inflate(6, 6), 1, border_radius=11)

    if app is not None:
        card_name = app.loc.t(payload.get("name_key", payload.get("id", "Carta")))
    else:
        card_name = payload.get("id", "Carta")
    title = _fit_one_line(title_font, str(card_name), rect.w - 56)
    title_shadow = title_font.render(title, True, (8, 8, 8))
    title_txt = title_font.render(title, True, (245, 238, 220))
    surface.blit(title_shadow, (rect.x + 10, rect.y + 8))
    surface.blit(title_txt, (rect.x + 9, rect.y + 7))

    base_cost = int(payload.get("cost", 0) or 0)
    live_cost = int(getattr(inst, "cost", base_cost) if inst is not None else base_cost)
    modified = live_cost != base_cost
    reduced = live_cost < base_cost
    cost_col = theme["energy"] if not modified else (120, 220, 255) if reduced else (228, 132, 108)
    center = (rect.right - 24, rect.y + 24)
    pygame.draw.circle(surface, (18, 18, 24), center, 24)
    pygame.draw.circle(surface, cost_col, center, 21)
    pygame.draw.circle(surface, (255, 244, 208), center, 21, 2)
    pygame.draw.circle(surface, (248, 222, 150), center, 24, 1)
    cost_txt = cost_font.render(str(live_cost), True, theme["text_dark"])
    surface.blit(cost_txt, (center[0] - cost_txt.get_width() // 2, center[1] - cost_txt.get_height() // 2))

    if modified:
        trans = f"{base_cost}->{live_cost}"
        tcol = theme["good"] if reduced else theme["bad"]
        surface.blit(tiny_font.render(trans, True, tcol), (rect.x + 10, rect.y + 25))
        if reduced and inst is not None:
            cost_pulse_until = state.get("cost_pulse_until", {})
            pid = str(getattr(inst, "instance_id", ""))
            if cost_pulse_until.get(pid, 0) > pygame.time.get_ticks():
                g = pygame.Surface((rect.w + 12, rect.h + 12), pygame.SRCALPHA)
                pygame.draw.rect(g, (96, 210, 255, 118), g.get_rect(), border_radius=14)
                surface.blit(g, (rect.x - 6, rect.y - 6))

    summary = summarize_card_effect(payload, card_instance=inst, ctx=ctx)
    kpis = _collect_kpis(summary, payload)

    role_key = infer_card_role(payload)
    role_col = ROLE_COLORS.get(role_key, theme.get("accent_violet", (176, 126, 240)))
    role_label = ROLE_LABELS.get(role_key, role_key.upper())
    role_rect = pygame.Rect(rect.x + 10, art_frame.bottom + 6, max(86, min(170, rect.w - 20)), 18)
    pygame.draw.rect(surface, (20, 18, 28), role_rect, border_radius=8)
    pygame.draw.rect(surface, role_col, role_rect, 1, border_radius=8)
    surface.blit(tiny_font.render(role_label, True, role_col), (role_rect.x + 7, role_rect.y + 2))

    model = to_card_framework_model(payload, summary=summary, app=app)
    effect_line = _fit_one_line(tiny_font, model.effect_text or str(summary.get("header") or ""), rect.w - 18)
    lore_line = _fit_one_line(tiny_font, model.lore_text, rect.w - 18)

    if preset == "preview":
        preview_lines = []
        for ln in list(summary.get("lines", []) or []):
            txt = _fit_one_line(tiny_font, str(ln), rect.w - 18)
            if txt:
                preview_lines.append(txt)
            if len(preview_lines) >= 2:
                break
        if not preview_lines and effect_line:
            preview_lines = [effect_line]
        for idx, line in enumerate(preview_lines[:2]):
            surface.blit(tiny_font.render(line, True, (236, 228, 206)), (rect.x + 9, role_rect.bottom + 4 + idx * 16))
        if lore_line:
            surface.blit(tiny_font.render(lore_line, True, theme.get("muted", (180, 170, 200))), (rect.x + 9, role_rect.bottom + 36))
    elif effect_line:
        surface.blit(tiny_font.render(effect_line, True, (236, 228, 206)), (rect.x + 9, role_rect.bottom + 6))

    kpi_band = pygame.Rect(rect.x + 6, rect.bottom - 38, rect.w - 12, 30)
    pygame.draw.rect(surface, (12, 12, 18), kpi_band, border_radius=8)
    pygame.draw.rect(surface, (156, 136, 204), kpi_band, 1, border_radius=8)
    x = kpi_band.x + 8
    for icon_name, val in kpis:
        x = draw_icon_with_value(surface, icon_name, val, (255, 246, 196), tiny_font, x, kpi_band.y + 6, size=2 if preset != "small" else 1)
        if x > kpi_band.right - 30:
            break

    if hovered:
        hover_glow = pygame.Surface((rect.w + 14, rect.h + 14), pygame.SRCALPHA)
        pygame.draw.rect(hover_glow, (232, 198, 255, 86), hover_glow.get_rect(), border_radius=18)
        surface.blit(hover_glow, (rect.x - 7, rect.y - 7))
    if selected:
        pygame.draw.rect(surface, theme["gold"], rect.inflate(8, 8), 3, border_radius=14)


def render_card_small(surface, rect, card, theme=None, state=None):
    _draw_core(surface, pygame.Rect(rect), card, theme, state, preset="small")


def render_card_medium(surface, rect, card, theme=None, state=None):
    _draw_core(surface, pygame.Rect(rect), card, theme, state, preset="medium")


def render_card_large(surface, rect, card, theme=None, state=None):
    _draw_core(surface, pygame.Rect(rect), card, theme, state, preset="large")


def render_card_preview(surface, rect, card, theme=None, state=None):
    _draw_core(surface, pygame.Rect(rect), card, theme, state, preset="preview")


