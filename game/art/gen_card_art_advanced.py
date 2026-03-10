from __future__ import annotations

import random
from pathlib import Path

import pygame

from game.art import gen_card_art32
from game.art.scene_engine import generate_scene_art

# Keep version aligned with active generator while exposing an advanced entrypoint.
GEN_CARD_ART_ADVANCED_VERSION = f"advanced_v4_narrative::{gen_card_art32.GEN_CARD_ART_VERSION}"


def _mode_for(card_type: str, prompt: str) -> str:
    p = str(prompt or "").lower()
    c = str(card_type or "").lower()
    if "legendary" in p or c == "legendary":
        return "premium_legendary"
    if "abstract" in p:
        return "procedural_abstract"
    if "illustration" in p or "illustrated" in p or "portrait" in p:
        return "illustrative_hybrid"
    if "motif" in p or "symbolic" in p or "sacred geometry" in p:
        return "procedural_motif"
    return "illustrative_hybrid"


def _set_style(prompt: str) -> str:
    low = str(prompt or "").lower()
    if "hiperboria" in low or "hiperborea" in low or "hip_" in low:
        return "hiperborea"
    if "archon" in low or "arconte" in low or "void" in low or "demon" in low:
        return "archon"
    return "base"


def _style_tokens(style: str) -> str:
    if style == "hiperborea":
        return (
            " set identity hiperborea: ancient advanced civilization, atlantean polar temples, crystal technology, "
            "marble white + ice blue + ancient gold palette."
        )
    if style == "archon":
        return (
            " set identity archon: dark entities, void corruption, gnostic horror, oppressive silhouettes, "
            "dark purple + crimson + black palette."
        )
    return (
        " set identity base: mystic geometry, chakana motifs, ceremonial runes, gold + violet palette."
    )


def _enrich_prompt(prompt: str, mode: str) -> str:
    p = str(prompt or "").strip()
    style = _set_style(p)

    if mode == "premium_legendary":
        tier = " premium legendary treatment, expanded motif detail, illustrated focal subject, richer glow layering, ceremonial silhouette priority."
    elif mode == "procedural_motif":
        tier = " motif-forward treatment, clear central symbol, reduced random repetition, narrative composition."
    elif mode == "illustrative_hybrid":
        tier = " illustrated fantasy card art treatment, painterly brush texture, cinematic lighting, strong character/motif readability."
    else:
        tier = " abstract procedural treatment with controlled geometry noise and clear value hierarchy."

    composition = (
        " narrative composition rules: subject 40-50 percent frame, environment 25-35 percent, focus object 10-15 percent, energy action 8-15 percent. "
        "Always show subject + visible action + readable environment context. "
        "Every artwork must include one clear background, one clear subject, one readable object or relic focus, and one coherent set of energy/effect traces. "
        "Keep sacred geometry mostly in frame borders, corners or distant architecture, never as a thin overlay hiding the focal subject. "
        "Preserve open air around the focal subject and separate planes clearly like layered 2d/2.5d card art."
    )

    return (p + tier + _style_tokens(style) + composition + " keep pixel clarity full hd no blur no stretch.").strip()


