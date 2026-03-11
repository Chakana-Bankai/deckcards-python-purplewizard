from .common import ROOT, write_text_report, rel


def _paths(items):
    return [ROOT / item for item in items]


def _existing(items):
    return [p for p in items if p.exists()]


def run(*, dry_run: bool = False):
    report = ROOT / 'reports' / 'engine' / 'cli_engine_audit_report.txt'

    engine_candidate = _existing(_paths([
        'engine/audio',
        'engine/creative_direction',
        'engine/audio_system',
        'engine/card_engine',
        'engine/combat',
        'engine/procedural_art',
        'engine/rendering',
        'engine/ui_framework',
        'game/art',
        'game/audio/audio_engine.py',
        'game/visual/portrait_pipeline.py',
        'game/visual/visual_engine.py',
        'game/core/paths.py',
        'tools/lib',
    ]))

    game_specific = _existing(_paths([
        'game/chakana_world',
        'game/content',
        'game/lore',
        'game/enemies',
        'game/relics',
        'game/map',
        'game/events',
        'game/narrative',
        'game/cards',
        'game/ui/screens',
        'game/data',
        'docs/canon',
        'assets/art_reference',
    ]))

    generated_output = _existing(_paths([
        'game/audio/generated',
        'game/visual/generated',
        'assets/staging',
        'reports/validation/scene_pipeline_samples',
        'reports/validation/art_candidate_staging',
    ]))

    reports = _existing(_paths([
        'reports/audit',
        'reports/art',
        'reports/cleanup',
        'reports/engine',
        'reports/master',
        'reports/qa',
        'reports/tools',
        'reports/validation',
        'reports/audits',
    ]))

    archive = _existing(_paths([
        'assets/_archive',
        'tools/archive',
        'docs/archive',
        'backups',
    ]))

    legacy = _existing(_paths([
        'reports/audits',
        'game/audio/audio_manifest.json',
        'game/data/bgm_manifest.json',
        'game/assets/tmp',
        'tools/build_chakana_master_from_reference.py',
        'tools/bootstrap_archon_curated_assets.py',
        'tools/curated_regen_cache_reset.py',
        'tools/check_card_coherence.py',
        'tools/check_combat_content_lock.py',
        'tools/check_deck_system.py',
        'tools/final_gameplay_integration_fix.py',
    ]))

    blockers = [
        'runtime still reads manifests directly from game/data and game/visual',
        'ui screens still mix reusable rendering and game-specific world flow',
        'legacy mirrors remain active for compatibility (audio_manifest/bgm_manifest)',
        'lore and cards are not yet normalized into engine-agnostic registries',
        'wrapper tools still coexist with chakana_studio.py and can confuse canonical entrypoint',
    ]

    lines = [
        'mode=engine_audit',
        f'dry_run={dry_run}',
        '',
        '[engine_candidate]',
    ]
    for p in engine_candidate:
        lines.append(f'- {rel(p)}')
    lines += ['', '[game_specific]']
    for p in game_specific:
        lines.append(f'- {rel(p)}')
    lines += ['', '[generated_output]']
    for p in generated_output:
        lines.append(f'- {rel(p)}')
    lines += ['', '[reports]']
    for p in reports:
        lines.append(f'- {rel(p)}')
    lines += ['', '[archive]']
    for p in archive:
        lines.append(f'- {rel(p)}')
    lines += ['', '[legacy]']
    for p in legacy:
        lines.append(f'- {rel(p)}')
    lines += ['', '[blocking_factors_for_extraction]']
    for b in blockers:
        lines.append(f'- {b}')
    lines += [
        '',
        '[recommended_extraction_sequence]',
        '- keep runtime stable and continue using mirrors',
        '- move manifest resolution behind a single adapter layer',
        '- export lore/card registries into structured data roots',
        '- separate reusable UI framework pieces from game/ui/screens',
        '- extract art/audio/rendering pipeline into engine runtime modules',
        '- leave Purple Wizard world content, lore and progression under game/',
        '',
        '[final_verdict]',
        'The repository is ready for incremental engine extraction, not for a hard split. The correct strategy remains mirror-first and adapter-first.',
    ]

    return write_text_report(report, 'chakana_studio engine audit', lines)
