# QA Report Post Combat Polish (Full)

- Overall Status: **WARNING**

## Build Snapshot
```json
{
  "game_version": "0.9.106a",
  "build_name": "Font Context Normalization Hotfix",
  "git_commit_hash": "0bd2874",
  "generated_at": "2026-03-09T15:42:43-03:00",
  "total_cards": 120,
  "total_cards_base": 60,
  "total_cards_hiperboria": 60,
  "total_relics": 12,
  "total_enemies": 31,
  "total_bosses": 4,
  "total_codex_entries": 142,
  "total_generated_assets": 217,
  "total_curated_assets": 10
}
```

## Baseline QA — WARNING

cards=120 avg_turns_battle=7.93 avg_turns_boss=7.29 boss_win_rate=1.0

```json
{
  "cards_checked_total": 120,
  "cards_checked_base": 60,
  "cards_checked_hiperboria": 60,
  "invalid_cards": 0,
  "duplicate_logic_cards": 10,
  "duplicate_visual_cards": 0,
  "avg_turns_battle": 7.93,
  "avg_turns_boss": 7.29,
  "boss_win_rate": 1.0,
  "relic_errors": 0,
  "art_failures": 0,
  "localization_issues": 5,
  "deck_check_rc": 0,
  "missing_kpi_icons": 7,
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
      "avg_turns_combat": 3.38,
      "avg_turns_boss": 3.5,
      "boss_win_rate": 1.0
    },
    "harmony_guardian": {
      "avg_damage": 55.9,
      "avg_turns_combat": 9.25,
      "avg_turns_boss": 9.5,
      "boss_win_rate": 1.0
    },
    "oracle_of_fate": {
      "avg_damage": 46.9,
      "avg_turns_combat": 8.25,
      "avg_turns_boss": 13,
      "boss_win_rate": 0.5
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
    "draw_if_direction_played": 2,
    "double_block_cap": 2,
    "damage_plus_rupture": 3
  }
}
```

## Content Registry — WARNING

registries=8 duplicate_ids=1 missing_ids=0

```json
{
  "registry_sizes": {
    "cards": 120,
    "relics": 12,
    "enemies": 31,
    "bosses": 4,
    "biomes": 4,
    "civilizations_sets": 2,
    "codex_entries": 142,
    "dialogue_scene_entries": 46
  },
  "missing_ids": {
    "cards": [],
    "relics": [],
    "enemies": [],
    "bosses": [],
    "biomes": [],
    "civilizations_sets": [],
    "codex_entries": [],
    "dialogue_scene_entries": []
  },
  "duplicate_ids": {
    "cards": [],
    "relics": [],
    "enemies": [],
    "bosses": [],
    "biomes": [],
    "civilizations_sets": [],
    "codex_entries": [],
    "dialogue_scene_entries": [
      "default"
    ]
  },
  "orphaned_entries": {
    "codex_missing_cards": [],
    "codex_missing_relics": [],
    "dialogue_enemy_refs_not_found": []
  },
  "assets_existing_but_not_referenced": [
    "_placeholder",
    "anillo_de_proteccion",
    "barrera_sagrada",
    "baston_del_umbral",
    "calculo_del_cosmos",
    "caparazon_kaypacha",
    "circulo_de_invocacion",
    "claridad_del_hanan",
    "corte_del_puma",
    "corte_dimensional",
    "desgarro_del_vacio",
    "equilibrio_mental",
    "espejo_astral",
    "fortaleza_chakana",
    "golpe_del_trueno",
    "guardia_solar",
    "impacto_solar",
    "lanza_del_amanecer",
    "luz_del_hanan",
    "mapa_del_destino",
    "meditacion_profunda",
    "mente_serena",
    "ojo_del_condor",
    "ojo_interior",
    "profecia_del_umbral",
    "punal_de_luz",
    "refugio_espiritual",
    "ruptura_del_umbral",
    "sello_de_los_tres_pachas",
    "tormenta_de_lanzas",
    "tormenta_mistica"
  ],
  "references_to_removed_assets": []
}
```

