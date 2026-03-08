from __future__ import annotations

from collections import Counter

TARGET_ARCHETYPES = ("cosmic_warrior", "harmony_guardian", "oracle_of_fate")
TARGET_DISTRIBUTION = {"common": 12, "uncommon": 7, "legendary": 1}
VALID_RARITIES = {"common", "uncommon", "legendary"}


def _normalized_rarity(value: str) -> str:
    r = str(value or "common").strip().lower()
    if r == "rare":
        return "uncommon"
    if r not in VALID_RARITIES:
        return "common"
    return r


def _score_card_for_promotion(card: dict) -> tuple:
    cost = int(card.get("cost", 0) or 0)
    effects = len(list(card.get("effects", []) or []))
    # Promote more expressive commons first.
    return (cost, effects, str(card.get("id", "")))


def _score_card_for_demotion(card: dict) -> tuple:
    cost = int(card.get("cost", 0) or 0)
    effects = len(list(card.get("effects", []) or []))
    # Demote lowest-impact uncommons first.
    return (cost, effects, str(card.get("id", "")))


def enforce_archetype_rarity_distribution(cards: list[dict]) -> dict:
    """Auto-fix archetype rarity distribution to 12/7/1.

    Keeps card effects/lore untouched and only edits the `rarity` field when needed.
    """
    items = [c for c in list(cards or []) if isinstance(c, dict) and c.get("id")]
    changed = False
    logs: list[str] = []

    by_arch: dict[str, list[dict]] = {}
    for arch in TARGET_ARCHETYPES:
        by_arch[arch] = [c for c in items if str(c.get("archetype", "")).strip().lower() == arch]

    for arch, arr in by_arch.items():
        if not arr:
            logs.append(f"[content] archetype {arch}: missing cards")
            continue

        # 1) Normalize rarity labels first.
        for c in arr:
            nr = _normalized_rarity(c.get("rarity", "common"))
            if str(c.get("rarity", "common")).lower() != nr:
                c["rarity"] = nr
                changed = True

        # 2) Ensure exactly one legendary.
        legends = [c for c in arr if str(c.get("rarity", "")).lower() == "legendary"]
        if len(legends) > 1:
            keep = legends[0]
            for c in legends[1:]:
                c["rarity"] = "uncommon"
                changed = True
            legends = [keep]
        elif len(legends) == 0:
            source = sorted(arr, key=_score_card_for_promotion, reverse=True)
            pick = source[0]
            pick["rarity"] = "legendary"
            changed = True
            legends = [pick]

        # 3) Enforce uncommon/common targets (excluding the single legendary).
        non_leg = [c for c in arr if c not in legends]
        uncommons = [c for c in non_leg if str(c.get("rarity", "")).lower() == "uncommon"]
        commons = [c for c in non_leg if str(c.get("rarity", "")).lower() != "uncommon"]

        target_uncommon = TARGET_DISTRIBUTION["uncommon"]
        target_common = TARGET_DISTRIBUTION["common"]

        if len(uncommons) > target_uncommon:
            to_demote = sorted(uncommons, key=_score_card_for_demotion)[: len(uncommons) - target_uncommon]
            for c in to_demote:
                c["rarity"] = "common"
                changed = True
        elif len(uncommons) < target_uncommon:
            need = target_uncommon - len(uncommons)
            promotable = sorted(commons, key=_score_card_for_promotion, reverse=True)[:need]
            for c in promotable:
                c["rarity"] = "uncommon"
                changed = True

        # 4) Final safety pass for invalid totals.
        cnt = Counter(str(c.get("rarity", "common")).lower() for c in arr)
        if int(cnt.get("common", 0)) + int(cnt.get("uncommon", 0)) + int(cnt.get("legendary", 0)) != len(arr):
            for c in arr:
                c["rarity"] = _normalized_rarity(c.get("rarity", "common"))
            changed = True
            cnt = Counter(str(c.get("rarity", "common")).lower() for c in arr)

        logs.append(
            f"[content] archetype {arch}: {int(cnt.get('common',0))} common, "
            f"{int(cnt.get('uncommon',0))} uncommon, {int(cnt.get('legendary',0))} legendary"
        )

        # If totals differ from 20, keep data but log clearly.
        if len(arr) != 20:
            logs.append(f"[content] archetype {arch}: total={len(arr)} expected=20")
        if int(cnt.get("common", 0)) != target_common or int(cnt.get("uncommon", 0)) != target_uncommon or int(cnt.get("legendary", 0)) != 1:
            logs.append(f"[content] archetype {arch}: distribution mismatch remains after autofix")

    return {"cards": items, "changed": changed, "logs": logs}
