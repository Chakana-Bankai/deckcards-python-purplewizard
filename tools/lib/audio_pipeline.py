import json
from .common import ROOT, write_text_report, rel


def run(*, dry_run: bool = False):
    report = ROOT / 'reports' / 'tools' / 'audio_audit_report.txt'
    manifests = [
        ROOT / 'data/manifests/audio_manifest.json',
        ROOT / 'game/data/audio_manifest.json',
        ROOT / 'game/data/audio_music_manifest.json',
    ]
    lines = ['mode=audio_audit', f'dry_run={dry_run}', '']
    for p in manifests:
        status = 'MISSING'
        extra = ''
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                status = 'OK'
                if isinstance(data, dict):
                    extra = f' keys={len(data.keys())}'
                    if 'entries' in data and isinstance(data['entries'], list):
                        extra += f' entries={len(data["entries"])}'
            except Exception:
                status = 'BROKEN'
        lines.append(f'- {rel(p)} => {status}{extra}')
    return write_text_report(report, 'chakana_studio audio audit', lines)
