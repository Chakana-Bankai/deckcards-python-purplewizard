"""Global UI safety rules for spacing and text bounds control."""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class UISafeDefaults:
    outer_margin: int = 12
    inner_padding: int = 10
    section_gap: int = 6
    text_safe_padding: int = 8


SAFE_DEFAULTS = UISafeDefaults()


VIEW_CONTEXT_RULES: dict[str, dict] = {
    "hand_view": {"font_scale": 0.92, "max_lines": 2, "padding": "compact", "compact_threshold": 3},
    "hover_view": {"font_scale": 1.0, "max_lines": 5, "padding": "comfortable", "compact_threshold": 5},
    "combat_preview": {"font_scale": 0.95, "max_lines": 4, "padding": "normal", "compact_threshold": 4},
    "deck_view": {"font_scale": 0.92, "max_lines": 3, "padding": "normal", "compact_threshold": 4},
    "codex_view": {"font_scale": 1.0, "max_lines": 6, "padding": "comfortable", "compact_threshold": 6},
    "shop_view": {"font_scale": 0.93, "max_lines": 3, "padding": "normal", "compact_threshold": 4},
    "pack_view": {"font_scale": 0.93, "max_lines": 3, "padding": "normal", "compact_threshold": 4},
    "archetype_preview": {"font_scale": 0.9, "max_lines": 3, "padding": "compact", "compact_threshold": 3},
    "dialogue_view": {"font_scale": 0.95, "max_lines": 3, "padding": "normal", "compact_threshold": 3},
    "map_panel_view": {"font_scale": 0.93, "max_lines": 2, "padding": "compact", "compact_threshold": 2},
}


def resolve_view_context(name: str) -> dict:
    key = str(name or "").strip().lower()
    return dict(VIEW_CONTEXT_RULES.get(key, VIEW_CONTEXT_RULES["combat_preview"]))


def safe_inset(rect: pygame.Rect, outer: int | None = None) -> pygame.Rect:
    pad = SAFE_DEFAULTS.outer_margin if outer is None else max(0, int(outer))
    return rect.inflate(-pad * 2, -pad * 2)


def clamp_single_line(font: pygame.font.Font, text: str, max_w: int) -> str:
    out = str(text or "").replace("\n", " ").strip()
    if not out:
        return ""
    while font.size(out)[0] > max_w and len(out) > 4:
        out = out[:-4] + "..."
    return out


def wrap_lines(font: pygame.font.Font, text: str, max_w: int, max_lines: int) -> list[str]:
    src = str(text or "").replace("\n", " ").strip()
    if not src:
        return []
    words = src.split()
    lines = []
    cur = ""
    for w in words:
        cand = (cur + " " + w).strip()
        if font.size(cand)[0] <= max_w:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        cur = w
        if len(lines) >= max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if lines and len(words) > len(" ".join(lines).split()):
        last = lines[-1]
        while font.size(last + "...")[0] > max_w and len(last) > 2:
            last = last[:-1]
        lines[-1] = last.rstrip(".") + "..."
    return lines[:max_lines]
