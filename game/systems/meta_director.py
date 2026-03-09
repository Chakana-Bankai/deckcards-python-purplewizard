from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetaDirectorConfig:
    tutorial_combats_for_hiperborea: int = 3


class MetaDirector:
    """Lightweight run director for progression/content variety without combat rewrites."""

    def __init__(self, config: MetaDirectorConfig | None = None):
        self.config = config or MetaDirectorConfig()

    def ensure_state(self, run_state: dict | None) -> dict:
        if not isinstance(run_state, dict):
            return {}
        meta = run_state.setdefault("meta_director", {})
        meta.setdefault("recent_enemy_ids", [])
        meta.setdefault("recent_event_ids", [])
        meta.setdefault("recent_shop_card_ids", [])
        meta.setdefault("recent_pack_ids", [])
        meta.setdefault("visual_direction_tags", [])
        meta.setdefault("audio_direction_tags", [])
        return meta

    def remember(self, run_state: dict | None, key: str, value: str, cap: int = 6):
        meta = self.ensure_state(run_state)
        if not meta:
            return
        values = meta.setdefault(key, [])
        if not isinstance(values, list):
            values = []
            meta[key] = values
        v = str(value or "").strip()
        if not v:
            return
        values.append(v)
        if len(values) > int(cap):
            del values[0 : len(values) - int(cap)]

    def anti_repeat_choice(self, run_state: dict | None, rng, key: str, candidates: list[str], cap: int = 6) -> str | None:
        ids = [str(x) for x in list(candidates or []) if x]
        if not ids:
            return None
        meta = self.ensure_state(run_state)
        recent = list(meta.get(key, []) or []) if isinstance(meta, dict) else []
        fresh = [cid for cid in ids if cid not in recent]
        pool = fresh or ids
        picked = rng.choice(pool)
        self.remember(run_state, key, picked, cap=cap)
        return picked

    def set_unlock_target(self) -> int:
        return int(self.config.tutorial_combats_for_hiperborea)

    def hiperborea_chance(self, run_state: dict | None, level: int) -> float:
        if not isinstance(run_state, dict):
            return 0.0
        discovered = {str(x).strip().lower() for x in list(run_state.get("discovered_sets", []) or []) if x}
        if "hiperboria" not in discovered:
            return 0.0
        lvl = max(1, int(level or 1))
        if lvl < 3:
            return 0.0
        if lvl < 5:
            return 0.25
        return 0.45

    def register_direction_tags(self, run_state: dict | None, biome: str, node_type: str = ""):
        meta = self.ensure_state(run_state)
        if not meta:
            return
        b = str(biome or "").strip().lower()
        n = str(node_type or "").strip().lower()

        visual = [f"biome:{b}"] if b else []
        audio = [f"ctx:{n}"] if n else []
        if b:
            audio.append(f"biome:{b}")

        if b in {"ukhu", "ukhu_pacha", "ukupacha"}:
            visual.append("mood:underworld")
            audio.append("mood:dark")
        elif b in {"hanan", "hanan_pacha", "hananpacha"}:
            visual.append("mood:ascendant")
            audio.append("mood:ethereal")
        elif b in {"hiperborea", "polar"}:
            visual.append("civilization:hiperborea")
            audio.append("mood:ancient_ice")

        meta["visual_direction_tags"] = visual
        meta["audio_direction_tags"] = audio
