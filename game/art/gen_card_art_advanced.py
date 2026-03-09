from __future__ import annotations

from pathlib import Path

from game.art import gen_card_art32

# Keep version aligned with active generator while exposing an advanced entrypoint.
GEN_CARD_ART_ADVANCED_VERSION = f"advanced_v2::{gen_card_art32.GEN_CARD_ART_VERSION}"


def _mode_for(card_type: str, prompt: str) -> str:
    p = str(prompt or "").lower()
    c = str(card_type or "").lower()
    if "legendary" in p or c == "legendary":
        return "premium_legendary"
    if "motif" in p or "symbolic" in p or "sacred geometry" in p:
        return "procedural_motif"
    return "procedural_abstract"


def _enrich_prompt(prompt: str, mode: str) -> str:
    p = str(prompt or "").strip()
    low = p.lower()

    set_tokens = ""
    if "hiperboria" in low or "hiperborea" in low or "hip_" in low:
        set_tokens = " set identity: hiperborea, palette marble white + ice blue + ancient gold, motifs crystals auroras polar temples ancient guardians."
    elif "archon" in low or "arconte" in low or "demon" in low or "void" in low:
        set_tokens = " set identity: archon, dark demonic corrupted oppressive, palette dark purple crimson black, fractured cosmic motifs."

    if mode == "premium_legendary":
        tier = " premium legendary treatment, expanded motif detail, illustrated focal subject, richer glow layering, ceremonial silhouette priority."
    elif mode == "procedural_motif":
        tier = " motif-forward treatment, clear central symbol, reduced random repetition, narrative composition."
    else:
        tier = " abstract procedural treatment with controlled geometry noise and clear value hierarchy."

    return (p + tier + set_tokens + " keep pixel clarity full hd no blur no stretch.").strip()


def generate(card_id: str, card_type: str, prompt: str, seed: int, out_path: Path) -> dict:
    """Advanced layered card art generation with safe fallback to current generator."""
    mode = _mode_for(card_type, prompt)
    enriched_prompt = _enrich_prompt(prompt, mode)
    seed_bump = 0 if mode == "procedural_abstract" else 71 if mode == "procedural_motif" else 173

    try:
        result = gen_card_art32.generate(card_id, card_type, enriched_prompt, seed + seed_bump, out_path)
        if isinstance(result, dict):
            result = dict(result)
            result.setdefault("generator_used", GEN_CARD_ART_ADVANCED_VERSION)
            result.setdefault("treatment_mode", mode)
            result.setdefault("prompt_enriched", True)
            return result
        return {
            "card_id": card_id,
            "path": str(out_path),
            "generator_used": GEN_CARD_ART_ADVANCED_VERSION,
            "treatment_mode": mode,
            "prompt_enriched": True,
        }
    except Exception:
        # Preserve legacy flow by retrying through base generator semantics.
        fallback = gen_card_art32.generate(card_id, card_type, prompt, seed + 137, out_path)
        if isinstance(fallback, dict):
            fallback = dict(fallback)
            fallback.setdefault("generator_used", f"fallback::{GEN_CARD_ART_ADVANCED_VERSION}")
            fallback.setdefault("treatment_mode", mode)
            fallback.setdefault("prompt_enriched", False)
        return fallback
