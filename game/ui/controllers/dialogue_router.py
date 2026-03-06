from __future__ import annotations

import pygame


class DialogueRouter:
    PRIORITY = {
        "defeat": 100,
        "victory": 92,
        "seal_release": 88,
        "seal_ready": 82,
        "player_low_hp": 80,
        "enemy_low_hp": 76,
        "enemy_intent": 66,
        "attack_played": 60,
        "block_played": 56,
        "combat_start": 70,
    }

    ALIASES = {
        "start": "combat_start",
        "turn_start": "enemy_intent",
        "enemy_turn_start": "enemy_intent",
        "enemy_intent_set": "enemy_intent",
        "card_played_attack": "attack_played",
        "card_played_block": "block_played",
        "card_played_ritual": "block_played",
        "card_played_defense": "block_played",
        "card_played_utility": "block_played",
        "harmony_ready": "seal_ready",
        "harmony_seal": "seal_release",
        "low_hp_player": "player_low_hp",
        "low_hp_enemy": "enemy_low_hp",
    }

    FALLBACK = {
        "combat_start": ("La arena astral ya despierta.", "Trazo la Chakana y fijo el pulso."),
        "enemy_intent": ("Mi proximo vector ya esta marcado.", "Leo tu intencion antes del impacto."),
        "attack_played": ("Tu filo altera mi patron.", "Golpeo el nodo donde cede la forma."),
        "block_played": ("Tu barrera cambia el ritmo.", "Defiendo y recoloco la geometria."),
        "seal_ready": ("Ese sello irradia peligro.", "El sello vibra: umbral completo."),
        "seal_release": ("Ese pulso rasga mi plano.", "Libero el sello y cierro el ciclo."),
        "player_low_hp": ("Tu constelacion se debilita.", "Sostengo el eje aunque sangre."),
        "enemy_low_hp": ("Mi contorno se quiebra.", "Tu patron se derrumba ante la Trama."),
        "victory": ("La espiral se apaga.", "El rito concluye en equilibrio."),
        "defeat": ("Hoy manda la sombra.", "Caigo, aprendo y regreso."),
    }

    def __init__(self, lore_engine, cooldown_ms: int = 900, action_gap: int = 2):
        self.lore_engine = lore_engine
        self.cooldown_ms = max(200, int(cooldown_ms))
        self.action_gap = max(1, int(action_gap))
        self.last_ms = 0
        self.last_priority = -1
        self.last_action_index = -999

    def _norm(self, trigger: str, ctx: dict) -> str:
        trig = self.ALIASES.get(str(trigger or ""), str(trigger or "combat_start"))
        if trig == "enemy_intent":
            intent = str((ctx or {}).get("intent", "")).lower()
            if intent and not any(k in intent for k in ["ata", "attack", "golpe", "strike"]):
                return "enemy_intent"
        return trig

    def pick(self, enemy_id: str, trigger: str, ctx: dict | None = None) -> tuple[str, str, str] | None:
        ctx = ctx or {}
        now = pygame.time.get_ticks()
        trig = self._norm(trigger, ctx)
        prio = self.PRIORITY.get(trig, 20)
        action_index = int(ctx.get("action_index", self.last_action_index + 1))

        forced = trig in {"combat_start", "seal_release", "victory", "defeat"}
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
