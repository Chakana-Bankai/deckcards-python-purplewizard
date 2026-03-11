from pathlib import Path

from .common import REPORTS, rel, write_text_report


def _bucket_count(bucket: str) -> int:
    folder = REPORTS / bucket
    return sum(1 for item in folder.rglob('*') if item.is_file()) if folder.exists() else 0


def _report_exists(path: Path) -> str:
    return f"{rel(path)}={'OK' if path.exists() else 'MISSING'}"


def _build_summary_report(*, dry_run: bool) -> Path:
    report = REPORTS / 'master' / 'chakana_reports_build.txt'
    buckets = ['audit', 'art', 'qa', 'tools', 'engine', 'validation', 'cleanup', 'master']
    lines = ['mode=reports_build', f'dry_run={dry_run}', '']
    for bucket in buckets:
        lines.append(f'- {bucket}: {_bucket_count(bucket)}')
    return write_text_report(report, 'chakana_studio reports build', lines)


def _build_master_consolidation_report(*, dry_run: bool) -> Path:
    report = REPORTS / 'master' / 'chakana_cli_master_consolidation_report.txt'
    files = [
        REPORTS / 'audit' / 'repository_reality_audit.txt',
        REPORTS / 'audit' / 'manifest_recovery_report.txt',
        REPORTS / 'art' / 'art_references_integration_report.txt',
        REPORTS / 'tools' / 'cli_master_creation_report.txt',
        REPORTS / 'tools' / 'tools_consolidation_report.txt',
        REPORTS / 'qa' / 'cli_validation_report.txt',
        REPORTS / 'engine' / 'chakana_engine_readiness_report.txt',
        REPORTS / 'engine' / 'cli_engine_audit_report.txt',
    ]
    lines = [
        'mode=chakana_cli_master_consolidation',
        f'dry_run={dry_run}',
        '',
        '1. What was found broken?',
        '- missing canonical buckets before consolidation: data/manifests/, reports/qa, reports/art, reports/engine, reports/master',
        '- runtime/tooling references expected assets/art_references and assets/archive but the real canonical roots are assets/art_reference and assets/_archive',
        '- auxiliary runtime manifests were missing in game/data: art_manifest_avatar.json, art_manifest_enemies.json, art_manifest_guides.json, biome_manifest.json',
        '- tooling duplication remained high across tools/, tools/qa/, tools/assets/ and tools/maintenance/',
        '',
        '2. What manifests were missing or repaired?',
        '- recovered runtime manifests in game/data: art_manifest_avatar.json, art_manifest_enemies.json, art_manifest_guides.json, biome_manifest.json',
        '- created canonical mirrors in data/manifests: art_manifest.json, audio_manifest.json, card_manifest.json, codex_manifest.json, art_reference_manifest.json',
        '- preserved compatibility mirrors instead of forcing a risky runtime migration',
        '',
        '3. What tools are now canonical?',
        '- preferred entrypoint: tools/chakana_studio.py',
        '- preferred module layer: tools/lib/*',
        '- preferred health checks: project-audit, manifest-audit, art-audit, audio-audit, qa-smoke, cli-validate, engine-audit, reports-build',
        '',
        '4. What was archived?',
        '- no aggressive archival was executed in this pass; wrappers and legacy entrypoints were intentionally preserved for compatibility',
        '- documented archive policy in tools/archive/README.md and canonical archive roots in assets/_archive and backups/',
        '',
        '5. What commands can now be run locally?',
        '- python tools/chakana_studio.py project-audit',
        '- python tools/chakana_studio.py sanitize --dry-run',
        '- python tools/chakana_studio.py duplication-check --dry-run',
        '- python tools/chakana_studio.py manifest-audit --dry-run',
        '- python tools/chakana_studio.py art-audit --dry-run',
        '- python tools/chakana_studio.py audio-audit --dry-run',
        '- python tools/chakana_studio.py qa-smoke --dry-run',
        '- python tools/chakana_studio.py cli-validate --dry-run',
        '- python tools/chakana_studio.py engine-audit --dry-run',
        '- python tools/chakana_studio.py reports-build',
        '',
        '6. What is the next recommended step before resuming art generation?',
        '- use chakana_studio as the only preferred operator entrypoint',
        '- finish lore structuring into data/lore/*.json',
        '- add an ID registry/mapping layer before any card-id renaming',
        '- then resume art iteration using the now-stable art_reference -> scene_spec -> staging -> validation -> production flow',
        '',
        'source_reports:',
    ]
    lines.extend([f'- {_report_exists(path)}' for path in files])
    return write_text_report(report, 'chakana CLI master consolidation report', lines)


def run(*, dry_run: bool = False):
    summary_report = _build_summary_report(dry_run=dry_run)
    master_report = _build_master_consolidation_report(dry_run=dry_run)
    return master_report if master_report.exists() else summary_report