def _palette_for_style(style: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    if style == "hiperborea":
        return (244, 246, 255), (126, 206, 255), (212, 176, 96)
    if style == "archon":
        return (58, 38, 84), (198, 54, 92), (36, 26, 48)
    return (112, 74, 168), (214, 182, 96), (42, 28, 64)


def _narrative_pass(out_path: Path, seed: int, mode: str, prompt: str) -> dict:
    try:
        surf = pygame.image.load(str(out_path)).convert_alpha()
    except Exception:
        return {"ok": False}

    base_w, base_h = surf.get_size()
    work_scale = 2
    if base_w < 480 or base_h < 320:
        surf = pygame.transform.smoothscale(surf, (base_w * work_scale, base_h * work_scale))
    w, h = surf.get_size()
    rng = random.Random(seed + 404)
    style = _set_style(prompt)
    p_main, p_accent, p_deep = _palette_for_style(style)

    # Environment depth (20-30%): atmospheric gradient and distant structures.
    env = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        t = y / max(1, h - 1)
        a = int(30 + 28 * (1.0 - t))
        col = (
            int(p_deep[0] * (0.8 + 0.2 * (1 - t))),
            int(p_deep[1] * (0.8 + 0.2 * (1 - t))),
            int(p_deep[2] * (0.8 + 0.2 * (1 - t))),
            a,
        )
        pygame.draw.line(env, col, (0, y), (w, y), 1)

    skyline_h = int(h * 0.24)
    for i in range(8):
        bw = rng.randint(max(8, w // 22), max(14, w // 11))
        bh = rng.randint(max(10, skyline_h // 3), skyline_h)
        bx = rng.randint(0, max(0, w - bw - 1))
        by = h - bh - rng.randint(0, max(2, h // 16))
        pygame.draw.rect(env, (*p_deep, 44), pygame.Rect(bx, by, bw, bh), border_radius=2)
    if style == "hiperborea":
        for i in range(4):
            tw = max(20, w // 7)
            th = max(18, h // 5)
            bx = int(w * (0.10 + i * 0.2))
            by = int(h * 0.50) - (i % 2) * 12
            pygame.draw.rect(env, (*p_main, 34), pygame.Rect(bx, by, tw, th), border_radius=4)
            pygame.draw.rect(env, (*p_accent, 46), pygame.Rect(bx + tw // 4, by - 18, tw // 2, 18), border_radius=3)
        for i in range(6):
            ay = int(h * (0.10 + i * 0.05))
            pygame.draw.arc(env, (*p_accent, 40), pygame.Rect(-20, ay, w + 40, max(32, h // 5)), 0.2, 2.9, 1)

    surf.blit(env, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # Subject focus mask (50-60%): brighten center subject and soften outside.
    subject_ratio = 0.56
    subject_w = int(w * subject_ratio)
    subject_h = int(h * subject_ratio)
    subject_rect = pygame.Rect((w - subject_w) // 2, int(h * 0.16), subject_w, subject_h)

    focus = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(focus, (*p_main, 28), subject_rect)
    if style == "hiperborea":
        pygame.draw.ellipse(focus, (*p_accent, 24), subject_rect.inflate(-subject_rect.w // 5, -subject_rect.h // 6))
    surf.blit(focus, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    vignette = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(3):
        pygame.draw.rect(vignette, (0, 0, 0, 16 + i * 7), pygame.Rect(i * 2, i * 2, w - i * 4, h - i * 4), 2, border_radius=10)
    surf.blit(vignette, (0, 0))

    # Action/energy (10-20%): arcs, sparks, and directional energy.
    fx = pygame.Surface((w, h), pygame.SRCALPHA)
    fx_count = 14 if mode == "premium_legendary" else 10
    for _ in range(fx_count):
        cx = rng.randint(int(w * 0.22), int(w * 0.78))
        cy = rng.randint(int(h * 0.18), int(h * 0.76))
        rw = rng.randint(max(12, w // 12), max(18, w // 7))
        rh = rng.randint(max(10, h // 14), max(18, h // 8))
        start = rng.randint(0, 360)
        end = start + rng.randint(40, 140)
        pygame.draw.arc(fx, (*p_accent, 72), pygame.Rect(cx - rw // 2, cy - rh // 2, rw, rh), start * 3.14159 / 180.0, end * 3.14159 / 180.0, 1)
    spark_n = 24 if mode == "premium_legendary" else 16
    for _ in range(spark_n):
        sx = rng.randint(int(w * 0.2), int(w * 0.8))
        sy = rng.randint(int(h * 0.16), int(h * 0.82))
        pygame.draw.circle(fx, (*p_accent, rng.randint(44, 88)), (sx, sy), rng.randint(1, 2))

    surf.blit(fx, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # Painterly micro texture, reduced geometry noise dominance.
    tex = pygame.Surface((w, h), pygame.SRCALPHA)
    strokes = 96 if mode == "premium_legendary" else 72
    for _ in range(strokes):
        x = rng.randint(0, max(0, w - 1))
        y = rng.randint(0, max(0, h - 1))
        ln = rng.randint(3, 9)
        col = (rng.randint(20, 44), rng.randint(16, 40), rng.randint(24, 52), rng.randint(5, 14))
        pygame.draw.line(tex, col, (x, y), (min(w - 1, x + ln), min(h - 1, y + rng.randint(-1, 1))), 1)
    surf.blit(tex, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

    if mode == "premium_legendary":
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*p_accent, 38), (w // 10, h // 7, w * 4 // 5, h * 2 // 3))
        surf.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    try:
        if (w, h) != (base_w, base_h):
            surf = pygame.transform.smoothscale(surf, (base_w, base_h)).convert_alpha()
        pygame.image.save(surf, str(out_path))
    except Exception:
        return {"ok": False}

    return {
        "ok": True,
        "style": style,
        "subject_ratio": subject_ratio,
        "work_resolution": f"{w}x{h}",
        "output_resolution": f"{base_w}x{base_h}",
        "environment_ratio_range": "0.20-0.30",
        "energy_ratio_range": "0.10-0.20",
    }


def generate(card_id: str, card_type: str, prompt: str, seed: int, out_path: Path) -> dict:
    """Advanced layered card art generation with safe fallback to current generator."""
    mode = _mode_for(card_type, prompt)
    enriched_prompt = _enrich_prompt(prompt, mode)
    seed_bump = {
        "procedural_motif": 71,
        "premium_legendary": 173,
        "illustrative_hybrid": 233,
    }.get(mode, 0)

    try:
        result = generate_scene_art(card_id, enriched_prompt, seed + seed_bump, out_path)
        comp = _narrative_pass(out_path, seed + seed_bump, mode, enriched_prompt)
        if isinstance(result, dict):
            result = dict(result)
            result.setdefault("generator_used", GEN_CARD_ART_ADVANCED_VERSION)
            result.setdefault("treatment_mode", mode)
            result.setdefault("prompt_enriched", True)
            result.setdefault("illustrative_finish", True)
            result.setdefault("narrative_composition", comp.get("ok", False))
            result.setdefault("set_style", comp.get("style", _set_style(enriched_prompt)))
            return result
        return {
            "card_id": card_id,
            "path": str(out_path),
            "generator_used": GEN_CARD_ART_ADVANCED_VERSION,
            "treatment_mode": mode,
            "prompt_enriched": True,
            "illustrative_finish": True,
            "narrative_composition": comp.get("ok", False),
            "set_style": comp.get("style", _set_style(enriched_prompt)),
        }
    except Exception:
        fallback = gen_card_art32.generate(card_id, card_type, prompt, seed + 137, out_path)
        comp = _narrative_pass(out_path, seed + 137, mode, prompt)
        if isinstance(fallback, dict):
            fallback = dict(fallback)
            fallback.setdefault("generator_used", f"fallback::{GEN_CARD_ART_ADVANCED_VERSION}")
            fallback.setdefault("treatment_mode", mode)
            fallback.setdefault("prompt_enriched", False)
            fallback.setdefault("illustrative_finish", True)
            fallback.setdefault("narrative_composition", comp.get("ok", False))
            fallback.setdefault("set_style", comp.get("style", _set_style(prompt)))
        return fallback
