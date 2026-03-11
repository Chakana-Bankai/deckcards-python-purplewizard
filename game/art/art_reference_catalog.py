from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from game.core.paths import art_reference_dir

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp'}

CATEGORY_PATHS = {
    'subjects': [
        'subjects/solar_warriors',
        'subjects/guides',
        'subjects/archons',
        'subjects/beasts',
        'silhouettes/characters',
        'silhouettes/creatures',
        'silhouettes/poses',
    ],
    'enemies': [
        'subjects/archons',
        'silhouettes/creatures',
    ],
    'creatures': [
        'subjects/beasts',
        'silhouettes/creatures',
    ],
    'weapons': [
        'weapons',
        'weapons/swords',
        'weapons/spears',
        'weapons/staffs',
        'weapons/relics',
        'silhouettes/weapons',
    ],
    'environments': [
        'environments/mountains',
        'environments/forest',
        'environments/ruins',
        'environments/sea',
        'environments/sky',
        'environments/temples',
        'environments/void',
    ],
    'symbols': [
        'symbols/chakana',
        'symbols/runes',
        'symbols/sacred_geometry',
    ],
    'palettes_mood': [
        'palettes/archon',
        'palettes/hyperborea',
        'palettes/solar',
        'lighting/dark',
        'lighting/sunrise',
        'lighting/sunset',
    ],
}

LEGACY_CATEGORY_ALIASES = {
    'fantasy_landscapes': ['environments'],
    'ancient_architecture': ['environments'],
    'andean_mythology': ['subjects', 'symbols'],
    'biblical_archetypes': ['subjects', 'symbols'],
    'chakana_symbols': ['symbols'],
    'sacred_geometry': ['symbols'],
    'characters_subjects': ['subjects'],
    'characters_subjets': ['subjects'],
    'weapons_relics': ['weapons'],
    'palette_mood': ['palettes_mood'],
}


@dataclass(frozen=True)
class ArtReferenceEntry:
    path: Path
    canonical_category: str
    subgroup: str


def _dedupe_keep_order(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def expand_categories(categories: list[str]) -> list[str]:
    expanded: list[str] = []
    for category in categories:
        cat = str(category or '').strip().lower()
        if not cat:
            continue
        expanded.extend(LEGACY_CATEGORY_ALIASES.get(cat, [cat]))
    return _dedupe_keep_order(expanded)


def iter_category_entries(root: Path | None = None, category: str = '') -> list[ArtReferenceEntry]:
    base = Path(root or art_reference_dir())
    category = str(category or '').strip().lower()
    rel_paths = CATEGORY_PATHS.get(category, [category] if category else [])
    entries: list[ArtReferenceEntry] = []
    seen: set[Path] = set()
    for rel in rel_paths:
        folder = base / rel
        if not folder.exists():
            continue
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
                continue
            if path in seen:
                continue
            seen.add(path)
            subgroup = str(path.parent.relative_to(base)).replace('\\', '/')
            entries.append(ArtReferenceEntry(path=path, canonical_category=category or 'unknown', subgroup=subgroup))
    return entries


def build_reference_manifest(root: Path | None = None) -> dict:
    base = Path(root or art_reference_dir())
    categories: dict[str, dict] = {}
    total = 0
    for category in CATEGORY_PATHS:
        entries = iter_category_entries(base, category)
        total += len(entries)
        groups: dict[str, int] = {}
        for entry in entries:
            groups[entry.subgroup] = groups.get(entry.subgroup, 0) + 1
        categories[category] = {
            'count': len(entries),
            'groups': groups,
            'sample_files': [entry.path.name for entry in entries[:8]],
        }
    return {
        'version': 'chakana_art_reference_manifest_v1',
        'root': str(base),
        'total_files': total,
        'categories': categories,
        'pipeline_flow': [
            'art_references',
            'scene_specs',
            'staging',
            'validation',
            'production',
        ],
        'legacy_aliases': LEGACY_CATEGORY_ALIASES,
    }
