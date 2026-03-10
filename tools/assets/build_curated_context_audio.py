from __future__ import annotations

import argparse
import shutil

from game.audio.audio_engine import ContextSpec, get_audio_engine
from game.core.paths import curated_audio_dir, project_root


CURATED_PROFILES = {
    "menu": ContextSpec("orchestral hopeful mystic", ("a",), 142.0, 0.05, 0.58, 0.10),
    "map_kay": ContextSpec("pilgrimage exploration warm", ("a",), 132.0, 0.08, 0.52, 0.20),
    "shop": ContextSpec("ritual sanctuary intimate", ("a",), 118.0, 0.05, 0.48, 0.12),
    "combat": ContextSpec("tactical orchestral pulse", ("a",), 126.0, 0.15, 0.56, 0.58),
    "combat_boss": ContextSpec("epic archon ceremonial", ("a",), 154.0, 0.22, 0.62, 0.90),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye soundtrack curado por contexto fuera del runtime.")
    parser.add_argument("--contexts", nargs="*", default=list(CURATED_PROFILES.keys()))
    args = parser.parse_args()

    engine = get_audio_engine()
    target_contexts = [c for c in args.contexts if c in CURATED_PROFILES]
    curated_root = curated_audio_dir() / "bgm"
    curated_root.mkdir(parents=True, exist_ok=True)
    report_lines = ["status=ok"]

    for ctx in target_contexts:
        spec = CURATED_PROFILES[ctx]
        engine.context_specs[ctx] = spec
        for variant in spec.variants:
            generated = engine._ensure_bgm_variant(ctx, variant, force=True)
            curated_path = curated_root / f"{ctx}_{variant}.wav"
            shutil.copy2(generated, curated_path)
            engine._register_item(
                f"{ctx}_{variant}",
                item_type="bgm",
                context=ctx,
                variant=variant,
                seed=engine._stable_seed(f"curated:{ctx}:{variant}"),
                file_path=curated_path,
                source="curated",
            )
            report_lines.append(f"{ctx}_{variant}={curated_path.name}")

    out = project_root() / "reports" / "validation" / "curated_context_audio_report.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"[curated_audio] report={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
