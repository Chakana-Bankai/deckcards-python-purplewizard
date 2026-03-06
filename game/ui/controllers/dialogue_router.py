from __future__ import annotations

import pygame


class DialogueRouter:
    PRIORITY = {
        "defeat": 100,
        "victory": 90,
        "seal_release": 86,
        "seal_ready": 82,
        "player_low_hp": 80,
        "enemy_low_hp": 75,
        "big_damage": 72,
        "combat_start": 70,
        "enemy_attack": 64,
        "attack": 58,
        "card_played": 52,
    }

    ALIASES = {
        "start": "combat_start",
        "turn_start": "enemy_attack",
        "enemy_turn_start": "enemy_attack",
        "enemy_intent_set": "enemy_attack",
        "enemy_big_attack": "big_damage",
        "low_hp_player": "player_low_hp",
        "low_hp_enemy": "enemy_low_hp",
        "enemy_low_hp": "enemy_low_hp",
        "player_low_hp": "player_low_hp",
        "card_played_attack": "attack",
        "card_played_block": "card_played",
        "card_played_ritual": "card_played",
        "card_played_defense": "card_played",
        "card_played_utility": "card_played",
        "harmony_ready": "seal_ready",
        "harmony_seal": "seal_release",
    }

    FALLBACK = {
        "combat_start": ("La geometria tiembla ante tu llegada.", "Trazo la cruz andina y alineo mi pulso."),
        "card_played": ("Un gesto no basta para quebrar el astral.", "Cada carta ordena un angulo del rito."),
        "attack": ("Golpeas la forma, no su nucleo.", "Corto el velo con precision ritual."),
        "big_damage": ("El impacto abre grietas en tu mandala.", "Sostengo el eje, no cedo al ruido."),
        "enemy_attack": ("Ataco cuando la figura se desequilibra.", "Leo tu vector antes de que nazca."),
        "player_low_hp": ("Tu constelacion se deshace.", "Respiro hondo: la Trama aun responde."),
        "enemy_low_hp": ("No... mi patron se colapsa.", "Tu patron pierde simetria."),
        "seal_ready": ("Siento el sello vibrar en el eter.", "La Chakana se enciende: umbral completo."),
        "seal_release": ("Ese pulso... me desgarra.", "Libero el sello y cierro el circuito."),
        "victory": ("La espiral se apaga.", "El rito concluye en equilibrio."),
        "defeat": ("Hoy gana la sombra.", "Recojo los fragmentos y vuelvo."),
    }

    def __init__(self, lore_engine, cooldown_ms: int = 800, action_gap: int = 2):
        self.lore_engine = lore_engine
        self.cooldown_ms = max(150, int(cooldown_ms))
        self.action_gap = max(1, int(action_gap))
        self.last_ms = 0
        self.last_priority = -1
        self.last_action_index = -999

    def _norm(self, trigger: str, ctx: dict) -> str:
        trig = self.ALIASES.get(str(trigger or ""), str(trigger or "combat_start"))
        if trig == "enemy_attack":
            intent = str((ctx or {}).get("intent", "")).lower()
            if intent and not any(k in intent for k in ["ata", "attack", "golpe", "strike"]):
                return "card_played"
        return trig

    def pick(self, enemy_id: str, trigger: str, ctx: dict | None = None) -> tuple[str, str, str] | None:
        ctx = ctx or {}
        now = pygame.time.get_ticks()
        trig = self._norm(trigger, ctx)
        prio = self.PRIORITY.get(trig, 20)
        action_index = int(ctx.get("action_index", self.last_action_index + 1))
        forced = trig in {"defeat", "victory", "combat_start", "seal_release"}
        critical = prio >= 75

        too_soon_ms = (now - self.last_ms) < self.cooldown_ms
        too_soon_actions = (action_index - self.last_action_index) < self.action_gap
        if not forced and (too_soon_ms or too_soon_actions) and not critical and prio <= self.last_priority:
            return None

        enemy, hero = self.lore_engine.get_combat_lines(enemy_id, trig)
        if not enemy.strip() or not hero.strip():
            enemy, hero = self.FALLBACK.get(trig, ("...", "..."))

        self.last_ms = now
        self.last_priority = prio
        self.last_action_index = action_index
        return enemy, hero, trig
