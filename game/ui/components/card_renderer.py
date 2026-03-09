from __future__ import annotations

import random

import pygame

from game.ui.components.card_effect_summary import infer_card_role, summarize_card_effect
from game.ui.components.card_framework import to_card_framework_model
from game.ui.system.icons import draw_icon_with_value
from game.ui.theme import UI_THEME
from game.ui.system.safety import clamp_single_line, wrap_lines, resolve_view_context


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
    "energy": "CANALIZACION",
    "control": "CONTROL",
    "ritual": "RITUAL",
    "combo": "COMBO",
}

RENDER_CONTEXT_RULES = {
    "hand_view": {"pad": 9, "text_pad": 6, "title_scale": 0.94, "effect_scale": 0.92, "lore_mode": "brief", "footer_mode": "compact", "art_fit_mode": "contain"},
    "hover_view": {"pad": 12, "text_pad": 8, "title_scale": 1.0, "effect_scale": 0.96, "lore_mode": "full", "footer_mode": "full", "art_fit_mode": "contain"},
    "combat_preview": {"pad": 11, "text_pad": 7, "title_scale": 0.98, "effect_scale": 0.95, "lore_mode": "normal", "footer_mode": "compact", "art_fit_mode": "contain"},
    "deck_view": {"pad": 10, "text_pad": 7, "title_scale": 0.94, "effect_scale": 0.92, "lore_mode": "brief", "footer_mode": "compact", "art_fit_mode": "contain"},
    "deck_builder": {"pad": 10, "text_pad": 7, "title_scale": 0.94, "effect_scale": 0.92, "lore_mode": "brief", "footer_mode": "compact", "art_fit_mode": "contain"},
    "codex_view": {"pad": 12, "text_pad": 8, "title_scale": 1.0, "effect_scale": 0.98, "lore_mode": "full", "footer_mode": "full", "art_fit_mode": "contain"},
    "shop_view": {"pad": 10, "text_pad": 7, "title_scale": 0.95, "effect_scale": 0.93, "lore_mode": "normal", "footer_mode": "compact", "art_fit_mode": "contain"},
    "pack_view": {"pad": 10, "text_pad": 7, "title_scale": 0.95, "effect_scale": 0.93, "lore_mode": "normal", "footer_mode": "compact", "art_fit_mode": "contain"},
    "archetype_preview": {"pad": 11, "text_pad": 7, "title_scale": 0.94, "effect_scale": 0.9, "lore_mode": "brief", "footer_mode": "set_only", "art_fit_mode": "contain"},
}

def _payload(card):
    if card is None:
        return None, None
    if hasattr(card, "definition"):
        definition = getattr(card, "definition", None)
        metadata = dict(getattr(definition, "metadata", {}) or {})
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
            "author": str(getattr(definition, "author", metadata.get("author", "")) or ""),
            "order": str(getattr(definition, "order", metadata.get("order", "")) or ""),
            "lore_text": str(getattr(definition, "lore_text", "") or ""),
            "set": str(metadata.get("set", (metadata.get("strategy", {}) or {}).get("set", "")) or ""),
            "artwork": str(metadata.get("artwork", getattr(definition, "id", "card")) or getattr(definition, "id", "card")),
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
            "order": str(card.get("order", (card.get("metadata", {}) or {}).get("order", "")) or ""),
            "lore_text": str(card.get("lore_text", card.get("lore", "")) or ""),
            "set": str(card.get("set", ((card.get("strategy", {}) or {}).get("set", ""))) or ""),
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


def _is_hiperboria(payload: dict) -> bool:
    set_name = str(payload.get("set", "") or "").strip().lower()
    cid = str(payload.get("id", "") or "").strip().lower()
    return "hiperboria" in set_name or cid.startswith("hip_")


