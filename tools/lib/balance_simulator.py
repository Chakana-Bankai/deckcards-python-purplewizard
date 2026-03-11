import json
from collections import Counter
from .common import ROOT, write_text_report


def _load_cards(path):
    raw = json.loads(path.read_text(encoding='utf-8-sig'))
    return raw if isinstance(raw, list) else raw.get('cards', [])


def run(*, dry_run: bool = False):
    report = ROOT / 'reports' / 'tools' / 'balance_sim_report.txt'
    files = [
        ROOT / 'game/data/cards.json',
        ROOT / 'game/data/cards_hiperboria.json',
        ROOT / 'game/data/cards_arconte.json',
    ]
    cards = []
    for p in files:
        cards.extend(_load_cards(p))
    rarity = Counter(str(c.get('rarity', 'unknown')) for c in cards if isinstance(c, dict))
    arche = Counter(str(c.get('archetype', 'unknown')) for c in cards if isinstance(c, dict))
    lines = ['mode=balance_sim', f'dry_run={dry_run}', f'total_cards={len(cards)}', '', 'rarity:']
    for k, v in sorted(rarity.items()):
        lines.append(f'- {k}: {v}')
    lines += ['', 'archetype:']
    for k, v in sorted(arche.items()):
        lines.append(f'- {k}: {v}')
    return write_text_report(report, 'chakana_studio balance sim', lines)
