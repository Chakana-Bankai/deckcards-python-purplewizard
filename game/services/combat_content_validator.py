from __future__ import annotations

from collections import Counter, defaultdict


def _sum_effect(card: dict, types: set[str]) -> int:
    total = 0
    for eff in list(card.get("effects", []) or []):
        if not isinstance(eff, dict):
            continue
        if str(eff.get("type", "")).lower() in types:
            total += int(eff.get("amount", 0) or 0)
    return int(total)


def validate_combat_content_lock(cards: list[dict], relics: list[dict], codex_cards: dict, codex_relics: dict, lang_es: dict | None = None, lang_en: dict | None = None) -> dict:
    issues: list[str] = []
    warnings: list[str] = []

    cards = [c for c in list(cards or []) if isinstance(c, dict)]
    relics = [r for r in list(relics or []) if isinstance(r, dict)]

    if len(cards) != 60:
        issues.append(f"cards_count:{len(cards)} expected 60")

    by_arch = Counter(str(c.get("archetype", "")) for c in cards)
    for aid in ("cosmic_warrior", "harmony_guardian", "oracle_of_fate"):
        if by_arch.get(aid, 0) != 20:
            issues.append(f"archetype_count:{aid}:{by_arch.get(aid, 0)} expected 20")

    # Locked rarity distribution per archetype: 12 common / 7 uncommon / 1 legendary.
    for aid in ("cosmic_warrior", "harmony_guardian", "oracle_of_fate"):
        subset = [c for c in cards if str(c.get("archetype", "")) == aid]
        rc = Counter()
        for c in subset:
            r = str(c.get("rarity", "common")).lower()
            if r == "rare":
                r = "uncommon"
            if r not in {"common", "uncommon", "legendary"}:
                r = "common"
            rc[r] += 1
        if int(rc.get("common", 0)) != 12 or int(rc.get("uncommon", 0)) != 7 or int(rc.get("legendary", 0)) != 1:
            issues.append(
                f"rarity_distribution:{aid}:common={int(rc.get('common',0))},uncommon={int(rc.get('uncommon',0))},legendary={int(rc.get('legendary',0))} expected 12/7/1"
            )

    # Archetype identity by effect footprint.
    arch_cards = defaultdict(list)
    for c in cards:
        arch_cards[str(c.get("archetype", ""))].append(c)

    cw = arch_cards.get("cosmic_warrior", [])
    hg = arch_cards.get("harmony_guardian", [])
    of = arch_cards.get("oracle_of_fate", [])

    cw_damage = sum(_sum_effect(c, {"damage", "damage_plus_rupture"}) for c in cw)
    cw_rupture = sum(_sum_effect(c, {"rupture", "apply_break", "set_rupture", "self_break"}) for c in cw)
    cw_combo = sum(1 for c in cw if {"copy_last_played", "copy_next_played"}.intersection({str(e.get("type", "")).lower() for e in c.get("effects", []) if isinstance(e, dict)}))
    if cw_damage <= 0 or cw_rupture <= 0 or cw_combo <= 0:
        issues.append("archetype_identity:cosmic_warrior")

    hg_block = sum(_sum_effect(c, {"gain_block", "block"}) for c in hg)
    hg_harmony = sum(_sum_effect(c, {"harmony_delta", "consume_harmony"}) for c in hg)
    hg_seal = sum(1 for c in hg if "seal" in {str(t).lower() for t in c.get("tags", [])})
    if hg_block <= 0 or hg_harmony <= 0 or hg_seal <= 0:
        issues.append("archetype_identity:harmony_guardian")

    of_draw = sum(_sum_effect(c, {"draw"}) for c in of)
    of_scry = sum(_sum_effect(c, {"scry"}) for c in of)
    of_ritual = sum(_sum_effect(c, {"harmony_delta", "consume_harmony", "ritual_trama"}) for c in of)
    if of_draw <= 0 or of_scry <= 0 or of_ritual <= 0:
        issues.append("archetype_identity:oracle_of_fate")

    # Soft range checks (warnings only).
    dmg_by_rarity = defaultdict(list)
    blk_by_rarity = defaultdict(list)
    for c in cards:
        rarity = str(c.get("rarity", "common")).lower()
        dmg = _sum_effect(c, {"damage"})
        blk = _sum_effect(c, {"gain_block", "block"})
        if dmg > 0:
            dmg_by_rarity[rarity].append(dmg)
        if blk > 0:
            blk_by_rarity[rarity].append(blk)

    # Expected floor/ceiling windows for quick lock checks.
    windows = {
        "common": (3, 5),
        "uncommon": (5, 7),
        "rare": (6, 9),
        "legendary": (8, 12),
    }
    for rarity, (low, high) in windows.items():
        arr = dmg_by_rarity.get(rarity, [])
        if arr:
            avg = sum(arr) / float(len(arr))
            if not (max(1, low - 1) <= avg <= high + 2):
                warnings.append(f"damage_window:{rarity}:avg={avg:.2f} expected~{low}-{high}")
        arrb = blk_by_rarity.get(rarity, [])
        if arrb:
            avg_b = sum(arrb) / float(len(arrb))
            # Small samples create noisy warnings for incidental block on non-defense legendaries.
            if len(arrb) >= 3 and not (max(1, low - 1) <= avg_b <= high + 2):
                warnings.append(f"block_window:{rarity}:avg={avg_b:.2f} expected~{low}-{high}")

    if len(relics) != 12:
        issues.append(f"relics_count:{len(relics)} expected 12")
    relic_ids = [str(r.get("id", "")) for r in relics if r.get("id")]
    if len(set(relic_ids)) != len(relic_ids):
        issues.append("relic_duplicate_ids")
    for r in relics:
        rid = str(r.get("id", ""))
        if not str(r.get("name_key", "")).strip():
            issues.append(f"relic_name_key_missing:{rid}")
        if not str(r.get("text_key", "")).strip():
            issues.append(f"relic_text_key_missing:{rid}")
        lore = str(r.get("lore_text", "")).strip()
        if not lore:
            issues.append(f"relic_lore_missing:{rid}")
        elif len(lore) > 120:
            warnings.append(f"relic_lore_long:{rid}")


    # Relic text key presence in localization files.
    if isinstance(lang_es, dict) and isinstance(lang_en, dict):
        for r in relics:
            rid = str(r.get("id", ""))
            nk = str(r.get("name_key", "")).strip()
            tk = str(r.get("text_key", "")).strip()
            if nk and nk not in lang_es:
                issues.append(f"relic_name_key_missing_es:{rid}")
            if nk and nk not in lang_en:
                issues.append(f"relic_name_key_missing_en:{rid}")
            if tk and tk not in lang_es:
                issues.append(f"relic_text_key_missing_es:{rid}")
            if tk and tk not in lang_en:
                issues.append(f"relic_text_key_missing_en:{rid}")

    codex_cards_items = list((codex_cards or {}).get("cards", []) or [])
    codex_card_ids = {str(c.get("id", "")) for c in codex_cards_items if isinstance(c, dict) and c.get("id")}
    if len(codex_cards_items) != 60 or len(codex_card_ids) != 60:
        issues.append(f"codex_cards_coverage:{len(codex_card_ids)} expected 60")

    codex_relic_items = list((codex_relics or {}).get("relics", []) or [])
    codex_relic_ids = {str(c.get("id", "")) for c in codex_relic_items if isinstance(c, dict) and c.get("id")}
    if len(codex_relic_ids) != 12:
        issues.append(f"codex_relics_coverage:{len(codex_relic_ids)} expected 12")

    return {
        "status": "OK" if not issues else "WARN",
        "cards": len(cards),
        "relics": len(relics),
        "issues": issues,
        "warnings": warnings,
    }
