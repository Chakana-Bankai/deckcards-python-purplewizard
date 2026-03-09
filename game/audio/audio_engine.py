from __future__ import annotations

import json
import math
import time
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from random import Random

import pygame

from engine.creative_direction import CreativeMusicDirector
from game.core.paths import assets_dir


@dataclass(frozen=True)
class ContextSpec:
    mood: str
    variants: tuple[str, ...]
    seconds: float
    pulse: float
    brightness: float
    tension: float


class AudioEngine:
    """Procedural audio engine with caching and context-aware playback."""

    VERSION = "chakana_audio_v6"
    SAMPLE_RATE = 32000

    def __init__(self):
        root = Path(__file__).resolve().parent
        self.audio_root = root
        self.generated_root = root / "generated"
        self.bgm_dir = self.generated_root / "bgm"
        self.sfx_dir = self.generated_root / "sfx"
        self.stingers_dir = self.generated_root / "stingers"
        self.studio_dir = self.generated_root / "studio"
        self.manifest_path = root / "audio_manifest.json"
        self.curated_audio_root = assets_dir() / "curated" / "audio"
        self._ensure_dirs()

        # Compact context set: fewer tracks, clearer identity.
        self.context_specs: dict[str, ContextSpec] = {
            "menu": ContextSpec("mystical calm", ("a", "b"), 116.0, 0.07, 0.38, 0.15),
            "map_ukhu": ContextSpec("exploration ambient", ("a", "b"), 108.0, 0.10, 0.34, 0.21),
            "map_kay": ContextSpec("exploration ambient", ("a", "b"), 108.0, 0.11, 0.40, 0.25),
            "map_hanan": ContextSpec("exploration ambient", ("a", "b"), 110.0, 0.12, 0.48, 0.31),
            "combat": ContextSpec("tense pulse", ("a", "b"), 86.0, 0.18, 0.52, 0.60),
            "combat_elite": ContextSpec("strong percussion", ("a", "b"), 92.0, 0.22, 0.56, 0.72),
            "combat_boss": ContextSpec("ceremonial epic", ("a", "b"), 102.0, 0.27, 0.60, 0.88),
            "shop": ContextSpec("calm ritual", ("a", "b"), 84.0, 0.07, 0.44, 0.20),
            "victory": ContextSpec("uplift", ("a", "b"), 32.0, 0.14, 0.60, 0.20),
            "defeat": ContextSpec("falling echo", ("a", "b"), 34.0, 0.08, 0.26, 0.40),
        }
        self.context_alias = {
            "map_kaypacha": "map_kay",
            "map_fractura_chakana": "map_hanan",
            "map_fractura": "map_hanan",
            "map_forest": "map_ukhu",
            "map_umbral": "map_ukhu",
            "combat_ukhu": "combat",
            "combat_kaypacha": "combat",
            "combat_hanan": "combat_elite",
            "combat_fractura_chakana": "combat_boss",
            "combat_fractura": "combat_boss",
            "combat_forest": "combat_elite",
            "combat_umbral": "combat_elite",
            "boss": "combat_boss",
            "events": "shop",
            "event": "shop",
            "lore": "shop",
            "sanctuary": "shop",
            "reward": "shop",
            "chest": "victory",
            "menu_main": "menu",
            "map_exploration": "map_kay",
            "shop_ritual": "shop",
            "combat_standard": "combat",
            "boss_battle": "combat_boss",
            "reward_reveal": "victory",
        }

        self.stingers = {
            "combat_start": 1.25,
            "elite_encounter": 1.45,
            "boss_reveal": 2.2,
            "victory": 1.8,
            "defeat": 1.8,
            "level_up": 1.3,
            "relic_gain": 1.5,
            "pack_open": 1.5,
            "seal_ready": 1.2,
            "harmony_ready": 1.3,
            "studio_intro": 3.8,
        }
        self.sfx_defs = {
            "card_play": 0.22,
            "card_invalid": 0.15,
            "button_click": 0.11,
            "gold_gain": 0.16,
            "xp_gain": 0.16,
            "damage_hit": 0.18,
            "heal": 0.22,
            "seal_activate": 0.28,
            "relic_pick": 0.20,
        }

        self._manifest = self._load_manifest()
        self._last_variant_by_context: dict[str, str] = {}
        self._sound_cache: dict[str, pygame.mixer.Sound] = {}
        self._sfx_cooldowns: dict[str, int] = {}
        self._logged_once: set[str] = set()
        self._music_volume = 0.5
        self._sfx_volume = 0.7
        self._muted = False
        self._stinger_channel = None
        self._ui_sfx_channel = None
        self._impact_channel = None
        self.current_context = "-"
        self.current_variant = "-"
        self.current_path = "-"
        self.status = "stopped"
        self._init_channels()
        self._creative_music_director = CreativeMusicDirector()

    def _ensure_dirs(self):
        for d in (self.generated_root, self.bgm_dir, self.sfx_dir, self.stingers_dir, self.studio_dir):
            d.mkdir(parents=True, exist_ok=True)

    def _init_channels(self):
        try:
            if not pygame.mixer.get_init():
                return
            pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
            self._stinger_channel = pygame.mixer.Channel(1)
            self._ui_sfx_channel = pygame.mixer.Channel(2)
            self._impact_channel = pygame.mixer.Channel(3)
        except Exception:
            self._stinger_channel = None
            self._ui_sfx_channel = None
            self._impact_channel = None

    def _log_once(self, key: str, text: str):
        if key in self._logged_once:
            return
        self._logged_once.add(key)
        print(text)

    def _load_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {"version": self.VERSION, "generated_at": int(time.time()), "items": {}}
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("version", self.VERSION)
                data.setdefault("generated_at", int(time.time()))
                data.setdefault("items", {})
                return data
        except Exception:
            pass
        return {"version": self.VERSION, "generated_at": int(time.time()), "items": {}}

    def _save_manifest(self):
        self._manifest["version"] = self.VERSION
        self._manifest["generated_at"] = int(time.time())
        self.manifest_path.write_text(json.dumps(self._manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    def _stable_seed(self, key: str) -> int:
        return abs(hash(f"{self.VERSION}:{key}")) % (2**31 - 1)

    def _write_wave(self, path: Path, samples: array):
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(samples.tobytes())

    def _triangle(self, phase: float) -> float:
        v = (phase / (2 * math.pi)) % 1.0
        return 4.0 * abs(v - 0.5) - 1.0

    def _music_samples(self, ctx: str, variant: str, seconds: float, seed_hint: int = 0) -> array:
        spec = self.context_specs[ctx]
        seed = self._stable_seed(f"bgm:{ctx}:{variant}:{int(seed_hint)}")
        rng = Random(seed)
        total = max(1, int(seconds * self.SAMPLE_RATE))
        samples = array("h")

        # Long-form harmonic progression + evolving motif to avoid repetitive bip loops.
        roots = [43.65, 49.0, 55.0, 61.74, 65.41]
        rng.shuffle(roots)
        section_sec = max(10.0, seconds / 6.0)
        motif_step = (0.62 if ("menu" in ctx or "shop" in ctx) else max(0.34, 0.44 - spec.pulse * 0.12))
        motif = [0, 2, 4, 2, 5, 4, 2, 0]

        prev = 0.0
        prev2 = 0.0
        for i in range(total):
            t = i / self.SAMPLE_RATE
            sec_idx = int(t / section_sec) % len(roots)
            root = roots[sec_idx]
            chord = (root, root * 1.20, root * 1.5)

            slow_lfo = 0.5 + 0.5 * math.sin(2 * math.pi * 0.05 * t + 0.6)
            pulse_env = 0.76 + 0.24 * math.sin(2 * math.pi * (0.10 + spec.pulse * 0.16) * t)

            mot_i = int(t / motif_step) % len(motif)
            melody_freq = root * (2 ** (motif[mot_i] / 12.0))

            pad = (
                0.30 * math.sin(2 * math.pi * chord[0] * t)
                + 0.23 * math.sin(2 * math.pi * chord[1] * t + 0.6)
                + 0.16 * math.sin(2 * math.pi * chord[2] * t + 1.4)
            )
            bass = 0.24 * math.sin(2 * math.pi * (root * 0.5) * t + 0.15 * math.sin(t * 0.18))
            motif_voice = 0.12 * math.sin(2 * math.pi * melody_freq * t + 0.22 * math.sin(t * 0.45))
            shimmer = 0.05 * math.sin(2 * math.pi * (root * 1.33) * t + 0.3)

            # Context accents (boss/combat get punch, menu/shop remain calm).
            accent = 0.0
            if "boss" in ctx:
                accent = 0.16 * math.sin(2 * math.pi * (root * 0.72) * t + 0.35 * math.sin(t * 0.8))
            elif "combat" in ctx:
                accent = 0.10 * math.sin(2 * math.pi * (root * 0.95) * t + 0.26 * math.sin(t * 0.62))
            elif "menu" in ctx or "shop" in ctx:
                accent = 0.04 * math.sin(2 * math.pi * (root * 1.25) * t + 1.1)

            noise = 0.0012 * math.sin(2 * math.pi * (42 + 8 * spec.brightness) * t + 0.06 * math.sin(t * 0.7))
            x = ((pad * pulse_env) + bass + motif_voice + shimmer + accent + noise) * (0.86 + 0.14 * slow_lfo)

            fade_in = min(1.0, t / 2.0)
            fade_out = min(1.0, (seconds - t) / 1.7)
            amp = max(0.0, min(1.0, fade_in * fade_out))

            # Two-stage smoothing to avoid sharp beep-like edges and whistle feel.
            x = 0.86 * x + 0.14 * prev
            x = 0.90 * x + 0.10 * prev2
            prev2 = prev
            prev = x
            y = int(max(-1.0, min(1.0, x * amp * 0.86)) * 32767)
            samples.append(y)
        return samples

    def _tone_burst(self, freq: float, seconds: float, attack: float = 0.01, decay: float = 0.2) -> array:
        total = max(1, int(seconds * self.SAMPLE_RATE))
        samples = array("h")
        for i in range(total):
            t = i / self.SAMPLE_RATE
            env_a = min(1.0, t / max(0.001, attack))
            env_d = max(0.0, 1.0 - (t / max(0.01, seconds)) ** max(0.2, decay))
            env = env_a * env_d
            x = (
                0.72 * math.sin(2 * math.pi * freq * t)
                + 0.24 * math.sin(2 * math.pi * (freq * 2.0) * t + 0.2)
                + 0.12 * self._triangle(2 * math.pi * (freq * 0.5) * t)
            )
            samples.append(int(max(-1.0, min(1.0, x * env * 0.82)) * 32767))
        return samples

    def _stinger_samples(self, name: str, seconds: float) -> array:
        if name == "studio_intro":
            total = max(1, int(seconds * self.SAMPLE_RATE))
            out = array("h")
            for i in range(total):
                t = i / self.SAMPLE_RATE
                env = min(1.0, t / 0.45) * max(0.0, min(1.0, (seconds - t) / 1.0))
                bell = math.sin(2 * math.pi * (390 + 16 * math.sin(t * 0.7)) * t) * math.exp(-t * 0.6)
                cosmic = math.sin(2 * math.pi * (110 + 34 * t) * t + 0.3 * math.sin(t * 1.9))
                chord = math.sin(2 * math.pi * 248 * t) + 0.55 * math.sin(2 * math.pi * 312 * t)
                x = 0.40 * bell + 0.30 * cosmic + (0.24 * chord if t > seconds - 1.1 else 0.0)
                out.append(int(max(-1.0, min(1.0, x * env * 0.86)) * 32767))
            return out

        # Multi-tone short phrases to avoid single-note "bip" feel.
        phrase = {
            "combat_start": (220.0, 294.0, 330.0),
            "elite_encounter": (196.0, 246.0, 294.0),
            "boss_reveal": (146.0, 174.0, 220.0),
            "victory": (312.0, 392.0, 468.0),
            "defeat": (166.0, 146.0, 118.0),
            "level_up": (392.0, 468.0, 524.0),
            "relic_gain": (358.0, 426.0, 512.0),
            "pack_open": (268.0, 320.0, 402.0),
            "seal_ready": (420.0, 374.0, 452.0),
            "harmony_ready": (452.0, 508.0, 560.0),
        }.get(name, (280.0, 340.0, 410.0))

        total = max(1, int(seconds * self.SAMPLE_RATE))
        out = array("h")
        seg = max(1, total // len(phrase))
        for i in range(total):
            t = i / self.SAMPLE_RATE
            idx = min(len(phrase) - 1, i // seg)
            f = phrase[idx]
            env = min(1.0, t / 0.02) * max(0.0, min(1.0, (seconds - t) / 0.18))
            x = (
                0.62 * math.sin(2 * math.pi * f * t)
                + 0.20 * math.sin(2 * math.pi * (f * 1.5) * t + 0.2)
                + 0.10 * self._triangle(2 * math.pi * (f * 0.5) * t)
            )
            out.append(int(max(-1.0, min(1.0, x * env * 0.82)) * 32767))
        return out

    def _sfx_samples(self, name: str, seconds: float) -> array:
        base = {
            "card_play": 280.0,
            "card_invalid": 150.0,
            "button_click": 320.0,
            "gold_gain": 360.0,
            "xp_gain": 396.0,
            "damage_hit": 96.0,
            "heal": 246.0,
            "seal_activate": 186.0,
            "relic_pick": 330.0,
        }.get(name, 260.0)
        # Softer tonal center + tiny motion to avoid pure beep character.
        total = max(1, int(seconds * self.SAMPLE_RATE))
        samples = array("h")
        for i in range(total):
            t = i / self.SAMPLE_RATE
            env = min(1.0, t / 0.006) * max(0.0, min(1.0, (seconds - t) / 0.09))
            harmonic = 0.62 * math.sin(2 * math.pi * base * t) + 0.22 * math.sin(2 * math.pi * (base * 1.42) * t + 0.3)
            body = 0.10 * self._triangle(2 * math.pi * (base * 0.62) * t)
            noise = 0.03 * math.sin(2 * math.pi * (46 + base * 0.04) * t)
            x = harmonic + body + noise
            samples.append(int(max(-1.0, min(1.0, x * env * 0.82)) * 32767))
        return samples

    def _curated_item_path(self, item_id: str, expected_type: str) -> Path | None:
        root = self.curated_audio_root
        if expected_type == "bgm":
            if "_" in item_id:
                ctx, var = item_id.rsplit("_", 1)
                p = root / "bgm" / f"{ctx}_{var}.wav"
                if p.exists():
                    return p
                p2 = root / "bgm" / f"{ctx}.wav"
                if p2.exists():
                    return p2
            p3 = root / "bgm" / f"{item_id}.wav"
            return p3 if p3.exists() else None
        if expected_type == "stinger":
            nm = item_id.replace("stinger_", "", 1)
            for p in (root / "stingers" / f"{nm}.wav", root / "studio" / f"{nm}.wav"):
                if p.exists():
                    return p
            return None
        if expected_type == "sfx":
            nm = item_id.replace("sfx_", "", 1)
            p = root / "sfx" / f"{nm}.wav"
            return p if p.exists() else None
        return None

    def _source_from_path(self, path: Path) -> str:
        sp = str(path).replace("\\", "/").lower()
        return "curated" if "/assets/curated/" in sp else "generated"

    def _default_item_path(self, item_id: str, expected_type: str) -> Path:
        if expected_type == "bgm":
            return self.bgm_dir / f"{item_id}.wav"
        if expected_type == "stinger":
            name = item_id.replace("stinger_", "", 1)
            folder = self.studio_dir if name == "studio_intro" else self.stingers_dir
            return folder / f"{name}.wav"
        if expected_type == "sfx":
            name = item_id.replace("sfx_", "", 1)
            return self.sfx_dir / f"{name}.wav"
        return self.generated_root / f"{item_id}.wav"

    def _item_ok(self, item_id: str, expected_type: str) -> Path | None:
        curated = self._curated_item_path(item_id, expected_type)
        if curated is not None:
            return curated

        items = self._manifest.get("items", {})
        meta = items.get(item_id, {}) if isinstance(items, dict) else {}
        if not isinstance(meta, dict) or meta.get("type") != expected_type:
            return None
        if str(meta.get("version", "")) != self.VERSION:
            return None
        p = Path(str(meta.get("file_path", ""))).expanduser()
        if p.exists():
            return p
        return None

    def _register_item(self, item_id: str, *, item_type: str, context: str, variant: str, seed: int, file_path: Path, source: str = "generated"):
        items = self._manifest.setdefault("items", {})
        items[item_id] = {
            "track_id": item_id,
            "type": item_type,
            "context": context,
            "variant": variant,
            "seed": int(seed),
            "file_path": str(file_path),
            "generation_date": int(time.time()),
            "version": self.VERSION,
            "state": "valid",
            "source": str(source or "generated"),
        }
        self._save_manifest()

    def _ensure_bgm_variant(self, ctx: str, variant: str, force: bool = False) -> Path:
        item_id = f"{ctx}_{variant}"
        cached = None if force else self._item_ok(item_id, "bgm")
        if cached is not None:
            if item_id not in self._manifest.get("items", {}):
                seed = self._stable_seed(f"bgm:{item_id}")
                self._register_item(item_id, item_type="bgm", context=ctx, variant=variant, seed=seed, file_path=cached, source=self._source_from_path(cached))
            return cached
        spec = self.context_specs[ctx]
        seed = self._stable_seed(f"bgm:{item_id}")
        path = self.bgm_dir / f"{item_id}.wav"
        best_samples, meta = self._creative_music_director.evolve_samples(
            context=ctx,
            variant=variant,
            seconds=spec.seconds,
            sample_rate=self.SAMPLE_RATE,
            generate_samples_fn=lambda c, v, s, sh: self._music_samples(c, v, s, sh),
            threshold=0.58,
        )
        self._write_wave(path, best_samples)
        self._register_item(item_id, item_type="bgm", context=ctx, variant=variant, seed=int(meta.get("seed", seed)), file_path=path, source="generated")
        print(f"[Audio] generated: {item_id}")
        return path

    def _ensure_stinger(self, name: str, force: bool = False) -> Path:
        item_id = f"stinger_{name}"
        cached = None if force else self._item_ok(item_id, "stinger")
        if cached is not None:
            if item_id not in self._manifest.get("items", {}):
                seed = self._stable_seed(item_id)
                self._register_item(item_id, item_type="stinger", context=name, variant="a", seed=seed, file_path=cached, source=self._source_from_path(cached))
            return cached
        seconds = float(self.stingers.get(name, 0.8))
        seed = self._stable_seed(item_id)
        path = (self.studio_dir if name == "studio_intro" else self.stingers_dir) / f"{name}.wav"
        self._write_wave(path, self._stinger_samples(name, seconds))
        self._register_item(item_id, item_type="stinger", context=name, variant="a", seed=seed, file_path=path, source="generated")
        print(f"[Audio] generated: {item_id}")
        return path

    def _ensure_sfx(self, name: str, force: bool = False) -> Path:
        item_id = f"sfx_{name}"
        cached = None if force else self._item_ok(item_id, "sfx")
        if cached is not None:
            if item_id not in self._manifest.get("items", {}):
                seed = self._stable_seed(item_id)
                self._register_item(item_id, item_type="sfx", context=name, variant="a", seed=seed, file_path=cached, source=self._source_from_path(cached))
            return cached
        seconds = float(self.sfx_defs.get(name, 0.14))
        seed = self._stable_seed(item_id)
        path = self.sfx_dir / f"{name}.wav"
        self._write_wave(path, self._sfx_samples(name, seconds))
        self._register_item(item_id, item_type="sfx", context=name, variant="a", seed=seed, file_path=path, source="generated")
        print(f"[Audio] generated: {item_id}")
        return path

    def _prune_manifest(self):
        items = self._manifest.get("items", {})
        if not isinstance(items, dict) or not items:
            return
        valid_ids = set()
        for ctx, spec in self.context_specs.items():
            for var in spec.variants:
                valid_ids.add(f"{ctx}_{var}")
        for name in self.stingers:
            valid_ids.add(f"stinger_{name}")
        for name in self.sfx_defs:
            valid_ids.add(f"sfx_{name}")

        changed = False
        for item_id in list(items.keys()):
            meta = items.get(item_id, {})
            p = Path(str((meta or {}).get("file_path", "")))
            if item_id not in valid_ids or not p.exists():
                del items[item_id]
                changed = True
        if changed:
            self._save_manifest()

    def ensure_core_assets(self, force: bool = False) -> dict:
        self._prune_manifest()
        for ctx, spec in self.context_specs.items():
            for var in spec.variants:
                self._ensure_bgm_variant(ctx, var, force=force)
        for name in self.stingers:
            self._ensure_stinger(name, force=force)
        for name in self.sfx_defs:
            self._ensure_sfx(name, force=force)
        return self._manifest

    def set_music_volume(self, value: float):
        self._music_volume = max(0.0, min(1.0, float(value)))
        try:
            pygame.mixer.music.set_volume(0.0 if self._muted else self._music_volume)
        except Exception:
            pass

    def set_sfx_volume(self, value: float):
        self._sfx_volume = max(0.0, min(1.0, float(value)))

    def set_muted(self, muted: bool):
        self._muted = bool(muted)
        try:
            pygame.mixer.music.set_volume(0.0 if self._muted else self._music_volume)
        except Exception:
            pass

    def _normalize_context(self, context: str) -> str:
        key = str(context or "menu").lower()
        key = self.context_alias.get(key, key)
        return key if key in self.context_specs else "menu"

    def _choose_variant(self, context: str) -> str:
        variants = self.context_specs[context].variants
        if len(variants) <= 1:
            return variants[0]
        last = self._last_variant_by_context.get(context)
        opts = [v for v in variants if v != last]
        choice = opts[Random().randint(0, len(opts) - 1)] if opts else variants[0]
        self._last_variant_by_context[context] = choice
        return choice

    def play_context(self, context: str):
        ctx = self._normalize_context(context)
        var = self._choose_variant(ctx)
        path = self._ensure_bgm_variant(ctx, var, force=False)
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(0.0 if self._muted else self._music_volume)
            pygame.mixer.music.play(-1, fade_ms=450)
            self.current_context = ctx
            self.current_variant = var
            self.current_path = path.name
            self.status = "playing"
            print(f"[Audio] context: {ctx} variant:{var} file:{path.name}")
        except Exception as exc:
            self.status = f"error:{exc}"
            print(f"[Audio] context error: {ctx} err={exc}")

    def _cached_sound(self, path: Path) -> pygame.mixer.Sound | None:
        key = str(path)
        snd = self._sound_cache.get(key)
        if snd is not None:
            return snd
        try:
            snd = pygame.mixer.Sound(str(path))
            self._sound_cache[key] = snd
            return snd
        except Exception:
            return None

    def play_stinger(self, name: str):
        nm = str(name or "").lower()
        if nm.startswith("stinger_"):
            nm = nm.replace("stinger_", "", 1)
        stinger_alias = {
            "reward": "relic_gain",
            "boss_phase": "boss_reveal",
        }
        nm = stinger_alias.get(nm, nm)
        if nm not in self.stingers:
            self._log_once(f"missing_stinger:{nm}", f"[Audio] stinger missing: {nm}")
            return
        path = self._ensure_stinger(nm, force=False)
        snd = self._cached_sound(path)
        if snd is None:
            return
        snd.set_volume(0.0 if self._muted else self._sfx_volume)
        if self._stinger_channel is not None:
            self._stinger_channel.play(snd)
        else:
            snd.play()
        print(f"[Audio] stinger: {nm} file:{path.name}")

    def play_sfx(self, name: str):
        nm = str(name or "").lower()
        alias = {
            "ui_click": "button_click",
            "card_pick": "button_click",
            "deny": "card_invalid",
            "hit": "damage_hit",
            "shield": "heal",
            "chime": "xp_gain",
            "whisper": "seal_activate",
            "exhaust": "card_invalid",
        }
        nm = alias.get(nm, nm)
        if nm.startswith("stinger_"):
            self.play_stinger(nm)
            return
        if nm == "studio_intro":
            self.play_stinger("studio_intro")
            return
        if nm not in self.sfx_defs:
            self._log_once(f"missing_sfx:{nm}", f"[Audio] sfx missing: {nm}")
            return
        now = pygame.time.get_ticks()
        cooldown_ms = {
            "button_click": 70,
            "card_invalid": 100,
            "card_play": 90,
            "damage_hit": 110,
            "seal_activate": 140,
        }.get(nm, 80)
        if now - self._sfx_cooldowns.get(nm, 0) < cooldown_ms:
            return
        self._sfx_cooldowns[nm] = now

        path = self._ensure_sfx(nm, force=False)
        snd = self._cached_sound(path)
        if snd is None:
            return
        snd.set_volume(0.0 if self._muted else self._sfx_volume)
        if nm in {"damage_hit", "card_play", "card_invalid", "seal_activate"} and self._impact_channel is not None:
            self._impact_channel.play(snd)
        elif self._ui_sfx_channel is not None:
            self._ui_sfx_channel.play(snd)
        else:
            snd.play()

    def play_studio_intro(self):
        self.play_stinger("studio_intro")

    def tick(self):
        if self.status.startswith("error"):
            return
        try:
            self.status = "playing" if pygame.mixer.music.get_busy() else "idle"
        except Exception:
            self.status = "idle"

    def debug_state(self) -> str:
        self.tick()
        return (
            f"context={self.current_context} variant={self.current_variant} "
            f"path={self.current_path} status={self.status} "
            f"music_vol={self._music_volume:.2f} sfx_vol={self._sfx_volume:.2f} muted={self._muted}"
        )


_ENGINE: AudioEngine | None = None


def get_audio_engine() -> AudioEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = AudioEngine()
    return _ENGINE
















