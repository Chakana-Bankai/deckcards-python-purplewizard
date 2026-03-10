from __future__ import annotations

"""Content lock validator for 1.0 scope auditability."""

from pathlib import Path

from game.core.paths import data_dir
from game.core.safe_io import load_json
from game.services.card_coherence import validate_cards_coherence
from game.services.combat_content_validator import validate_combat_content_lock


def _ids(items: list[dict]) -> set[str]:
    return {str(x.get("id", "")) for x in items if isinstance(x, dict) and x.get("id")}


def _hp_values(items: list[dict]) -> list[int]:
    vals: list[int] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        hp = row.get("hp")
        if isinstance(hp, list):
            for v in hp:
                try:
                    vals.append(int(v))
                except Exception:
                    pass
        else:
            try:
                vals.append(int(hp))
            except Exception:
                pass
    return vals


def validate_content_lock_1_0(base: Path | None = None) -> dict:
    base = base or data_dir()
    issues: list[str] = []
    warnings: list[str] = []

    spec = load_json(base / "content_lock_1_0.json", default={})
    if not isinstance(spec, dict):
        spec = {}

    cards = load_json(base / "cards.json", default=[])
    relics = load_json(base / "relics.json", default=[])
    enemies = load_json(base / "enemies" / "enemies_30.json", default=[])
    bosses = load_json(base / "enemies" / "bosses_3.json", default=[])
    biomes = load_json(base / "biomes.json", default=[])
    events = load_json(base / "events.json", default=[])
    archons = load_json(base / "archons_1_0.json", default=[])
    codex = load_json(base / "codex.json", default={})
    codex_cards = load_json(base / "codex_cards_lore_set1.json", default={})
    codex_relics = load_json(base / "codex_relics_lore_set1.json", default={})
    lang_es = load_json(base / "lang" / "es.json", default={})
    lang_en = load_json(base / "lang" / "en.json", default={})

    cards = [c for c in cards if isinstance(c, dict)] if isinstance(cards, list) else []
    relics = [r for r in relics if isinstance(r, dict)] if isinstance(relics, list) else []
    enemies = [e for e in enemies if isinstance(e, dict)] if isinstance(enemies, list) else []
    bosses = [b for b in bosses if isinstance(b, dict)] if isinstance(bosses, list) else []
    biomes = [b for b in biomes if isinstance(b, dict)] if isinstance(biomes, list) else []
    events = [e for e in events if isinstance(e, dict)] if isinstance(events, list) else []
    archons = [a for a in archons if isinstance(a, dict)] if isinstance(archons, list) else []

    target = {
        "cards": int(spec.get("cards", 60) or 60),
        "relics": int(spec.get("relics", 12) or 12),
        "enemies": int(spec.get("enemies", 31) or 31),
        "bosses": int(spec.get("bosses", 4) or 4),
        "biomes": int(spec.get("biomes", 4) or 4),
        "events": int(spec.get("events", 6) or 6),
        "archons": int(spec.get("archons", 4) or 4),
        "codex_sections": int(spec.get("codex_sections", 10) or 10),
        "codex_cards": int(spec.get("codex_cards", 60) or 60),
        "codex_relics": int(spec.get("codex_relics", 12) or 12),
        "tutorial_steps": int(spec.get("tutorial_steps", 7) or 7),
    }

    if len(cards) != target["cards"]:
        issues.append(f"cards_count:{len(cards)} expected {target['cards']}")
    if len(relics) != target["relics"]:
        issues.append(f"relics_count:{len(relics)} expected {target['relics']}")
    if len(enemies) != target["enemies"]:
        issues.append(f"enemies_count:{len(enemies)} expected {target['enemies']}")
    if len(bosses) != target["bosses"]:
        issues.append(f"bosses_count:{len(bosses)} expected {target['bosses']}")
    if len(biomes) != target["biomes"]:
        issues.append(f"biomes_count:{len(biomes)} expected {target['biomes']}")
    if len(events) != target["events"]:
        issues.append(f"events_count:{len(events)} expected {target['events']}")
    if len(archons) != target["archons"]:
        issues.append(f"archons_count:{len(archons)} expected {target['archons']}")

    combat = validate_combat_content_lock(cards, relics, codex_cards, codex_relics, lang_es=lang_es, lang_en=lang_en)
    issues.extend(list(combat.get("issues", []) or []))
    warnings.extend(list(combat.get("warnings", []) or []))

    coherence = validate_cards_coherence(cards)
    if bool(coherence.get("ok", False)) is False:
        warnings.append(f"card_coherence_warnings:{int(coherence.get('warnings', 0) or 0)}")

    codex_sections = list((codex or {}).get("sections", []) or []) if isinstance(codex, dict) else []
    if len(codex_sections) != target["codex_sections"]:
        issues.append(f"codex_sections_count:{len(codex_sections)} expected {target['codex_sections']}")

    required_ids = {
        "lore", "systems", "rules", "cards", "enemies", "archons", "biomes", "relics", "builds", "tips_help"
    }
    sec_ids = {str(s.get("id", "")) for s in codex_sections if isinstance(s, dict)}
    missing_sections = sorted(required_ids - sec_ids)
    if missing_sections:
        issues.append("codex_missing_sections:" + ",".join(missing_sections))

    rules_section = next((s for s in codex_sections if isinstance(s, dict) and str(s.get("id", "")) == "rules"), {})
    items = list(rules_section.get("items", []) or []) if isinstance(rules_section, dict) else []
    if len(items) < 3:
        issues.append(f"rules_items_count:{len(items)} expected >=3")

    card_ids = _ids(cards)
    codex_card_ids = _ids(list((codex_cards or {}).get("cards", []) or []) if isinstance(codex_cards, dict) else [])
    if len(codex_card_ids) != target["codex_cards"]:
        issues.append(f"codex_cards_count:{len(codex_card_ids)} expected {target['codex_cards']}")
    missing_cards = sorted(card_ids - codex_card_ids)
    if missing_cards:
        issues.append(f"codex_missing_cards:{len(missing_cards)}")

    relic_ids = _ids(relics)
    codex_relic_ids = _ids(list((codex_relics or {}).get("relics", []) or []) if isinstance(codex_relics, dict) else [])
    if len(codex_relic_ids) != target["codex_relics"]:
        issues.append(f"codex_relics_count:{len(codex_relic_ids)} expected {target['codex_relics']}")
    missing_relics = sorted(relic_ids - codex_relic_ids)
    if missing_relics:
        issues.append(f"codex_missing_relics:{len(missing_relics)}")

    non_boss_enemy_hp = _hp_values([e for e in enemies if str(e.get("tier", "")).lower() != "boss"])
    boss_hp = _hp_values(bosses)
    if non_boss_enemy_hp:
        max_enemy_hp = max(non_boss_enemy_hp)
        if max_enemy_hp > 220:
            warnings.append(f"enemy_hp_high:max={max_enemy_hp}")
    if boss_hp:
        max_boss_hp = max(boss_hp)
        if max_boss_hp > 360:
            warnings.append(f"boss_hp_high:max={max_boss_hp}")

    return {
        "status": "OK" if not issues else "WARN",
        "version": "1.0",
        "counts": {
            "cards": len(cards),
            "relics": len(relics),
            "enemies": len(enemies),
            "bosses": len(bosses),
            "biomes": len(biomes),
            "events": len(events),
            "archons": len(archons),
        },
        "issues": issues,
        "warnings": warnings,
    }
