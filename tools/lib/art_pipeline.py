import json
from .common import ROOT, write_text_report


def run(*, dry_run: bool = False):
    report = ROOT / 'reports' / 'art' / 'art_pipeline_cli_audit_report.txt'
    manifest = ROOT / 'data' / 'manifests' / 'art_reference_manifest.json'
    card_dir = ROOT / 'game' / 'assets' / 'sprites' / 'cards'
    lines = ['mode=art_audit', f'dry_run={dry_run}', f'card_pngs={len(list(card_dir.glob("*.png")))}']
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding='utf-8'))
        lines += ['', f'reference_total={data.get("total_files", 0)}', 'reference_categories:']
        for k, v in sorted((data.get('categories') or {}).items()):
            lines.append(f'- {k}: {v}')
    else:
        lines += ['', 'manifest_missing=data/manifests/art_reference_manifest.json']
    return write_text_report(report, 'chakana_studio art audit', lines)
