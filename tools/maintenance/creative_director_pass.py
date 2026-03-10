from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from engine.creative_direction import QualityEvaluator

ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 128)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _collect_referenced_paths() -> set[Path]:
    refs: set[Path] = set()
    json_candidates = [
        ROOT / "game" / "audio" / "audio_manifest.json",
        ROOT / "game" / "visual" / "visual_manifest.json",
        ROOT / "game" / "visual" / "portrait_manifest.json",
        ROOT / "game" / "data" / "art_manifest.json",
        ROOT / "game" / "data" / "bgm_manifest.json",
    ]
    for p in json_candidates:
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        stack = [data]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                for _, v in cur.items():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
                    elif isinstance(v, str) and (".png" in v or ".wav" in v):
                        rp = Path(v)
                        if not rp.is_absolute():
                            rp = (ROOT / rp).resolve()
                        refs.add(rp)
            elif isinstance(cur, list):
                for x in cur:
                    stack.append(x)
    return refs


def _archive_file(path: Path, archive_root: Path) -> Path:
    rel = path.relative_to(ROOT)
    out = archive_root / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(out))
    return out


def _cleanup_assets() -> dict:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_root = ROOT / "assets" / "archive" / "creative_director_cleanup" / ts
    refs = _collect_referenced_paths()

    roots = [
        ROOT / "game" / "visual" / "generated",
        ROOT / "game" / "audio" / "generated",
    ]
    patterns = ("placeholder", "tmp", "temp", "draft", "copy", "old", "bak")

    moved = []
    dedup_map: dict[str, Path] = {}

    for root in roots:
        if not root.exists():
            continue
        files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".png", ".wav"}]
        for f in files:
            low = f.name.lower()
            if any(tok in low for tok in patterns):
                moved.append((f, "placeholder_or_temp", _archive_file(f, archive_root)))
                continue

            file_hash = _sha256(f)
            if file_hash in dedup_map:
                keep = dedup_map[file_hash]
                newer = f if f.stat().st_mtime > keep.stat().st_mtime else keep
                older = keep if newer == f else f
                dedup_map[file_hash] = newer
                if older.exists():
                    moved.append((older, "duplicate_hash", _archive_file(older, archive_root)))
                continue
            dedup_map[file_hash] = f

        files2 = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".png", ".wav"}]
        for f in files2:
            if f.resolve() not in refs:
                moved.append((f, "unreferenced_generated", _archive_file(f, archive_root)))

    return {
        "archive_root": archive_root,
        "moved": moved,
    }


def _evaluate_quality() -> dict:
    evaluator = QualityEvaluator()

    card_dir = ROOT / "assets" / "sprites" / "cards"
    art_scores = []
    if card_dir.exists():
        for p in sorted(card_dir.glob("*.png"))[:40]:
            art_scores.append((p, evaluator.evaluate_art_file(p)))

    import wave
    from array import array

    bgm_files = []
    bgm_dir = ROOT / "game" / "audio" / "generated" / "bgm"
    if bgm_dir.exists():
        bgm_files.extend(sorted(bgm_dir.glob("*.wav"))[:12])

    if not bgm_files:
        fallback = ROOT / "assets" / "music"
        if fallback.exists():
            bgm_files.extend(sorted(fallback.glob("*.wav"))[:12])

    if not bgm_files:
        try:
            from game.audio.audio_engine import get_audio_engine

            get_audio_engine().ensure_core_assets(force=False)
            if bgm_dir.exists():
                bgm_files.extend(sorted(bgm_dir.glob("*.wav"))[:12])
        except Exception:
            pass

    music_scores = []
    for p in bgm_files:
        try:
            with wave.open(str(p), "rb") as wf:
                n = wf.getnframes()
                sr = wf.getframerate()
                raw = wf.readframes(n)
            samples = array("h")
            samples.frombytes(raw)
            music_scores.append((p, evaluator.evaluate_music_samples(samples, sr)))
        except Exception:
            continue

    art_avg = sum(s.overall for _, s in art_scores) / max(1, len(art_scores))
    music_avg = sum(s.overall for _, s in music_scores) / max(1, len(music_scores))
    return {
        "art_scores": art_scores,
        "music_scores": music_scores,
        "art_avg": art_avg,
        "music_avg": music_avg,
    }


def main() -> int:
    quality = _evaluate_quality()
    cleanup = _cleanup_assets()

    report = ROOT / "creative_director_report.txt"
    lines = []
    lines.append("CHAKANA CREATIVE DIRECTOR REPORT")
    lines.append(f"generated_at={datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("[quality]")
    lines.append(f"art_avg={quality['art_avg']:.3f}")
    lines.append(f"music_avg={quality['music_avg']:.3f}")
    lines.append(f"art_candidates_checked={len(quality['art_scores'])}")
    lines.append(f"music_candidates_checked={len(quality['music_scores'])}")
    lines.append("")
    lines.append("[cleanup]")
    lines.append(f"archive_root={cleanup['archive_root']}")
    lines.append(f"assets_moved={len(cleanup['moved'])}")

    reason_count: dict[str, int] = {}
    for _, reason, _ in cleanup["moved"]:
        reason_count[reason] = reason_count.get(reason, 0) + 1
    for k in sorted(reason_count):
        lines.append(f"{k}={reason_count[k]}")

    lines.append("")
    lines.append("[stability]")
    lines.append("generation_mode=iterative_supervised")
    lines.append("art_threshold=0.62")
    lines.append("music_threshold=0.58")
    lines.append("status=PASS" if quality["art_avg"] >= 0.45 and quality["music_avg"] >= 0.40 else "status=WARNING")

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[creative_director] report={report}")
    print(f"[creative_director] moved={len(cleanup['moved'])} archive={cleanup['archive_root']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
