from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import pygame

from game.art.gen_art32 import seed_from_id
from game.art.gen_card_art32 import GEN_CARD_ART_VERSION, generate
from game.core.paths import assets_dir, data_dir
from game.core.safe_io import atomic_write_json_if_changed, load_json
from game.visual.generators.lore_motifs import MOTIF_LIBRARY, motifs_for_archetype


class PromptBuilder:
    def family_for(self, card: dict) -> str:
        tags = {str(t).lower() for t in (card.get("tags", []) or [])}
        role = str(card.get("role", "")).lower()
        if "attack" in tags or role == "attack":
            return "attack"
        if "block" in tags or "defense" in tags or role == "defense":
            return "defense"
        if "ritual" in tags or role == "ritual":
            return "ritual"
        if "draw" in tags or "scry" in tags or "control" in tags or role == "control":
            return "control"
        return "spirit"

    def effect_signature(self, card: dict) -> str:
        effects = [str(e.get("type", "")).lower() for e in list(card.get("effects", []) or []) if isinstance(e, dict)]
        if "damage" in effects:
            return "impacto_ofensivo"
        if "gain_block" in effects or "block" in effects:
            return "barrera_ritual"
        if "scry" in effects:
            return "vision_oracular"
        if "draw" in effects:
            return "flujo_mental"
        if "harmony_delta" in effects:
            return "resonancia_armonica"
        return "trazo_mistico"

    def archetype_mood(self, card: dict) -> tuple[str, str, str, str]:
        # Prefer explicit semantic fields from card data/runtime enrichment.
        palette = str(card.get("palette", "")).strip()
        energy = str(card.get("energy", "")).strip()
        symbol = str(card.get("symbol", "")).strip()
        if palette and energy and symbol:
            lighting = "balanced glow"
            if "crimson" in palette or "red" in palette:
                lighting = "hard rim light"
            elif "teal" in palette or "gold" in palette:
                lighting = "soft frontal glow"
            elif "indigo" in palette or "cyan" in palette:
                lighting = "split mystic light"
            return (palette, lighting, symbol.replace("_", " "), energy)

        arch = str(card.get("archetype", "")).lower()
        if arch == "cosmic_warrior":
            return ("crimson-magenta", "hard rim light", "blade sigils", "burst arcs")
        if arch == "harmony_guardian":
            return ("teal-gold", "soft frontal glow", "shield mandala", "stable rings")
        if arch == "oracle_of_fate":
            return ("indigo-cyan", "split mystic light", "eye geometry", "spiral streams")
        return ("violet-neutral", "balanced glow", "chakana glyph", "arc traces")

    def lore_profile(self, card: dict) -> tuple[str, str, str]:
        explicit_motif = str(card.get("motif", "")).strip().lower()
        if explicit_motif:
            motif = MOTIF_LIBRARY.get(explicit_motif, {})
            shape = ",".join(list(motif.get("shapes", ("chakana",)))[:2])
            symbol = ",".join(list(motif.get("symbols", ("seal",)))[:2])
            tone = str(motif.get("tone", "mystic_order"))
            return explicit_motif, shape, f"{symbol}:{tone}"

        motifs = motifs_for_archetype(str(card.get("archetype", "")))
        primary = motifs[0]
        motif = MOTIF_LIBRARY.get(primary, {})
        shape = ",".join(list(motif.get("shapes", ("chakana",)))[:2])
        symbol = ",".join(list(motif.get("symbols", ("seal",)))[:2])
        tone = str(motif.get("tone", "mystic_order"))
        return primary, shape, f"{symbol}:{tone}"

    def build_entry(self, card: dict) -> dict:
        cid = card.get("id", "unknown")
        ctype = self.family_for(card)
        palette, lighting, symbols, energy = self.archetype_mood(card)
        primary, shape, lore_tokens = self.lore_profile(card)
        role = str(card.get("role", "") or "control").lower()
        effect_sig = self.effect_signature(card)
        prompt = (
            f"chakana card::{cid}::{ctype} high density pixel fantasy, layered depth, "
            f"silhouette discipline, role {role}, palette {palette}, lighting {lighting}, "
            f"sacred geometry {symbols}, motif {primary} ({shape}), "
            f"effect signature {effect_sig}, energy pattern {energy}, lore tokens {lore_tokens}, "
            f"crisp no blur, intentional composition"
        )
        return {
            "id": cid,
            "card_type": ctype,
            "family": ctype,
            "prompt_text": prompt,
        }


class CardArtGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "cards"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.generated_count = 0
        self.replaced_count = 0
        self.version_seed = GEN_CARD_ART_VERSION
        self._recent_hashes: deque[int] = deque(maxlen=5)

    def _placeholder(self, card_id: str) -> pygame.Surface:
        out = pygame.Surface((320, 220), flags=pygame.SRCALPHA, depth=32)
        out.fill((18, 14, 28, 255))
        pygame.draw.circle(out, (180, 150, 220), (160, 110), 42, 2)
        pygame.draw.line(out, (180, 150, 220), (132, 88), (188, 132), 2)
        pygame.draw.line(out, (180, 150, 220), (188, 88), (132, 132), 2)
        pygame.draw.rect(out, (92, 78, 130), out.get_rect(), 2)
        f = pygame.font.SysFont("consolas", 16)
        out.blit(f.render(card_id[:24], True, (220, 215, 236)), (10, 194))
        return out

    def ensure_art(self, card_id: str, tags: list[str], rarity: str, mode: str = "missing_only", family: str | None = None, symbol: str | None = None, prompt: str = ""):
        path = self.out_dir / f"{card_id}.png"
        if path.exists() and mode not in {"force_regen"}:
            return {"card_id": card_id, "path": str(path), "generator_used": "existing", "hash16": None, "prompt": prompt}

        card_type = family or ("attack" if "attack" in tags else "defense" if ("block" in tags or "defense" in tags) else "control" if ("draw" in tags or "scry" in tags or "control" in tags) else "spirit")
        seed = seed_from_id(card_id, GEN_CARD_ART_VERSION)
        result = generate(card_id, card_type, prompt, seed, path)
        h = int(result.get("hash16", 0))
        if any(abs(h - prev) < 220 for prev in self._recent_hashes):
            result = generate(card_id, card_type, prompt, seed + 991, path)
            h = int(result.get("hash16", 0))
        self._recent_hashes.append(h)
        if not path.exists():
            pygame.image.save(self._placeholder(card_id), str(path))
            result = {"card_id": card_id, "path": str(path), "generator_used": "placeholder", "hash16": 0, "prompt": prompt}
        self.generated_count += 1
        return result


def _legacy_txt_to_cards(txt_path: Path) -> dict:
    cards = {}
    if not txt_path.exists():
        return cards
    try:
        for raw in txt_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip() or ":" not in raw:
                continue
            cid, prompt = raw.split(":", 1)
            cid = cid.strip()
            prompt = prompt.strip()
            if not cid:
                continue
            cards[cid] = {"prompt": prompt, "style": "legacy", "updated_at": "1970-01-01T00:00:00Z"}
    except Exception:
        return {}
    return cards


def _prompt_payload(cards: list[dict], seed: int = 12345) -> dict:
    pb = PromptBuilder()
    out = {"version": 1, "seed": int(seed), "cards": {}}
    seen = set()
    for c in cards:
        cid = str(c.get("id", "")).strip()
        if not cid:
            continue
        if cid in seen:
            print(f"[prompts] warning duplicate write attempt for card_id={cid}")
            continue
        seen.add(cid)
        entry = pb.build_entry(c)
        out["cards"][cid] = {
            "prompt": entry.get("prompt_text", ""),
            "style": entry.get("card_type", "spirit"),
            "updated_at": "1970-01-01T00:00:00Z",
        }
    return out


def export_prompts(cards: list[dict], enemies: list[dict] | None = None):
    prompts_path = data_dir() / "card_prompts.json"
    legacy_txt_path = data_dir() / "card_prompts.txt"
    payload = _prompt_payload(cards, seed=12345)

    existing = load_json(prompts_path, default={}, optional=True)
    if not isinstance(existing, dict):
        existing = {}
    existing_cards = existing.get("cards", {}) if isinstance(existing.get("cards", {}), dict) else {}
    if not existing_cards and legacy_txt_path.exists():
        legacy_cards = _legacy_txt_to_cards(legacy_txt_path)
        if legacy_cards:
            for cid, data in legacy_cards.items():
                payload["cards"].setdefault(cid, data)

    for cid, pdata in payload["cards"].items():
        old = existing_cards.get(cid, {}) if isinstance(existing_cards, dict) else {}
        if isinstance(old, dict) and old.get("prompt") == pdata.get("prompt") and old.get("style") == pdata.get("style"):
            pdata["updated_at"] = str(old.get("updated_at", pdata.get("updated_at")))

    atomic_write_json_if_changed(prompts_path, payload, sort_keys=True)
    atomic_write_json_if_changed(data_dir() / "prompt_manifest.json", {"generator_version": GEN_CARD_ART_VERSION, "count": len(payload.get("cards", {}))}, sort_keys=True)
    atomic_write_json_if_changed(data_dir() / "art_manifest_cards.json", {"generator_version": GEN_CARD_ART_VERSION, "count": len(payload.get("cards", {}))}, sort_keys=True)