def _draw_hiperborea_emblem(surface: pygame.Surface, art_rect: pygame.Rect):
    # Chakana Polar: small snow-cross emblem at art bottom-right.
    cx = art_rect.right - 14
    cy = art_rect.bottom - 14
    col = (226, 206, 140)
    ice = (180, 224, 248)
    pygame.draw.circle(surface, (26, 34, 52), (cx, cy), 11)
    pygame.draw.circle(surface, ice, (cx, cy), 10, 1)
    pygame.draw.circle(surface, col, (cx, cy), 8, 1)
    pygame.draw.line(surface, col, (cx - 6, cy), (cx + 6, cy), 1)
    pygame.draw.line(surface, col, (cx, cy - 6), (cx, cy + 6), 1)
    pygame.draw.line(surface, ice, (cx - 4, cy - 4), (cx + 4, cy + 4), 1)
    pygame.draw.line(surface, ice, (cx + 4, cy - 4), (cx - 4, cy + 4), 1)


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


def _draw_card_background(surface, rect: pygame.Rect, payload: dict, tier: str, accent_color: tuple[int, int, int], is_hip: bool = False):
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

    if is_hip:
        base_map = {
            "normal": (220, 230, 238),
            "rare": (198, 218, 236),
            "legendary": (232, 220, 184),
            "ritual": (202, 220, 238),
        }
        border_map = {
            "normal": (148, 184, 220),
            "rare": (132, 172, 214),
            "legendary": (196, 164, 90),
            "ritual": (164, 188, 220),
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
    if is_hip:
        pygame.draw.rect(surface, (186, 214, 236), rect.inflate(10, 10), 1, border_radius=15)


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
        return out[:4]

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
    if role == "energy" or "energy" in tags:
        semantic.append(("energy", 1))
    if not semantic:
        semantic.append(("support", 1))
    return semantic[:4]


def _fit_one_line(font, text: str, max_w: int) -> str:
    return clamp_single_line(font, text, max_w)


def _fit_lines(font, text: str, max_w: int, max_lines: int) -> list[str]:
    return wrap_lines(font, text, max_w, max_lines)


def _resolve_render_context(state: dict | None, preset: str) -> dict:
    default_by_preset = {
        "small": "hand_view",
        "medium": "combat_preview",
        "large": "hover_view",
        "preview": "codex_view",
    }
    key = str((state or {}).get("render_context", default_by_preset.get(preset, "combat_preview")) or "").strip().lower()
    safety = resolve_view_context(key)
    merged = dict(RENDER_CONTEXT_RULES.get(key, RENDER_CONTEXT_RULES["combat_preview"]))
    if "font_scale" in safety:
        merged.setdefault("font_scale", safety["font_scale"])
    return merged


def _layout_for(rect: pygame.Rect, preset: str, rules: dict) -> dict:
    cfg = {
        "small": {"pad": 10, "text_pad": 6},
        "medium": {"pad": 10, "text_pad": 7},
        "large": {"pad": 11, "text_pad": 8},
        "preview": {"pad": 12, "text_pad": 9},
    }.get(preset, {"pad": 10, "text_pad": 7})

    cfg["pad"] = int(max(7, rules.get("pad", cfg["pad"])))
    cfg["text_pad"] = int(max(4, rules.get("text_pad", cfg["text_pad"])))

    content = rect.inflate(-cfg["pad"] * 2, -cfg["pad"] * 2)
    gap = cfg["text_pad"]

    ratio_header = 0.10
    ratio_art = 0.55
    ratio_type = 0.06
    ratio_effects = 0.12
    ratio_lore = 0.08
    ratio_footer = 0.09

    h = content.h
    header_h = max(34, int(h * ratio_header))
    art_h = max(86, int(h * ratio_art))
    type_h = max(16, int(h * ratio_type))
    effects_h = max(42, int(h * ratio_effects))
    lore_h = max(16, int(h * ratio_lore))
    footer_h = max(30, int(h * ratio_footer))

    used = header_h + art_h + type_h + effects_h + lore_h + footer_h + gap * 5
    if used > h:
        overflow = used - h
        cut_effects = min(overflow, max(0, effects_h - 30))
        effects_h -= cut_effects
        overflow -= cut_effects
        if overflow > 0:
            cut_lore = min(overflow, max(0, lore_h - 18))
            lore_h -= cut_lore
            overflow -= cut_lore
        if overflow > 0:
            art_h = max(72, art_h - overflow)

    y = content.y
    header = pygame.Rect(content.x, y, content.w, header_h)
    y = header.bottom + gap
    art = pygame.Rect(content.x, y, content.w, art_h)
    y = art.bottom + gap

    type_bar = pygame.Rect(content.x, y, content.w, type_h)
    y = type_bar.bottom + gap

    effects = pygame.Rect(content.x, y, content.w, effects_h)
    y = effects.bottom + gap
    lore = pygame.Rect(content.x, y, content.w, lore_h)
    y = lore.bottom + gap

    footer = pygame.Rect(content.x, y, content.w, footer_h)

    type_label = pygame.Rect(type_bar.x + 8, type_bar.y + 2, max(86, int(type_bar.w * 0.62)), max(14, type_bar.h - 4))
    emblem = pygame.Rect(type_bar.right - 112, type_bar.y + 1, 106, max(14, type_bar.h - 2))
    author = pygame.Rect(footer.x + 8, footer.y + 2, max(92, int(footer.w * 0.52)), max(18, footer.h - 4))
    stats = pygame.Rect(author.right + 4, footer.y + 1, max(92, footer.right - (author.right + 10)), max(18, footer.h - 2))

    return {
        "cfg": cfg,
        "content": content,
        "header": header,
        "art": art,
        "type_bar": type_bar,
        "type_label": type_label,
        "effects": effects,
        "lore": lore,
        "footer": footer,
        "author": author,
        "emblem": emblem,
        "stats": stats,
    }

def _type_label(role_key: str, payload: dict, tier: str) -> str:
    tags = {str(t).lower() for t in (payload.get("tags", []) or [])}
    if tier == "legendary":
        return "LEGENDARIA"
    if role_key == "energy" or "energy" in tags:
        return "CANALIZACION"
    return ROLE_LABELS.get(role_key, role_key.upper())


def _effect_lines(summary: dict, model, max_lines: int) -> list[str]:
    raw = list(summary.get("lines", []) or []) if isinstance(summary, dict) else []
    if not raw:
        txt = str(model.effect_text or summary.get("header") or "")
        raw = [x.strip() for x in txt.replace(";", ",").split(",") if str(x).strip()]
    return [str(x).strip() for x in raw if str(x).strip()][:max_lines]


def _density_for(effects_count: int) -> str:
    if effects_count <= 2:
        return "normal"
    if effects_count == 3:
        return "compact"
    return "dense"


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
    is_hip = _is_hiperboria(payload)

    title_font = _font(app, "small_font")
    tiny_font = _font(app, "tiny_font")
    cost_font = _font(app, "big_font")
    if title_font is None or tiny_font is None or cost_font is None:
        return

    _draw_card_background(surface, rect, payload, tier, accent_color, is_hip=is_hip)
    rules = _resolve_render_context(state, preset)
    sec = _layout_for(rect, preset, rules)

    # Definitive zones: header / art / type / text+lore / stats
    for r in (sec["header"], sec["art"], sec["effects"], sec["lore"], sec["footer"]):
        pygame.draw.rect(surface, (12, 11, 18, 62), r, border_radius=8)

    art_frame = sec["art"]
    pygame.draw.rect(surface, (24, 20, 30), art_frame, border_radius=9)
    pygame.draw.rect(surface, accent_color, art_frame, 2, border_radius=9)
    art_inner = art_frame.inflate(-8, -8)
    pygame.draw.rect(surface, (12, 12, 16), art_inner, border_radius=7)

    art = None
    if app is not None:
        try:
            art = app.assets.sprite("cards", payload.get("artwork", payload.get("id", "")), (art_inner.w, art_inner.h), fallback=(70, 44, 105))
        except Exception:
            art = None
    if art is None or art.get_width() < 8 or art.get_height() < 8:
        art = _fallback_card_art(app, (art_inner.w, art_inner.h), tier, accent_color)
    surface.blit(art, art_inner.topleft)
    if is_hip:
        _draw_hiperborea_emblem(surface, art_inner)

    if tier == "legendary":
        pygame.draw.rect(surface, (250, 226, 156), art_frame.inflate(6, 6), 1, border_radius=11)

    if app is not None:
        card_name = app.loc.t(payload.get("name_key", payload.get("id", "Carta")))
    else:
        card_name = payload.get("id", "Carta")

    title_bar = pygame.Rect(sec["header"].x + 6, sec["header"].y + 3, max(72, sec["header"].w - 54), sec["header"].h - 6)
    pygame.draw.rect(surface, (20, 18, 28), title_bar, border_radius=9)
    pygame.draw.rect(surface, accent_color, title_bar, 1, border_radius=9)

    title = _fit_one_line(title_font, str(card_name), title_bar.w - 20)
    # Auto-shrink title in dense cards to avoid overflow/collision with cost orb.
    title_renderer = title_font
    if (preset in {"small", "medium"} or rules.get("title_scale", 1.0) < 1.0) and len(title) > 18 and app is not None:
        title_renderer = tiny_font
    title_shadow = title_renderer.render(title, True, (8, 8, 8))
    title_txt = title_renderer.render(title, True, (245, 238, 220))
    tx = title_bar.x + 10
    ty = title_bar.y + max(1, (title_bar.h - title_txt.get_height()) // 2)
    surface.blit(title_shadow, (tx + 1, ty + 1))
    surface.blit(title_txt, (tx, ty))

    base_cost = int(payload.get("cost", 0) or 0)
    live_cost = int(getattr(inst, "cost", base_cost) if inst is not None else base_cost)
    modified = live_cost != base_cost
    reduced = live_cost < base_cost
    cost_col = theme["energy"] if not modified else (120, 220, 255) if reduced else (228, 132, 108)
    center = (sec["header"].right - 22, sec["header"].y + sec["header"].h // 2)
    pygame.draw.circle(surface, (18, 18, 24), center, 24)
    pygame.draw.circle(surface, cost_col, center, 21)
    pygame.draw.circle(surface, (255, 244, 208), center, 21, 2)
    pygame.draw.circle(surface, (248, 222, 150), center, 24, 1)
    cost_txt = cost_font.render(str(live_cost), True, theme["text_dark"])
    surface.blit(cost_txt, (center[0] - cost_txt.get_width() // 2, center[1] - cost_txt.get_height() // 2))

    if modified:
        trans = f"{base_cost}->{live_cost}"
        tcol = theme["good"] if reduced else theme["bad"]
        surface.blit(tiny_font.render(trans, True, tcol), (sec["header"].x + 10, sec["header"].y + 28))

    summary = summarize_card_effect(payload, card_instance=inst, ctx=ctx)
    model = to_card_framework_model(payload, summary=summary, app=app)

    role_key = infer_card_role(payload)
    role_col = ROLE_COLORS.get(role_key, theme.get("accent_violet", (176, 126, 240)))
    type_label = _type_label(role_key, payload, tier)
    pygame.draw.rect(surface, (20, 18, 28), sec["type_bar"], border_radius=8)
    pygame.draw.rect(surface, role_col, sec["type_bar"], 1, border_radius=8)
    type_txt = _fit_one_line(tiny_font, type_label, sec["type_label"].w - 8)
    type_lbl = tiny_font.render(type_txt, True, role_col)
    type_y = sec["type_label"].y + max(1, (sec["type_label"].h - type_lbl.get_height()) // 2)
    surface.blit(type_lbl, (sec["type_label"].x + 2, type_y))

    set_text = "HIPERBOREA" if is_hip else "BASE"
    set_col = (226, 206, 140) if is_hip else (170, 156, 196)
    set_lbl = _fit_one_line(tiny_font, set_text, sec["emblem"].w - 6)
    set_surf = tiny_font.render(set_lbl, True, set_col)
    set_y = sec["emblem"].y + max(1, (sec["emblem"].h - set_surf.get_height()) // 2)
    surface.blit(set_surf, (sec["emblem"].x + max(3, (sec["emblem"].w - set_surf.get_width()) // 2), set_y))

    effect_items = _collect_kpis(summary, payload) or [("support", 1)]
    density = _density_for(len(effect_items))
    row_h = 18 if density == "normal" else 16 if density == "compact" else 14
    if rules.get("effect_scale", 1.0) < 0.95:
        row_h = max(12, row_h - 1)

    ex = sec["effects"].x + 8
    ey = sec["effects"].y + max(2, (sec["effects"].h - (row_h * 2 + 2)) // 2)
    second_row_used = False
    for icon_name, val in effect_items:
        token = f"{icon_name}:{val}"
        tw = max(62, tiny_font.size(token)[0] + 34)
        if ex + tw > sec["effects"].right - 8 and not second_row_used:
            ex = sec["effects"].x + 8
            ey += row_h + 2
            second_row_used = True
        if ex + tw > sec["effects"].right - 8:
            break
        token_rect = pygame.Rect(ex, ey, tw, row_h)
        pygame.draw.rect(surface, (20, 18, 30), token_rect, border_radius=6)
        pygame.draw.rect(surface, (120, 110, 162), token_rect, 1, border_radius=6)
        draw_icon_with_value(
            surface,
            icon_name,
            val,
            (255, 246, 196),
            tiny_font,
            token_rect.x + 4,
            token_rect.y + max(1, (token_rect.h - 18) // 2),
            size=1,
            min_icon_px=18,
        )
        ex = token_rect.right + 6

    # Lore is always present and italic with a subtle alpha in non-hover contexts.
    lore_max_lines = 2
    if preset in {"preview", "large"}:
        lore_max_lines = 3
    if rules.get("lore_mode") == "brief":
        lore_max_lines = 1
    if rules.get("lore_mode") == "full":
        lore_max_lines = max(2, lore_max_lines)

    lore_lines = _fit_lines(tiny_font, model.lore_text, sec["lore"].w - 10, lore_max_lines)
    lore_alpha = 255 if hovered or preset in {"preview", "large"} else int(255 * 0.85)
    ly = sec["lore"].y + max(0, (sec["lore"].h - max(1, len(lore_lines)) * 12) // 2)
    italic_prev = False
    if hasattr(tiny_font, "get_italic"):
        italic_prev = bool(tiny_font.get_italic())
    if hasattr(tiny_font, "set_italic"):
        tiny_font.set_italic(True)
    for line in lore_lines:
        lbl = tiny_font.render(line, True, (198, 176, 224))
        lbl.set_alpha(lore_alpha)
        lx = sec["lore"].x + max(4, (sec["lore"].w - lbl.get_width()) // 2)
        surface.blit(lbl, (lx, ly))
        ly += 12
    if hasattr(tiny_font, "set_italic"):
        tiny_font.set_italic(italic_prev)

    footer_mode = str(rules.get("footer_mode", "compact"))
    border_meta = _fit_one_line(
        tiny_font,
        f"Autor: {model.author or 'Chakana Studio'} | Orden: {model.order or 'Chakana'}",
        sec["author"].w - 6,
    )
    if footer_mode != "set_only" and border_meta:
        meta = tiny_font.render(border_meta, True, (142, 124, 176))
        meta.set_alpha(int(255 * 0.55))
        mx = sec["author"].x + max(2, (sec["author"].w - meta.get_width()) // 2)
        my = sec["author"].y + max(1, (sec["author"].h - meta.get_height()) // 2)
        surface.blit(meta, (mx, my))

    stat_rect = sec["stats"]
    pygame.draw.rect(surface, (16, 14, 24), stat_rect, border_radius=7)
    pygame.draw.rect(surface, (132, 118, 164), stat_rect, 1, border_radius=7)
    sx = stat_rect.x + 5
    sy = stat_rect.y + max(1, (stat_rect.h - 16) // 2)
    for icon_name, val in effect_items[:3]:
        sx = draw_icon_with_value(
            surface,
            icon_name,
            val,
            (236, 226, 194),
            tiny_font,
            sx,
            sy,
            size=1,
            min_icon_px=16,
        )
        if sx > stat_rect.right - 28:
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




















