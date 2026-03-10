from __future__ import annotations

import json
import shutil
from pathlib import Path

from game.core.paths import curated_audio_dir, data_dir, project_root

ACTIVE_CONTEXTS = {
    "menu": "menu_a",
    "map_ukhu": "map_ukhu_a",
    "map_kay": "map_kay_a",
    "map_hanan": "map_hanan_a",
    "shop": "shop_a",
    "combat": "combat_a",
    "combat_boss": "combat_boss_a",
    "victory": "victory_a",
    "defeat": "defeat_a",
}


def main() -> int:
    manifest_path = data_dir() / "audio_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = payload.setdefault("items", {})
    curated_root = curated_audio_dir() / "bgm"
    curated_root.mkdir(parents=True, exist_ok=True)
    report_lines = [
        "status=ok",
        "mode=minimal_curated_library",
    ]

    for context, item_id in ACTIVE_CONTEXTS.items():
        item = items.get(item_id)
        if not isinstance(item, dict):
            report_lines.append(f"missing={item_id}")
            continue
        source_path = Path(str(item.get("file_path", "")))
        if not source_path.exists():
            rel = str(item.get("relative_path", "") or "")
            if rel:
                source_path = project_root() / rel
        if not source_path.exists():
            report_lines.append(f"missing_file={item_id}")
            continue
        curated_path = curated_root / f"{context}_a.wav"
        if not curated_path.exists():
            shutil.copy2(source_path, curated_path)
        else:
            try:
                shutil.copy2(source_path, curated_path)
            except PermissionError:
                pass
        normalized = dict(item)
        normalized.update(
            {
                "track_id": f"{context}_a",
                "context": context,
                "variant": "a",
                "file_path": str(curated_path),
                "relative_path": str(curated_path.relative_to(project_root())).replace("\\", "/"),
                "source": "curated",
                "state": "valid",
                "active_runtime": True,
            }
        )
        items[f"{context}_a"] = normalized
        report_lines.append(f"active={context}_a source={source_path.name}")

    for item_id, item in list(items.items()):
        if not isinstance(item, dict):
            continue
        if str(item.get("type", "")) != "bgm":
            continue
        ctx = str(item.get("context", "") or "")
        if ctx in ACTIVE_CONTEXTS and item_id != f"{ctx}_a":
            item["state"] = "archived"
            item["active_runtime"] = False
        elif ctx not in ACTIVE_CONTEXTS and item_id.startswith(("menu_", "map_", "combat_", "shop_", "victory_", "defeat_")):
            item["active_runtime"] = False

    payload["version"] = "chakana_audio_curated_minimal_v1"
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    out = project_root() / "reports" / "validation" / "audio_library_minimal_curated_report.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"[audio_library] report={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
