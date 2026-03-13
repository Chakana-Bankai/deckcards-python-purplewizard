# Phase 9 QA Supervision Expanded

## Metrics
- `cards_checked_total`: 120
- `cards_checked_base`: 60
- `cards_checked_hiperboria`: 60
- `invalid_cards`: 0
- `duplicate_logic_cards`: 0
- `duplicate_visual_cards`: 0
- `avg_turns_battle`: 8.67
- `avg_turns_boss`: 7
- `boss_win_rate`: 1.0
- `relic_errors`: 0
- `art_failures`: 0
- `localization_issues`: 0
- `missing_kpi_icons`: 0
- `effect_text_overflow_risk`: 0
- `deck_check_rc`: 0

## Archetype Simulation (10 each)
- `cosmic_warrior`: avg_damage=39.3 avg_turns_combat=3.12 avg_turns_boss=2.5 boss_win_rate=1.0
- `harmony_guardian`: avg_damage=39.6 avg_turns_combat=11.12 avg_turns_boss=8.5 boss_win_rate=1.0
- `oracle_of_fate`: avg_damage=33 avg_turns_combat=11 avg_turns_boss=7.5 boss_win_rate=1.0

## Map Distribution
- combats_like=10 events=2 relic=1 shop=1 boss=1 sanctuary=1

## Audio and Intro
- bgm_context_missing=[]
- stingers_missing=[]
- intro_duration=5.8 intro_has_logo=True intro_cosmic_bg=True

## Issues Sample

## Missing Icon Types
- none

## Raw JSON
```json
{
  "cards_checked_total": 120,
  "cards_checked_base": 60,
  "cards_checked_hiperboria": 60,
  "invalid_cards": 0,
  "duplicate_logic_cards": 0,
  "duplicate_visual_cards": 0,
  "avg_turns_battle": 8.67,
  "avg_turns_boss": 7,
  "boss_win_rate": 1.0,
  "relic_errors": 0,
  "art_failures": 0,
  "localization_issues": 0,
  "deck_check_rc": 0,
  "missing_kpi_icons": 0,
  "effect_text_overflow_risk": 0,
  "map_distribution": {
    "combats_like": 10,
    "events": 2,
    "relic": 1,
    "shop": 1,
    "boss": 1,
    "sanctuary": 1,
    "raw": {
      "combat": 8,
      "event": 2,
      "sanctuary": 1,
      "shop": 1,
      "challenge": 1,
      "relic": 1,
      "elite": 1,
      "boss": 1
    }
  },
  "archetype_simulation": {
    "cosmic_warrior": {
      "avg_damage": 39.3,
      "avg_turns_combat": 3.12,
      "avg_turns_boss": 2.5,
      "boss_win_rate": 1.0
    },
    "harmony_guardian": {
      "avg_damage": 39.6,
      "avg_turns_combat": 11.12,
      "avg_turns_boss": 8.5,
      "boss_win_rate": 1.0
    },
    "oracle_of_fate": {
      "avg_damage": 33,
      "avg_turns_combat": 11,
      "avg_turns_boss": 7.5,
      "boss_win_rate": 1.0
    }
  },
  "audio_intro": {
    "bgm_context_ok": [
      "boss",
      "menu",
      "shop",
      "victory"
    ],
    "bgm_context_missing": [],
    "stingers_ok": [
      "boss_reveal",
      "combat_start",
      "defeat",
      "harmony_ready",
      "level_up",
      "pack_open",
      "relic_gain",
      "seal_ready",
      "victory"
    ],
    "stingers_missing": [],
    "audio_manifest_exists": true,
    "intro_duration": 5.8,
    "intro_has_logo": true,
    "intro_cosmic_bg": true
  },
  "required_field_issues_sample": [],
  "missing_icon_types": {}
}
```
