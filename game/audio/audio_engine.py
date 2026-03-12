from __future__ import annotations

import json
import math
import time
from array import array
from dataclasses import dataclass
from pathlib import Path
from random import Random

import pygame
from rich.console import Console

from engine.creative_direction import CreativeMusicDirector
from engine.audio.music.music_state_machine import MusicStateMachine, TransitionRequest
from engine.audio.music.music_transition_manager import MusicTransitionManager
from engine.audio.music.music_layer_controller import MusicLayerController
from engine.audio.mixer.audio_bus_manager import AudioBusManager
from engine.audio.mixer.ducking_controller import DuckingController
from game.audio.audio_stack_tools import AudioAnalysisReport, analyze_audio_file, write_wav_soundfile
from game.core.paths import audio_dir, audio_generated_dir, curated_audio_dir, data_dir


@dataclass(frozen=True)
class ContextSpec:
    mood: str
    variants: tuple[str, ...]
    seconds: float
    pulse: float
    brightness: float
    tension: float


console = Console(stderr=True, highlight=False)


class AudioEngine:
    """Procedural audio engine with caching and context-aware playback."""

    VERSION = "chakana_audio_v7"
    SAMPLE_RATE = 32000

    def __init__(self):
        self.audio_root = audio_dir()
        self.generated_root = audio_generated_dir()
        self.bgm_dir = self.generated_root / "bgm"
        self.sfx_dir = self.generated_root / "sfx"
        self.stingers_dir = self.generated_root / "stingers"
        self.studio_dir = self.generated_root / "studio"
        self.legacy_manifest_path = self.audio_root / "audio_manifest.json"
        self.manifest_path = data_dir() / "audio_manifest.json"
        self.music_manifest_path = data_dir() / "audio_music_manifest.json"
        self.stinger_manifest_path = data_dir() / "audio_stinger_manifest.json"
        self.sfx_manifest_path = data_dir() / "audio_sfx_manifest.json"
        self.ambient_manifest_path = data_dir() / "audio_ambient_manifest.json"
        self.curated_audio_root = curated_audio_dir()
        self._ensure_dirs()

        # Compact context set: fewer tracks, clearer identity.
        self.context_specs: dict[str, ContextSpec] = {
            "menu": ContextSpec("joyful mystic overture", ("a",), 118.0, 0.07, 0.46, 0.14),
            "map_ukhu": ContextSpec("deep ritual ambience", ("a",), 108.0, 0.10, 0.34, 0.24),
            "map_kay": ContextSpec("pilgrimage ambient", ("a",), 112.0, 0.09, 0.44, 0.22),
            "map_hanan": ContextSpec("luminous sacred ambient", ("a",), 114.0, 0.10, 0.56, 0.18),
            "combat": ContextSpec("chaotic tactical orchestral pulse", ("a",), 122.0, 0.18, 0.54, 0.68),
            "combat_elite": ContextSpec("chaotic tactical orchestral pulse", ("a",), 122.0, 0.20, 0.54, 0.74),
            "combat_boss": ContextSpec("epic archon ceremonial orchestral", ("a",), 132.0, 0.26, 0.62, 0.90),
            "shop": ContextSpec("intimate ceremonial sanctuary", ("a",), 106.0, 0.06, 0.48, 0.16),
            "reward": ContextSpec("gentle uplift reveal", ("a",), 22.0, 0.09, 0.58, 0.14),
            "codex": ContextSpec("scholarly sacred reflection", ("a",), 96.0, 0.05, 0.42, 0.10),
            "credits": ContextSpec("reflective sacred reprise", ("a",), 98.0, 0.07, 0.50, 0.16),
            "victory": ContextSpec("uplift ceremonial", ("a",), 32.0, 0.14, 0.62, 0.18),
            "defeat": ContextSpec("somber echo", ("a",), 34.0, 0.08, 0.26, 0.38),
        }
        self.context_alias = {
            "map_kaypacha": "map_kay",
            "map_fractura_chakana": "map_hanan",
            "map_fractura": "map_hanan",
            "map_forest": "map_ukhu",
            "map_umbral": "map_ukhu",
            "combat_ukhu": "combat",
            "combat_kaypacha": "combat",
            "combat_hanan": "combat",
            "combat_elite": "combat",
            "combat_fractura_chakana": "combat_boss",
            "combat_fractura": "combat_boss",
            "combat_forest": "combat",
            "combat_umbral": "combat",
            "boss": "combat_boss",
            "events": "shop",
            "event": "shop",
            "lore": "shop",
            "sanctuary": "shop",
            "reward": "reward",
            "chest": "victory",
            "menu_main": "menu",
            "map_exploration": "map_kay",
            "shop_ritual": "shop",
            "combat_standard": "combat",
            "boss_battle": "combat_boss",
            "reward_reveal": "victory",
            "credits": "credits",
            "codex": "codex",
            "main_menu": "menu",
            "combat_normal": "combat",
            "rare_reveal": "reward",
            "legendary_reveal": "reward",
            "ending": "victory",
        }

        self.stingers = {
            "combat_start": 1.25,
            "elite_encounter": 1.45,
            "boss_reveal": 2.2,
            "reward": 0.55,
            "pack_open": 0.65,
            "rare_reveal": 0.75,
            "legendary_reveal": 1.10,
            "victory": 1.8,
            "defeat": 1.8,
            "level_up": 1.3,
            "relic_gain": 1.5,
            "seal_ready": 1.2,
            "harmony_ready": 1.3,
            "ritual_trigger": 0.55,
            "boss_warning": 0.75,
            "studio_intro": 3.8,
        }
        self.sfx_defs = {
            "hover": 0.08,
            "select": 0.11,
            "confirm": 0.16,
            "cancel": 0.14,
            "invalid": 0.12,
            "card_play": 0.22,
            "card_invalid": 0.15,
            "button_click": 0.11,
            "draw_card": 0.12,
            "play_card": 0.18,
            "attack_light": 0.16,
            "attack_heavy": 0.22,
            "block": 0.18,
            "gold_gain": 0.16,
            "xp_gain": 0.16,
            "damage_hit": 0.18,
            "heal": 0.22,
            "ritual": 0.26,
            "seal_activate": 0.28,
            "combo_trigger": 0.16,
            "harmony_gain": 0.16,
            "boss_phase": 0.28,
            "relic_pick": 0.20,
        }
        self.ambient_defs = {
            "gaia_mountain_wind": 42.0,
            "temple_resonance": 36.0,
            "archon_void_drones": 34.0,
            "shop_ambience": 30.0,
            "codex_ambience": 32.0,
        }

        self._manifest = self._load_manifest()
        self._last_variant_by_context: dict[str, str] = {}
        self._variant_history_by_context: dict[str, list[str]] = {}
        self._sound_cache: dict[str, pygame.mixer.Sound] = {}
        self._sfx_cooldowns: dict[str, int] = {}
        self._logged_once: set[str] = set()
        self._music_volume = 0.5
        self._sfx_volume = 0.7
        self._stinger_volume = 0.8
        self._ambient_volume = 0.5
        self._muted = False
        self._bus_manager = AudioBusManager()
        self._ducking_controller = DuckingController()
        self._duck_music_until_ms = 0
        self._duck_restore_music_volume = self._music_volume
        self._duck_music_amount = 0.0
        self._stinger_channel = None
        self._ui_sfx_channel = None
        self._impact_channel = None
        self._ambient_channel = None
        self.current_context = "-"
        self.current_variant = "-"
        self.current_path = "-"
        self.current_ambient = "-"
        self.status = "stopped"
        self._init_channels()
        self._creative_music_director = CreativeMusicDirector()
        self._music_state_machine = MusicStateMachine(initial="menu")
        self._transition_manager = MusicTransitionManager()
        self._layer_controller = MusicLayerController()
        self._layer_mode = "single"
        self._music_intensity = 0.25
        self._current_layers = self._layer_controller.set_intensity(self._music_intensity)
        self.current_state = "menu"
        self.current_layer = "full"
        self.state_context_defaults = {
            "menu": "menu",
            "map": "map_kay",
            "combat": "combat",
            "boss": "combat_boss",
            "shop": "shop",
            "reward": "reward",
            "dialogue": "shop",
            "defeat": "defeat",
            "victory": "victory",
            "credits": "credits",
            "codex": "codex",
            "main_menu": "menu",
            "combat_normal": "combat",
            "rare_reveal": "reward",
            "legendary_reveal": "reward",
        }
        self.direction_profiles = {
            "menu": {"plane": "chakana", "faction": "studio", "intensity": "low", "anti_repeat_group": "menu", "tags": ("mystical", "identity", "calm")},
            "map": {"plane": "kay_pacha", "faction": "chakana", "intensity": "low_mid", "anti_repeat_group": "map", "tags": ("travel", "wonder", "exploration")},
            "combat": {"plane": "fractura", "faction": "neutral", "intensity": "mid", "anti_repeat_group": "combat", "tags": ("tactical", "ritual", "pressure")},
            "boss": {"plane": "fractura", "faction": "archon", "intensity": "high", "anti_repeat_group": "boss", "tags": ("ceremonial", "threat", "climax")},
            "shop": {"plane": "sanctuary", "faction": "guide", "intensity": "low", "anti_repeat_group": "shop", "tags": ("calm", "ritual", "intimate")},
            "reward": {"plane": "echo", "faction": "chakana", "intensity": "mid", "anti_repeat_group": "reward", "tags": ("uplift", "discovery", "release")},
            "dialogue": {"plane": "codex", "faction": "oracle", "intensity": "low", "anti_repeat_group": "dialogue", "tags": ("hologram", "lore", "focus")},
            "codex": {"plane": "codex", "faction": "oracle", "intensity": "low", "anti_repeat_group": "codex", "tags": ("study", "archive", "focus")},
            "defeat": {"plane": "umbral", "faction": "archon", "intensity": "low", "anti_repeat_group": "defeat", "tags": ("fall", "echo", "loss")},
            "victory": {"plane": "ascension", "faction": "chakana", "intensity": "mid", "anti_repeat_group": "victory", "tags": ("closure", "gratitude", "transcendence")},
            "credits": {"plane": "ascension", "faction": "studio", "intensity": "low_mid", "anti_repeat_group": "credits", "tags": ("reflection", "gratitude", "continuation")},
        }
        self._recent_state_history: list[str] = []

    def _ensure_dirs(self):
        self.bgm_layers_dir = self.generated_root / "bgm_layers"
        self.ambient_dir = self.generated_root / "ambient"
        for d in (self.generated_root, self.bgm_dir, self.bgm_layers_dir, self.ambient_dir, self.sfx_dir, self.stingers_dir, self.studio_dir):
            d.mkdir(parents=True, exist_ok=True)

    def _init_channels(self):
        try:
            if not pygame.mixer.get_init():
                return
            pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
            self._stinger_channel = pygame.mixer.Channel(1)
            self._ui_sfx_channel = pygame.mixer.Channel(2)
            self._impact_channel = pygame.mixer.Channel(3)
            self._ambient_channel = pygame.mixer.Channel(4)
        except Exception:
            self._stinger_channel = None
            self._ui_sfx_channel = None
            self._impact_channel = None
            self._ambient_channel = None

    def _log_once(self, key: str, text: str):
        if key in self._logged_once:
            return
        self._logged_once.add(key)
        console.print(text)

    def _new_manifest_payload(self) -> dict:
        return {"version": self.VERSION, "generated_at": int(time.time()), "items": {}}

    def _manifest_candidates(self) -> tuple[Path, ...]:
        return (self.manifest_path, self.legacy_manifest_path)

    def _resolve_manifest_file_path(self, meta: dict) -> Path:
        raw = str((meta or {}).get("relative_path", "") or "").strip()
        if raw:
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = Path.cwd() / candidate
            return candidate.expanduser()
        raw = str((meta or {}).get("file_path", "") or "").strip()
        if raw:
            return Path(raw).expanduser()
        return Path()

    def _serialize_manifest_path(self, file_path: Path) -> tuple[str, str]:
        absolute = file_path.resolve()
        try:
            relative = absolute.relative_to(Path.cwd().resolve())
            rel_str = str(relative).replace('\\', '/')
        except ValueError:
            rel_str = str(absolute).replace('\\', '/')
        return str(absolute), rel_str

    def _normalize_manifest_payload(self, data: dict) -> dict:
        payload = self._new_manifest_payload()
        if isinstance(data, dict):
            payload.update({k: v for k, v in data.items() if k != "items"})
            items = data.get("items", {})
            if isinstance(items, dict):
                payload["items"] = items
        payload.setdefault("items", {})
        items = payload.get("items", {})
        if isinstance(items, dict):
            for meta in items.values():
                if isinstance(meta, dict):
                    resolved = self._resolve_manifest_file_path(meta)
                    if str(resolved):
                        absolute, relative = self._serialize_manifest_path(resolved)
                        meta["file_path"] = absolute
                        meta["relative_path"] = relative
        payload["version"] = self.VERSION
        payload["generated_at"] = int(time.time())
        return payload

    def _load_manifest(self) -> dict:
        for candidate in self._manifest_candidates():
            if not candidate.exists():
                continue
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return self._normalize_manifest_payload(data)
            except Exception:
                continue
        return self._new_manifest_payload()

    def _save_manifest(self):
        self._manifest = self._normalize_manifest_payload(self._manifest)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._manifest, indent=2, ensure_ascii=False)
        self.manifest_path.write_text(payload, encoding="utf-8")
        self.legacy_manifest_path.write_text(payload, encoding="utf-8")
        self._export_runtime_manifests()

    def _manifest_entry(self, meta: dict) -> dict:
        if not isinstance(meta, dict):
            return {}
        file_path = self._resolve_manifest_file_path(meta)
        absolute, relative = self._serialize_manifest_path(file_path) if str(file_path) else ("", "")
        return {
            "track_id": str(meta.get("track_id", "") or ""),
            "type": str(meta.get("type", "") or ""),
            "context": str(meta.get("context", "") or ""),
            "variant": str(meta.get("variant", "") or ""),
            "source": str(meta.get("source", "generated") or "generated"),
            "state": str(meta.get("state", "valid") or "valid"),
            "file_path": absolute,
            "relative_path": relative,
        }

    def _write_export_manifest(self, path: Path, payload: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _export_runtime_manifests(self):
        items = self._manifest.get("items", {})
        if not isinstance(items, dict):
            return

        music_items = {}
        stinger_items = {}
        sfx_items = {}
        ambient_items = {}

        for item_id, meta in items.items():
            entry = self._manifest_entry(meta)
            if not entry:
                continue
            item_type = entry.get("type", "")
            if item_type == "bgm":
                music_items[item_id] = entry
            elif item_type == "stinger":
                stinger_items[item_id] = entry
            elif item_type == "sfx":
                sfx_items[item_id] = entry
            elif item_type == "ambient":
                ambient_items[item_id] = entry

        self._write_export_manifest(
            self.music_manifest_path,
            {"version": self.VERSION, "source": "game/data/audio_manifest.json", "items": music_items},
        )
        self._write_export_manifest(
            self.stinger_manifest_path,
            {"version": self.VERSION, "source": "game/data/audio_manifest.json", "items": stinger_items},
        )
        self._write_export_manifest(
            self.sfx_manifest_path,
            {"version": self.VERSION, "source": "game/data/audio_manifest.json", "items": sfx_items},
        )
        self._write_export_manifest(
            self.ambient_manifest_path,
            {"version": self.VERSION, "source": "game/data/audio_manifest.json", "items": ambient_items},
        )

    def _stable_seed(self, key: str) -> int:
        return abs(hash(f"{self.VERSION}:{key}")) % (2**31 - 1)

    def _write_wave(self, path: Path, samples: array):
        write_wav_soundfile(path, samples, self.SAMPLE_RATE, channels=1, subtype='PCM_16')

    def _analyze_audio_asset(self, path: Path) -> AudioAnalysisReport | None:
        try:
            return analyze_audio_file(path)
        except Exception as exc:
            self._log_once(f'audio_analysis_error:{path.name}', f'[Audio] analysis error: {path.name} err={exc}')
            return None

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

    def _ambient_samples(self, name: str, seconds: float) -> array:
        base = {
            "gaia_mountain_wind": (68.0, 0.18, 0.10),
            "temple_resonance": (96.0, 0.22, 0.16),
            "archon_void_drones": (52.0, 0.26, 0.20),
            "shop_ambience": (88.0, 0.14, 0.08),
            "codex_ambience": (80.0, 0.16, 0.10),
        }.get(name, (72.0, 0.16, 0.10))
        f0, depth, shimmer = base
        total = max(1, int(seconds * self.SAMPLE_RATE))
        out = array("h")
        prev = 0.0
        for i in range(total):
            t = i / self.SAMPLE_RATE
            sweep = f0 + 8.0 * math.sin(2 * math.pi * 0.03 * t)
            drone = 0.45 * math.sin(2 * math.pi * sweep * t)
            low = 0.20 * math.sin(2 * math.pi * (f0 * 0.5) * t + 0.4)
            airy = 0.12 * math.sin(2 * math.pi * (f0 * 1.9) * t + 0.22 * math.sin(t * 0.2))
            noise = depth * math.sin(2 * math.pi * (18.0 + 6.0 * math.sin(t * 0.12)) * t)
            sparkle = shimmer * math.sin(2 * math.pi * (f0 * 2.6) * t + 0.7)
            x = drone + low + airy + noise + sparkle
            x = 0.90 * x + 0.10 * prev
            prev = x
            env = min(1.0, t / 1.6) * max(0.0, min(1.0, (seconds - t) / 1.8))
            out.append(int(max(-1.0, min(1.0, x * env * 0.72)) * 32767))
        return out

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
        if expected_type == "ambient":
            nm = item_id.replace("ambient_", "", 1)
            p = root / "ambient" / f"{nm}.wav"
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
        if expected_type == "ambient":
            name = item_id.replace("ambient_", "", 1)
            return self.ambient_dir / f"{name}.wav"
        return self.generated_root / f"{item_id}.wav"

    def _item_ok(self, item_id: str, expected_type: str) -> Path | None:
        items = self._manifest.get("items", {})
        meta = items.get(item_id, {}) if isinstance(items, dict) else {}
        if isinstance(meta, dict) and meta and meta.get("type") == expected_type:
            p = self._resolve_manifest_file_path(meta)
            if p.exists() and str(meta.get("state", "valid")) not in {"archived_legacy", "legacy_optional"}:
                if not isinstance(meta.get("analysis"), dict) or not meta.get("analysis"):
                    analysis = self._analyze_audio_asset(p)
                    if analysis:
                        meta["analysis"] = analysis.model_dump()
                        self._save_manifest()
                return p

        curated = self._curated_item_path(item_id, expected_type)
        if curated is not None:
            return curated
        return None

    def _register_item(self, item_id: str, *, item_type: str, context: str, variant: str, seed: int, file_path: Path, source: str = "generated"):
        items = self._manifest.setdefault("items", {})
        analysis = self._analyze_audio_asset(file_path)
        items[item_id] = {
            "track_id": item_id,
            "type": item_type,
            "context": context,
            "variant": variant,
            "seed": int(seed),
            "file_path": self._serialize_manifest_path(file_path)[0],
            "relative_path": self._serialize_manifest_path(file_path)[1],
            "generation_date": int(time.time()),
            "version": self.VERSION,
            "state": "valid",
            "source": str(source or "generated"),
            "analysis": analysis.model_dump() if analysis else {},
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
        analysis = self._analyze_audio_asset(path)
        if analysis:
            console.print(f"[cyan][Audio][/cyan] generated: {item_id} tempo={analysis.tempo_bpm} onsets={analysis.onset_count} variation={analysis.variation_score}")
        else:
            console.print(f"[cyan][Audio][/cyan] generated: {item_id}")
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
        analysis = self._analyze_audio_asset(path)
        if analysis:
            console.print(f"[cyan][Audio][/cyan] generated: {item_id} tempo={analysis.tempo_bpm} onsets={analysis.onset_count} variation={analysis.variation_score}")
        else:
            console.print(f"[cyan][Audio][/cyan] generated: {item_id}")
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
        analysis = self._analyze_audio_asset(path)
        if analysis:
            console.print(f"[cyan][Audio][/cyan] generated: {item_id} tempo={analysis.tempo_bpm} onsets={analysis.onset_count} variation={analysis.variation_score}")
        else:
            console.print(f"[cyan][Audio][/cyan] generated: {item_id}")
        return path

    def _ensure_ambient(self, name: str, force: bool = False) -> Path:
        item_id = f"ambient_{name}"
        cached = None if force else self._item_ok(item_id, "ambient")
        if cached is not None:
            if item_id not in self._manifest.get("items", {}):
                seed = self._stable_seed(item_id)
                self._register_item(item_id, item_type="ambient", context=name, variant="a", seed=seed, file_path=cached, source=self._source_from_path(cached))
            return cached
        seconds = float(self.ambient_defs.get(name, 32.0))
        seed = self._stable_seed(item_id)
        path = self.ambient_dir / f"{name}.wav"
        self._write_wave(path, self._ambient_samples(name, seconds))
        self._register_item(item_id, item_type="ambient", context=name, variant="a", seed=seed, file_path=path, source="generated")
        analysis = self._analyze_audio_asset(path)
        if analysis:
            console.print(f"[cyan][Audio][/cyan] generated: {item_id} tempo={analysis.tempo_bpm} onsets={analysis.onset_count} variation={analysis.variation_score}")
        else:
            console.print(f"[cyan][Audio][/cyan] generated: {item_id}")
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
        for name in self.ambient_defs:
            valid_ids.add(f"ambient_{name}")

        changed = False
        for item_id in list(items.keys()):
            meta = items.get(item_id, {})
            p = self._resolve_manifest_file_path(meta)
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
        for name in self.ambient_defs:
            self._ensure_ambient(name, force=force)
        return self._manifest

    def _effective_bus_gain(self, bus: str) -> float:
        b = str(bus or "master").lower()
        master = self._bus_manager.get_level("master", 1.0)
        level = self._bus_manager.get_level(b, 1.0)
        duck = self._ducking_controller.get_amount(b)
        return max(0.0, min(1.0, master * level * (1.0 - duck)))

    def _refresh_bus_gains(self):
        try:
            pygame.mixer.music.set_volume(0.0 if self._muted else self._effective_bus_gain("music"))
            if self._ambient_channel is not None:
                self._ambient_channel.set_volume(0.0 if self._muted else self._effective_bus_gain("ambient"))
        except Exception:
            pass

    def set_master_volume(self, value: float):
        self._bus_manager.set_level("master", max(0.0, min(1.0, float(value))))
        self._refresh_bus_gains()

    def set_bus_volume(self, bus: str, value: float):
        self._bus_manager.set_level(str(bus or ""), max(0.0, min(1.0, float(value))))
        self._refresh_bus_gains()

    def apply_volume_profile(self, profile_name: str):
        from engine.audio.mixer.volume_profiles import VOLUME_PROFILES

        key = str(profile_name or "default")
        prof = VOLUME_PROFILES.get(key, VOLUME_PROFILES.get("default", {}))
        self._bus_manager.apply_profile(prof)
        self._music_volume = self._bus_manager.get_level("music", self._music_volume)
        self._sfx_volume = self._bus_manager.get_level("sfx", self._sfx_volume)
        self._stinger_volume = self._bus_manager.get_level("stingers", self._stinger_volume)
        self._ambient_volume = self._bus_manager.get_level("ambient", self._ambient_volume)
        self._refresh_bus_gains()

    def set_music_volume(self, value: float):
        self._music_volume = max(0.0, min(1.0, float(value)))
        self._bus_manager.set_level("music", self._music_volume)
        self._refresh_bus_gains()

    def set_sfx_volume(self, value: float):
        self._sfx_volume = max(0.0, min(1.0, float(value)))
        self._bus_manager.set_level("sfx", self._sfx_volume)

    def set_stinger_volume(self, value: float):
        self._stinger_volume = max(0.0, min(1.0, float(value)))
        self._bus_manager.set_level("stingers", self._stinger_volume)

    def set_ambient_volume(self, value: float):
        self._ambient_volume = max(0.0, min(1.0, float(value)))
        self._bus_manager.set_level("ambient", self._ambient_volume)
        self._refresh_bus_gains()

    def set_muted(self, muted: bool):
        self._muted = bool(muted)
        self._refresh_bus_gains()

    def _normalize_context(self, context: str) -> str:
        key = str(context or "menu").lower()
        key = self.context_alias.get(key, key)
        return key if key in self.context_specs else "menu"

    def _choose_variant(self, context: str) -> str:
        variants = self.context_specs[context].variants
        if len(variants) <= 1:
            return variants[0]
        history = list(self._variant_history_by_context.get(context, []))[-4:]
        last = self._last_variant_by_context.get(context)
        scores = []
        for variant in variants:
            recency_penalty = 3 if variant == last else 0
            recency_penalty += history.count(variant)
            scores.append((recency_penalty, variant))
        scores.sort(key=lambda item: (item[0], item[1]))
        best_score = scores[0][0]
        best = [variant for score, variant in scores if score == best_score]
        choice = best[Random().randint(0, len(best) - 1)]
        self._last_variant_by_context[context] = choice
        history.append(choice)
        self._variant_history_by_context[context] = history[-6:]
        return choice

    def _state_from_context(self, context: str) -> str:
        ctx = str(context or "menu").lower()
        if ctx.startswith("map"):
            return "map"
        if ctx.startswith("combat_boss") or ctx == "boss":
            return "boss"
        if ctx.startswith("combat"):
            return "combat"
        if ctx.startswith("shop"):
            return "shop"
        if ctx.startswith("victory"):
            return "victory"
        if ctx.startswith("defeat"):
            return "defeat"
        if ctx.startswith("reward"):
            return "reward"
        if ctx.startswith("credits") or ctx.startswith("ending"):
            return "credits"
        if ctx.startswith("dialogue") or ctx.startswith("event") or ctx.startswith("lore"):
            return "dialogue"
        return "menu"

    def get_direction_profile(self, state: str | None = None) -> dict:
        key = str(state or self.current_state or "menu").lower()
        return dict(self.direction_profiles.get(key, self.direction_profiles["menu"]))

    def _register_state_history(self, state: str):
        key = str(state or "menu").lower()
        self._recent_state_history.append(key)
        self._recent_state_history = self._recent_state_history[-6:]

    def _anti_repeat_variant(self, ctx: str, variant: str) -> str:
        state = self._state_from_context(ctx)
        profile = self.get_direction_profile(state)
        group = str(profile.get("anti_repeat_group", state))
        recent = [item for item in self._recent_state_history[-3:] if item == group]
        if len(recent) >= 2:
            variants = self.context_specs[ctx].variants
            for alt in variants:
                if alt != variant:
                    return alt
        return variant

    def play_state(self, state: str, context_override: str | None = None):
        target_state = str(state or "menu").lower()
        target_context = str(context_override or self.state_context_defaults.get(target_state, "menu"))
        self.play_context(target_context)

    def set_layer_mode(self, mode: str) -> str:
        mm = str(mode or "single").lower()
        self._layer_mode = "layered" if mm in {"layered", "layers", "multi"} else "single"
        return self._layer_mode

    def set_music_intensity(self, value: float):
        self._music_intensity = max(0.0, min(1.0, float(value)))
        self._current_layers = self._layer_controller.set_intensity(self._music_intensity)
        return self._current_layers

    def layer_state(self) -> dict[str, bool]:
        ls = self._current_layers
        return {
            "pad": bool(ls.pad),
            "bass": bool(ls.bass),
            "melody": bool(ls.melody),
            "percussion": bool(ls.percussion),
            "fx": bool(ls.fx),
        }

    def _default_intensity_for_state(self, state: str) -> float:
        table = {
            "menu": 0.22,
            "map": 0.32,
            "combat": 0.62,
            "boss": 0.86,
            "shop": 0.26,
            "reward": 0.42,
            "dialogue": 0.20,
            "defeat": 0.18,
            "victory": 0.46,
        }
        return float(table.get(str(state or "menu"), 0.30))

    def _resolve_layer_playback(self, ctx: str, variant: str, fallback_path: Path):
        if self._layer_mode != "layered":
            self.current_layer = "full"
            return fallback_path

        active = self.layer_state()
        preferred = []
        if active.get("melody"):
            preferred.append("melody")
        if active.get("percussion"):
            preferred.append("percussion")
        if active.get("fx"):
            preferred.append("fx")
        preferred.extend(["pad", "bass", "full"])

        for layer in preferred:
            candidates = [
                self.bgm_layers_dir / ctx / f"{layer}_{variant}.wav",
                self.bgm_layers_dir / ctx / f"{layer}.wav",
                self.curated_audio_root / "bgm_layers" / ctx / f"{layer}_{variant}.wav",
                self.curated_audio_root / "bgm_layers" / ctx / f"{layer}.wav",
            ]
            for cand in candidates:
                if cand.exists():
                    self.current_layer = layer
                    return cand

        self.current_layer = "full"
        return fallback_path

    def _ambient_from_music_context(self, ctx: str) -> str | None:
        key = str(ctx or "").lower()
        if key.startswith("map_ukhu"):
            return "archon_void_drones"
        if key.startswith("map_hanan"):
            return "temple_resonance"
        if key.startswith("map"):
            return "gaia_mountain_wind"
        if key.startswith("shop"):
            return "shop_ambience"
        if key.startswith("menu") or key.startswith("event") or key.startswith("lore"):
            return "codex_ambience"
        return None

    def play_ambient(self, context_name: str | None):
        if not context_name:
            self.stop_ambient()
            return
        nm = str(context_name).lower()
        if nm not in self.ambient_defs:
            self._log_once(f"missing_ambient:{nm}", f"[Audio] ambient missing: {nm}")
            return
        path = self._ensure_ambient(nm, force=False)
        snd = self._cached_sound(path)
        if snd is None:
            return
        snd.set_volume(0.0 if self._muted else self._effective_bus_gain("ambient"))
        try:
            if self._ambient_channel is not None:
                if self.current_ambient == nm and self._ambient_channel.get_busy():
                    return
                self._ambient_channel.play(snd, loops=-1)
            else:
                snd.play(loops=-1)
            self.current_ambient = nm
            console.print(f"[cyan][Audio][/cyan] ambient: {nm} file:{path.name}")
        except Exception as exc:
            self._log_once(f"ambient_error:{nm}", f"[Audio] ambient error: {nm} err={exc}")

    def stop_ambient(self):
        try:
            if self._ambient_channel is not None:
                self._ambient_channel.stop()
        except Exception:
            pass
        self.current_ambient = "-"

    def begin_dialogue_duck(self, amount: float = 0.35):
        amt = max(0.0, min(0.90, float(amount)))
        self._ducking_controller.apply("music", amt, source="dialogue")
        self._ducking_controller.apply("ambient", min(0.85, amt + 0.15), source="dialogue")
        self._refresh_bus_gains()

    def end_dialogue_duck(self):
        self._ducking_controller.clear("music", source="dialogue")
        self._ducking_controller.clear("ambient", source="dialogue")
        self._refresh_bus_gains()

    def mixer_snapshot(self) -> dict:
        return {
            "buses": self._bus_manager.snapshot(),
            "ducking": self._ducking_controller.snapshot(),
            "muted": bool(self._muted),
        }

    def play_context(self, context: str):
        ctx = self._normalize_context(context)
        target_state = self._state_from_context(ctx)
        transition = self._transition_manager.resolve(self.current_state, target_state)
        self.set_music_intensity(self._default_intensity_for_state(target_state))

        # Avoid restarting the same music context if it's already playing.
        try:
            if self.current_context == ctx and pygame.mixer.music.get_busy():
                self.current_state = self._music_state_machine.transition(
                    TransitionRequest(
                        target=target_state,
                        fade_out_ms=int(transition.get("fade_out_ms", 0) or 0),
                        fade_in_ms=int(transition.get("fade_in_ms", 0) or 0),
                    )
                )
                self.status = "playing"
                return
        except Exception:
            pass

        var = self._anti_repeat_variant(ctx, self._choose_variant(ctx))
        path = self._ensure_bgm_variant(ctx, var, force=False)
        path = self._resolve_layer_playback(ctx, var, path)
        fade_ms = int(transition.get("fade_in_ms", 450) or 450)
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(0.0 if self._muted else self._effective_bus_gain("music"))
            pygame.mixer.music.play(-1, fade_ms=max(0, fade_ms))
            self.current_context = ctx
            self.current_variant = var
            self.current_path = path.name
            self.current_state = self._music_state_machine.transition(
                TransitionRequest(
                    target=target_state,
                    fade_out_ms=int(transition.get("fade_out_ms", 0) or 0),
                    fade_in_ms=max(0, fade_ms),
                )
            )
            self._register_state_history(self.current_state)
            self.status = "playing"
            self.play_ambient(self._ambient_from_music_context(ctx))
            console.print(f"[cyan][Audio][/cyan] state:{self.current_state} context:{ctx} variant:{var} layer:{self.current_layer} file:{path.name}")
        except Exception as exc:
            self.status = f"error:{exc}"
            console.print(f"[red][Audio][/red] context error: {ctx} err={exc}")

    def _apply_music_duck(self, amount: float, duration_ms: int):
        now = pygame.time.get_ticks()
        amt = max(0.0, min(0.95, float(amount)))
        dur = max(0, int(duration_ms))
        self._duck_music_amount = max(self._duck_music_amount, amt)
        self._duck_restore_music_volume = self._music_volume
        self._duck_music_until_ms = max(self._duck_music_until_ms, now + dur)
        self._ducking_controller.apply("music", self._duck_music_amount, source="stinger")
        self._ducking_controller.apply("ambient", min(0.90, self._duck_music_amount + 0.10), source="stinger")
        self._refresh_bus_gains()

    def _update_ducking(self):
        if self._duck_music_until_ms <= 0:
            return
        now = pygame.time.get_ticks()
        if now < self._duck_music_until_ms:
            return
        self._duck_music_until_ms = 0
        self._duck_music_amount = 0.0
        self._ducking_controller.clear("music", source="stinger")
        self._ducking_controller.clear("ambient", source="stinger")
        self._refresh_bus_gains()

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
            "reward": "reward",
            "boss_phase": "boss_warning",
            "rare": "rare_reveal",
            "legendary": "legendary_reveal",
        }
        nm = stinger_alias.get(nm, nm)
        if nm not in self.stingers:
            self._log_once(f"missing_stinger:{nm}", f"[Audio] stinger missing: {nm}")
            return
        path = self._ensure_stinger(nm, force=False)
        snd = self._cached_sound(path)
        if snd is None:
            return

        duck_profile = {
            "boss_reveal": (0.45, 1800),
            "defeat": (0.38, 1600),
            "victory": (0.34, 1400),
            "studio_intro": (0.28, 1200),
            "elite_encounter": (0.30, 1200),
            "relic_gain": (0.24, 900),
            "pack_open": (0.24, 900),
            "level_up": (0.22, 800),
            "harmony_ready": (0.20, 700),
            "seal_ready": (0.20, 700),
            "combat_start": (0.22, 800),
        }
        duck_amount, duck_ms = duck_profile.get(nm, (0.20, 700))
        self._apply_music_duck(duck_amount, duck_ms)

        stinger_gain = self._effective_bus_gain("stingers")
        snd.set_volume(0.0 if self._muted else stinger_gain)
        if self._stinger_channel is not None:
            self._stinger_channel.play(snd)
        else:
            snd.play()
        console.print(f"[cyan][Audio][/cyan] stinger: {nm} file:{path.name} duck={duck_amount:.2f}/{duck_ms}ms")

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
            "ui_confirm": "confirm",
            "ui_cancel": "cancel",
            "menu_confirm": "confirm",
            "menu_cancel": "cancel",
            "menu_hover": "hover",
            "menu_select": "select",
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
        snd.set_volume(0.0 if self._muted else self._effective_bus_gain("sfx"))
        if nm in {"damage_hit", "card_play", "card_invalid", "seal_activate"} and self._impact_channel is not None:
            self._impact_channel.play(snd)
        elif self._ui_sfx_channel is not None:
            self._ui_sfx_channel.play(snd)
        else:
            snd.play()

    def play_studio_intro(self):
        self.play_stinger("studio_intro")

    def tick(self):
        self._update_ducking()
        if self.status.startswith("error"):
            return
        try:
            self.status = "playing" if pygame.mixer.music.get_busy() else "idle"
        except Exception:
            self.status = "idle"
    def debug_state(self) -> str:
        self.tick()
        ls = self.layer_state()
        mx = self.mixer_snapshot()
        return (
            f"state={self.current_state} context={self.current_context} variant={self.current_variant} layer={self.current_layer} ambient={self.current_ambient} "
            f"path={self.current_path} status={self.status} mode={self._layer_mode} intensity={self._music_intensity:.2f} "
            f"layers=pad:{int(ls['pad'])},bass:{int(ls['bass'])},melody:{int(ls['melody'])},percussion:{int(ls['percussion'])},fx:{int(ls['fx'])} "
            f"music_vol={self._music_volume:.2f} sfx_vol={self._sfx_volume:.2f} stinger_vol={self._stinger_volume:.2f} ambient_vol={self._ambient_volume:.2f} profile={self.get_direction_profile()} "
            f"duck={self._duck_music_amount:.2f} buses={mx['buses']} ducking={mx['ducking']} muted={self._muted}"
        )

_ENGINE: AudioEngine | None = None


def get_audio_engine() -> AudioEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = AudioEngine()
    return _ENGINE



























