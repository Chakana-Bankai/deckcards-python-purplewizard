from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS_PATH = ROOT / "game" / "data" / "cards.json"
PROMPTS_PATH = ROOT / "game" / "data" / "card_prompts.json"

CONTROL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def fail(msg: str) -> int:
    print(f"[validate_prompts] FAIL: {msg}")
    return 1


def main() -> int:
    cards = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
    payload = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))

    if not isinstance(payload, dict) or not isinstance(payload.get("cards"), dict):
        return fail("card_prompts.json must be an object with a 'cards' object")

    card_ids = [str(c.get("id", "")).strip() for c in cards if isinstance(c, dict)]
    card_ids = [cid for cid in card_ids if cid]
    prompts_cards = payload["cards"]

    if len(prompts_cards) != len(card_ids):
        return fail(f"prompt count mismatch prompts={len(prompts_cards)} cards={len(card_ids)}")

    seen = set()
    for cid in card_ids:
        if cid in seen:
            return fail(f"duplicate card id in cards.json: {cid}")
        seen.add(cid)
        if cid not in prompts_cards:
            return fail(f"missing prompt for card id: {cid}")

    for cid, entry in prompts_cards.items():
        if cid not in seen:
            return fail(f"extra prompt card id not in cards.json: {cid}")
        if not isinstance(entry, dict):
            return fail(f"prompt entry for {cid} must be object")
        prompt = str(entry.get("prompt", ""))
        if not (12 <= len(prompt) <= 260):
            return fail(f"prompt length out of range for {cid}: {len(prompt)}")
        if CONTROL_RE.search(prompt):
            return fail(f"weird control character found in prompt for {cid}")

    print(f"[validate_prompts] PASS: {len(card_ids)} prompts validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