## Cards — WARNING

cards=120 base=60 hiperboria=60 invalid=0

```json
{
  "expected": {
    "total": 120,
    "base": 60,
    "hiperboria": 60
  },
  "actual": {
    "total": 120,
    "base": 60,
    "hiperboria": 60
  },
  "invalid_cards": [],
  "missing_lore": [],
  "missing_set_tag": [],
  "missing_tags": [],
  "missing_art": [],
  "duplicate_names": [],
  "effect_mapping_issues": [
    "filo_en_cadena:draw_if_direction_played",
    "fusion_espiritual:double_block_cap",
    "cw_lore_10:draw_if_direction_played",
    "hg_lore_13:double_block_cap",
    "hip_cosmic_warrior_05:damage_plus_rupture",
    "hip_cosmic_warrior_10:damage_plus_rupture",
    "hip_cosmic_warrior_15:damage_plus_rupture"
  ]
}
```

## Rendering — PASS

contexts=7 failures=0 warnings=0

```json
{
  "per_context": {
    "combat_hand": {
      "rendered": 6,
      "warnings": []
    },
    "hover_preview": {
      "rendered": 6,
      "warnings": []
    },
    "deck_view": {
      "rendered": 6,
      "warnings": []
    },
    "codex_view": {
      "rendered": 6,
      "warnings": []
    },
    "shop_view": {
      "rendered": 6,
      "warnings": []
    },
    "pack_view": {
      "rendered": 6,
      "warnings": []
    },
    "archetype_preview": {
      "rendered": 6,
      "warnings": []
    }
  },
  "render_failures": [],
  "warnings": []
}
```

## Combat HUD — PASS

ratios=0.32/0.213/0.467 missing_icons=0

```json
{
  "ratios": {
    "top": 0.32,
    "mid": 0.213,
    "bottom": 0.467
  },
  "expected": {
    "top": 0.3,
    "mid": 0.2,
    "bottom": 0.5
  },
  "missing_icons": [],
  "overlap": {
    "hand_vs_actions": false,
    "hand_vs_player": false,
    "enemy_vs_topbar": false
  }
}
```

## Hand Layout — PASS

states=3 warnings=0

```json
{
  "states": {
    "3": {
      "spacing": 860,
      "left": 22,
      "right": 1899,
      "in_bounds": true
    },
    "5": {
      "spacing": 430,
      "left": 22,
      "right": 1899,
      "in_bounds": true
    },
    "7": {
      "spacing": 286,
      "left": 24,
      "right": 1897,
      "in_bounds": true
    }
  },
  "warnings": []
}
```

## Fonts — WARNING

missing_custom_files=5 missing_contexts=0

```json
{
  "font_dir": "C:\\Users\\mxpri\\PurpleWizard\\deckcards-python-purplewizard\\game\\assets\\fonts",
  "missing_custom_files": [
    "chakana_pixel.ttf",
    "chakana_ui.ttf",
    "chakana_mono.ttf",
    "chakana_title.ttf",
    "chakana_lore.ttf"
  ],
  "fallback_font_count": 5,
  "registered_contexts": [
    "card_body",
    "card_effect",
    "card_footer",
    "card_lore",
    "card_title",
    "card_titles",
    "card_type",
    "codex_header",
    "codex_headers",
    "combat_label",
    "combat_labels",
    "combat_title",
    "combat_value",
    "hud_numbers",
    "hud_value",
    "lore_text",
    "map_label",
    "map_labels",
    "map_title",
    "menu_label",
    "menu_title",
    "modal_label",
    "modal_title",
    "shop_header",
    "shop_headers",
    "special_pixel_label"
  ],
  "missing_contexts": []
}
```

## Icons — WARNING

missing_required=1 missing_mappings=3

