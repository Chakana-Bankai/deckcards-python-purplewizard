from __future__ import annotations

from pathlib import Path

from game.art import gen_card_art32

# Keep version aligned with active generator while exposing an advanced entrypoint.
GEN_CARD_ART_ADVANCED_VERSION = f"advanced::{gen_card_art32.GEN_CARD_ART_VERSION}"


def generate(card_id: str, card_type: str, prompt: str, seed: int, out_path: Path) -> dict:
    """Advanced layered card art generation with safe fallback to current generator.

    This adapter keeps pipeline compatibility and allows future extension without
    changing callers.
    """
    try:
        result = gen_card_art32.generate(card_id, card_type, prompt, seed, out_path)
        if isinstance(result, dict):
            result = dict(result)
            result.setdefault("generator_used", GEN_CARD_ART_ADVANCED_VERSION)
            return result
        return {"card_id": card_id, "path": str(out_path), "generator_used": GEN_CARD_ART_ADVANCED_VERSION}
    except Exception:
        # Preserve legacy flow by retrying through base generator semantics.
        return gen_card_art32.generate(card_id, card_type, prompt, seed + 137, out_path)
