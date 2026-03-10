from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import pygame

from engine.creative_direction import CreativeArtDirector
from game.art.gen_art32 import seed_from_id
from game.art.gen_card_art32 import GEN_CARD_ART_VERSION
from game.art.gen_card_art_advanced import generate
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

    def composition_blueprint(self, card: dict) -> dict:
        arch = str(card.get("archetype", "") or "").lower()
        family = self.family_for(card)
        role = str(card.get("role", "") or family).lower()
        rarity = str(card.get("rarity", "common") or "common").lower()
        motif = str(card.get("motif", "") or "").lower()
        effect_sig = self.effect_signature(card)

        if "hip_" in str(card.get("id", "")).lower() or "hiperborea" in str(card.get("set", "")).lower() or "hiperboria" in str(card.get("set", "")).lower():
            environment = "ancient polar temple background with crystalline architecture and distant aurora"
        elif "archon" in arch or "archon" in motif or "void" in motif:
            environment = "corrupted void sanctuary background with broken geometry and oppressive depth"
        else:
            environment = "mystic chakana sanctuary background with layered sacred stone and cosmic horizon"

        if family == "attack":
            subject = "warrior, beast or ritual attacker in clear combat pose"
            obj = "weapon, blade, spear or striking focus relic"
        elif family == "defense":
            subject = "guardian, sentinel or shield bearer in anchored stance"
            obj = "shield seal, stone ward or defensive relic focus"
        elif family == "ritual":
            subject = "ritual caster or ceremonial conduit channeling power"
            obj = "altar focus, seal tablet or sacred catalyst"
        elif family == "control":
            subject = "oracle, seer or mind-weaver reading the flow"
            obj = "eye relic, codex shard or divination instrument"
        else:
            subject = "mystic conduit or spiritual avatar holding the field"
            obj = "chakana relic, energy knot or spiritual focus"

        if arch == "oracle_of_fate":
            subject = "oracular figure with intense gaze reading the weave"
        elif arch == "harmony_guardian":
            subject = "guardian figure holding balance and warding force"
        elif arch == "cosmic_warrior":
            subject = "cosmic warrior driving forward with decisive motion"
        elif "archon" in arch:
            subject = "archon entity or corrupted servant dominating the scene"

        effects = {
            "impacto_ofensivo": "burst arcs, impact trails, sparks and offensive energy cuts",
            "barrera_ritual": "stable rings, ward sigils, shield glow and defensive pulse lines",
            "vision_oracular": "spiral streams, eye light, foresight glyphs and cognitive echoes",
            "flujo_mental": "draw currents, ribbon streams, memory wisps and lucid particles",
            "resonancia_armonica": "harmonic halos, resonance bands, golden pulse chords and balanced light",
            "trazo_mistico": "arc traces, luminous dust, subtle sigils and ether drift",
        }.get(effect_sig, "arc traces, luminous dust, subtle sigils and ether drift")

        if rarity == "legendary":
            effects += ", premium ceremonial glow and expanded focal aura"
        return {
            "subject": subject,
            "object": obj,
            "environment": environment,
            "effects": effects,
        }

    def build_entry(self, card: dict) -> dict:
        cid = card.get("id", "unknown")
        ctype = self.family_for(card)
        palette, lighting, symbols, energy = self.archetype_mood(card)
        primary, shape, lore_tokens = self.lore_profile(card)
        role = str(card.get("role", "") or "control").lower()
        rarity = str(card.get("rarity", "common") or "common").lower()
        effect_sig = self.effect_signature(card)
        blueprint = self.composition_blueprint(card)
        prompt = (
            f"chakana card::{cid}::{ctype} high density pixel fantasy, layered depth, "
            f"silhouette discipline, role {role}, rarity {rarity}, palette {palette}, lighting {lighting}, "
            f"sacred geometry {symbols}, symbolic overlays aligned to motif, motif {primary} ({shape}), "
            f"subject {blueprint['subject']}, object {blueprint['object']}, environment {blueprint['environment']}, "
            f"effect signature {effect_sig}, effects {blueprint['effects']}, energy pattern {energy}, lore tokens {lore_tokens}, "
            f"crisp no blur, intentional composition, illustrative fantasy finish, painterly readability, strong focal character"
        )
        return {
            "id": cid,
            "card_type": ctype,
            "family": ctype,
            "composition": blueprint,
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
        self._creative_director = CreativeArtDirector()

    def _set_id_from_prompt(self, prompt: str) -> str:
        low = str(prompt or "").lower()
        if "hiperboria" in low or "hiperborea" in low or "hip_" in low:
            return "hiperborea"
        if "archon" in low or "arconte" in low or "void" in low:
            return "archon"
        return "base"

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
        set_id = self._set_id_from_prompt(prompt)

        def _gen(target_path: Path, use_seed: int) -> dict:
            result_local = generate(card_id, card_type, prompt, use_seed, target_path)
            h_local = int(result_local.get("hash16", 0))
            if any(abs(h_local - prev) < 220 for prev in self._recent_hashes):
                result_local = generate(card_id, card_type, prompt, use_seed + 991, target_path)
                h_local = int(result_local.get("hash16", 0))
            result_local = dict(result_local)
            result_local["hash16"] = h_local
            return result_local

        result = self._creative_director.evolve(
            card_id=card_id,
            set_id=set_id,
            base_seed=seed,
            out_path=path,
            generate_fn=_gen,
            threshold=0.62 if str(rarity or "").lower() != "legendary" else 0.70,
        )

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
            "composition": dict(entry.get("composition", {})),
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
