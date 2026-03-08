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

    VERSION = "chakana_audio_v1"
    SAMPLE_RATE = 22050

    def __init__(self):
        root = Path(__file__).resolve().parent
        self.audio_root = root
        self.generated_root = root / "generated"
        self.bgm_dir = self.generated_root / "bgm"
        self.sfx_dir = self.generated_root / "sfx"
        self.stingers_dir = self.generated_root / "stingers"
        self.studio_dir = self.generated_root / "studio"
        self.manifest_path = root / "audio_manifest.json"
        self._ensure_dirs()

        self.context_specs: dict[str, ContextSpec] = {
            "menu": ContextSpec("mystical calm", ("a", "b", "c"), 26.0, 0.16, 0.42, 0.18),
            "map_ukhu": ContextSpec("exploration ambient", ("a", "b", "c"), 28.0, 0.18, 0.38, 0.22),
            "map_kay": ContextSpec("exploration ambient", ("a", "b", "c"), 28.0, 0.20, 0.44, 0.25),
            "map_hanan": ContextSpec("exploration ambient", ("a", "b", "c"), 28.0, 0.22, 0.50, 0.30),
            "combat": ContextSpec("tense pulse", ("a", "b"), 24.0, 0.34, 0.55, 0.62),
            "combat_elite": ContextSpec("strong percussion", ("a", "b"), 24.0, 0.40, 0.58, 0.72),
            "combat_boss": ContextSpec("ceremonial epic", ("a", "b"), 26.0, 0.46, 0.64, 0.88),
            "event": ContextSpec("mystic narrative", ("a", "b"), 22.0, 0.20, 0.46, 0.26),
            "shop": ContextSpec("calm ritual", ("a", "b"), 22.0, 0.18, 0.48, 0.24),
            "victory": ContextSpec("uplift", ("a",), 18.0, 0.24, 0.62, 0.18),
            "defeat": ContextSpec("falling echo", ("a",), 18.0, 0.14, 0.28, 0.38),
        }
        self.context_alias = {
            "map_kaypacha": "map_kay",
            "map_forest": "map_ukhu",
            "map_umbral": "map_ukhu",
            "combat_kaypacha": "combat",
            "combat_forest": "combat_elite",
            "combat_umbral": "combat_elite",
            "combat_hanan": "combat",
            "boss": "combat_boss",
            "events": "event",
            "lore": "event",
            "reward": "shop",
            "chest": "victory",
        }

        self.stingers = {
            "combat_start": 0.7,
            "elite_encounter": 0.9,
            "boss_reveal": 1.2,
            "victory": 1.1,
            "defeat": 1.1,
            "level_up": 0.8,
            "relic_gain": 0.9,
            "pack_open": 0.9,
            "seal_ready": 0.7,
            "harmony_ready": 0.8,
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
        self._music_volume = 0.5
        self._sfx_volume = 0.7
        self._muted = False
        self.current_context = "-"
        self.current_variant = "-"
        self.current_path = "-"
        self.status = "stopped"

    def _ensure_dirs(self):
        for d in (self.generated_root, self.bgm_dir, self.sfx_dir, self.stingers_dir, self.studio_dir):
            d.mkdir(parents=True, exist_ok=True)

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

    def _music_samples(self, ctx: str, variant: str, seconds: float) -> array:
        spec = self.context_specs[ctx]
        seed = self._stable_seed(f"bgm:{ctx}:{variant}")
        rng = Random(seed)
        total = max(1, int(seconds * self.SAMPLE_RATE))
        samples = array("h")

        base_roots = [52.0, 58.0, 65.0, 73.0]
        rng.shuffle(base_roots)
        bar_sec = 60.0 / max(40.0, 72.0 + 64.0 * spec.pulse)

        for i in range(total):
            t = i / self.SAMPLE_RATE
            bar_idx = int(t / max(0.01, bar_sec * 2.0)) % len(base_roots)
            root = base_roots[bar_idx]
            pulse_freq = root * (1.5 + 0.2 * spec.tension)
            overtone = root * (2.0 + 0.15 * spec.brightness)

            pad = (
                0.38 * math.sin(2 * math.pi * root * t)
                + 0.24 * math.sin(2 * math.pi * (root * 1.25) * t + 0.7)
                + 0.14 * math.sin(2 * math.pi * (root * 1.5) * t + 1.9)
            )
            arp = 0.18 * math.sin(2 * math.pi * overtone * t + 0.6 * math.sin(t * 0.7))
            gate = 0.5 + 0.5 * math.sin(2 * math.pi * (1.0 + spec.pulse) * t)
            rhythm = gate * self._triangle(2 * math.pi * pulse_freq * t)
            noise = 0.05 * math.sin(2 * math.pi * (900 + 80 * spec.brightness) * t + 0.3 * math.sin(t * 3.7))

            x = (0.46 * pad) + (0.26 * arp) + (0.20 * rhythm) + noise
            if spec.tension > 0.6:
                x += 0.08 * math.sin(2 * math.pi * (root * 4.0) * t)

            fade_in = min(1.0, t / 1.2)
            fade_out = min(1.0, (seconds - t) / 1.0)
            amp = max(0.0, min(1.0, fade_in * fade_out))
            y = int(max(-1.0, min(1.0, x * amp * 0.82)) * 32767)
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
                env = min(1.0, t / 0.35) * max(0.0, min(1.0, (seconds - t) / 0.8))
                bell = math.sin(2 * math.pi * (420 + 18 * math.sin(t * 0.9)) * t) * math.exp(-t * 0.7)
                cosmic = math.sin(2 * math.pi * (120 + 40 * t) * t + 0.4 * math.sin(t * 2.2))
                rise = self._triangle(2 * math.pi * (40 + 90 * min(1.0, t / seconds)) * t)
                chord = math.sin(2 * math.pi * 260 * t) + 0.5 * math.sin(2 * math.pi * 325 * t)
                x = 0.38 * bell + 0.28 * cosmic + 0.20 * rise + (0.26 * chord if t > seconds - 0.9 else 0.0)
                out.append(int(max(-1.0, min(1.0, x * env * 0.88)) * 32767))
            return out

        base = {
            "combat_start": 220.0,
            "elite_encounter": 182.0,
            "boss_reveal": 146.0,
            "victory": 312.0,
            "defeat": 118.0,
            "level_up": 392.0,
            "relic_gain": 358.0,
            "pack_open": 268.0,
            "seal_ready": 420.0,
            "harmony_ready": 452.0,
        }.get(name, 300.0)
        return self._tone_burst(base, seconds, attack=0.02, decay=0.6)

    def _sfx_samples(self, name: str, seconds: float) -> array:
        base = {
            "card_play": 340.0,
            "card_invalid": 170.0,
            "button_click": 620.0,
            "gold_gain": 520.0,
            "xp_gain": 560.0,
            "damage_hit": 120.0,
            "heal": 280.0,
            "seal_activate": 240.0,
            "relic_pick": 440.0,
        }.get(name, 320.0)
        return self._tone_burst(base, seconds, attack=0.004, decay=0.9)

    def _item_ok(self, item_id: str, expected_type: str) -> Path | None:
        items = self._manifest.get("items", {})
        meta = items.get(item_id, {}) if isinstance(items, dict) else {}
        if not isinstance(meta, dict) or meta.get("type") != expected_type:
            return None
        p = Path(str(meta.get("file_path", "")))
        return p if p.exists() else None

    def _register_item(self, item_id: str, *, item_type: str, context: str, variant: str, seed: int, file_path: Path):
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
        }
        self._save_manifest()

    def _ensure_bgm_variant(self, ctx: str, variant: str, force: bool = False) -> Path:
        item_id = f"{ctx}_{variant}"
        cached = None if force else self._item_ok(item_id, "bgm")
        if cached is not None:
            return cached
        spec = self.context_specs[ctx]
        seed = self._stable_seed(f"bgm:{item_id}")
        path = self.bgm_dir / f"{item_id}.wav"
        self._write_wave(path, self._music_samples(ctx, variant, spec.seconds))
        self._register_item(item_id, item_type="bgm", context=ctx, variant=variant, seed=seed, file_path=path)
        print(f"[Audio] generated: {item_id}")
        return path

    def _ensure_stinger(self, name: str, force: bool = False) -> Path:
        item_id = f"stinger_{name}"
        cached = None if force else self._item_ok(item_id, "stinger")
        if cached is not None:
            return cached
        seconds = float(self.stingers.get(name, 0.8))
        seed = self._stable_seed(item_id)
        path = (self.studio_dir if name == "studio_intro" else self.stingers_dir) / f"{name}.wav"
        self._write_wave(path, self._stinger_samples(name, seconds))
        self._register_item(item_id, item_type="stinger", context=name, variant="a", seed=seed, file_path=path)
        print(f"[Audio] generated: {item_id}")
        return path

    def _ensure_sfx(self, name: str, force: bool = False) -> Path:
        item_id = f"sfx_{name}"
        cached = None if force else self._item_ok(item_id, "sfx")
        if cached is not None:
            return cached
        seconds = float(self.sfx_defs.get(name, 0.14))
        seed = self._stable_seed(item_id)
        path = self.sfx_dir / f"{name}.wav"
        self._write_wave(path, self._sfx_samples(name, seconds))
        self._register_item(item_id, item_type="sfx", context=name, variant="a", seed=seed, file_path=path)
        print(f"[Audio] generated: {item_id}")
        return path

    def ensure_core_assets(self, force: bool = False) -> dict:
        self._ensure_bgm_variant("menu", "a", force=force)
        self._ensure_bgm_variant("combat", "a", force=force)
        self._ensure_stinger("victory", force=force)
        self._ensure_stinger("defeat", force=force)
        self._ensure_stinger("studio_intro", force=force)
        self._ensure_sfx("button_click", force=force)
        self._ensure_sfx("card_play", force=force)
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
            print(f"[Audio] context: {ctx} variant:{var}")
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
        if nm not in self.stingers:
            return
        path = self._ensure_stinger(nm, force=False)
        snd = self._cached_sound(path)
        if snd is None:
            return
        snd.set_volume(0.0 if self._muted else self._sfx_volume)
        snd.play()
        print(f"[Audio] stinger: {nm}")

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
        snd.play()
        print(f"[Audio] sfx: {nm}")

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