```json
{
  "required_missing": [
    "draw_if"
  ],
  "missing_mapping_effect_types": [
    "damage_plus_rupture",
    "double_block_cap",
    "draw_if_direction_played"
  ],
  "duplicate_alias_entries": 0,
  "used_effect_types": 18
}
```

## Audio — WARNING

contexts_missing=0 stale_manifest_entries=0

```json
{
  "active_track_by_context": {
    "menu": {
      "track_key": "menu",
      "file": "music/menu__v1.wav"
    },
    "map": {
      "track_key": "map_umbral",
      "file": "music/map_umbral__v1.wav"
    },
    "shop": {
      "track_key": "shop",
      "file": "music/shop__v1.wav"
    },
    "combat": {
      "track_key": "combat_umbral",
      "file": "music/combat_umbral__v1.wav"
    },
    "boss": {
      "track_key": "boss",
      "file": "music/boss__v1.wav"
    },
    "victory": {
      "track_key": "victory",
      "file": "music/victory__v1.wav"
    },
    "defeat": {
      "track_key": "ending",
      "file": "music/ending__v1.wav"
    }
  },
  "missing_contexts": [],
  "cache_anomalies": {
    "stale_manifest_entries": [],
    "duplicate_generated_files": [
      ".gitkeep"
    ]
  },
  "whistle_artifact_check": "manual_review_required"
}
```

## Scenes — PASS

missing_scene_files=0 missing_portrait_assets=0

```json
{
  "missing_scene_files": [],
  "missing_portrait_assets": [],
  "missing_dialogue_files": [],
  "text_bounds_check": "wrapped dialogue blocks present; keep manual visual verification"
}
```

## Codex — PASS

missing_tabs=0 empty_groups=0

```json
{
  "missing_tabs": [],
  "group_counts": {
    "base_cards": 60,
    "hiperboria_cards": 60,
    "relics": 12
  },
  "empty_groups": []
}
```

## Performance — WARNING

benchmarks=5 heavy_contexts=2

```json
{
  "benchmarks_ms": [
    {
      "label": "card_render",
      "avg_ms": 4.757,
      "p95_ms": 5.834,
      "max_ms": 7.029
    },
    {
      "label": "hover_render",
      "avg_ms": 5.551,
      "p95_ms": 7.313,
      "max_ms": 11.705
    },
    {
      "label": "combat_hud_render",
      "avg_ms": 0.59,
      "p95_ms": 0.728,
      "max_ms": 0.854
    },
    {
      "label": "codex_card_preview",
      "avg_ms": 5.342,
      "p95_ms": 6.183,
      "max_ms": 6.804
    },
    {
      "label": "scene_hologram_render",
      "avg_ms": 0.001,
      "p95_ms": 0.001,
      "max_ms": 0.006
    }
  ],
  "heavy_contexts": [
    {
      "label": "hover_render",
      "avg_ms": 5.551,
      "p95_ms": 7.313,
      "max_ms": 11.705
    },
    {
      "label": "codex_card_preview",
      "avg_ms": 5.342,
      "p95_ms": 6.183,
      "max_ms": 6.804
    }
  ]
}
```

## Risks
```json
{
  "priority_1_runtime": [],
  "priority_2_visual_integrity": [
    "Content Registry: registries=8 duplicate_ids=1 missing_ids=0",
    "Cards: cards=120 base=60 hiperboria=60 invalid=0",
    "Audio: contexts_missing=0 stale_manifest_entries=0"
  ],
  "priority_3_maintainability": [
    "Baseline QA: cards=120 avg_turns_battle=7.93 avg_turns_boss=7.29 boss_win_rate=1.0",
    "Fonts: missing_custom_files=5 missing_contexts=0",
    "Icons: missing_required=1 missing_mappings=3",
    "Performance: benchmarks=5 heavy_contexts=2"
  ]
}
```

## Recommended Next Actions
1. font pipeline consolidation (custom files + context mapping).
2. audio cache/manifest cleanup and context track verification.
