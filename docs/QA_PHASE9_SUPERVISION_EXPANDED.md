# Phase 9 QA Supervision Expanded

## Metrics
- `cards_checked_total`: 120
- `cards_checked_base`: 60
- `cards_checked_hiperboria`: 60
- `invalid_cards`: 0
- `duplicate_logic_cards`: 25
- `duplicate_visual_cards`: 0
- `avg_turns_battle`: 12.95
- `avg_turns_boss`: 14.43
- `boss_win_rate`: 0.286
- `relic_errors`: 0
- `art_failures`: 60
- `localization_issues`: 5
- `missing_kpi_icons`: 26
- `effect_text_overflow_risk`: 0
- `deck_check_rc`: 0

## Archetype Simulation (10 each)
- `cosmic_warrior`: avg_damage=49.8 avg_turns_combat=4.12 avg_turns_boss=4.5 boss_win_rate=1.0
- `harmony_guardian`: avg_damage=0 avg_turns_combat=18.38 avg_turns_boss=16.5 boss_win_rate=0.0
- `oracle_of_fate`: avg_damage=21.3 avg_turns_combat=17.62 avg_turns_boss=16.5 boss_win_rate=0.0

## Map Distribution
- combats_like=10 events=2 relic=1 shop=1 boss=1 sanctuary=1

## Audio and Intro
- bgm_context_missing=[]
- stingers_missing=[]
- intro_duration=4.0 intro_has_logo=True intro_cosmic_bg=True

## Issues Sample

## Missing Icon Types
- `heal`: 11
- `exhaust_self`: 6
- `damage_plus_rupture`: 3
- `draw_if_direction_played`: 2
- `double_block_cap`: 2
- `retain`: 2

## Raw JSON
```json
{
  "cards_checked_total": 120,
  "cards_checked_base": 60,
  "cards_checked_hiperboria": 60,
  "invalid_cards": 0,
  "duplicate_logic_cards": 25,
  "duplicate_visual_cards": 0,
  "avg_turns_battle": 12.95,
  "avg_turns_boss": 14.43,
  "boss_win_rate": 0.286,
  "relic_errors": 0,
  "art_failures": 60,
  "localization_issues": 5,
  "deck_check_rc": 0,
  "missing_kpi_icons": 26,
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
      "avg_damage": 49.8,
      "avg_turns_combat": 4.12,
      "avg_turns_boss": 4.5,
      "boss_win_rate": 1.0
    },
    "harmony_guardian": {
      "avg_damage": 0,
      "avg_turns_combat": 18.38,
      "avg_turns_boss": 16.5,
      "boss_win_rate": 0.0
    },
    "oracle_of_fate": {
      "avg_damage": 21.3,
      "avg_turns_combat": 17.62,
      "avg_turns_boss": 16.5,
      "boss_win_rate": 0.0
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
    "intro_duration": 4.0,
    "intro_has_logo": true,
    "intro_cosmic_bg": true
  },
  "required_field_issues_sample": [],
  "missing_icon_types": {
    "exhaust_self": 6,
    "heal": 11,
    "draw_if_direction_played": 2,
    "double_block_cap": 2,
    "retain": 2,
    "damage_plus_rupture": 3
  }
}
```
