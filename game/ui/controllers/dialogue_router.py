from __future__ import annotations

import pygame


class DialogueRouter:
    PRIORITY = {
        "defeat": 100,
        "victory": 90,
        "low_hp_player": 80,
        "low_hp_enemy": 75,
        "combat_start": 70,
        "enemy_intent_set": 60,
        "card_played_attack": 55,
        "card_played_block": 52,
        "card_played_ritual": 50,
    }

    ALIASES = {
        "start": "combat_start",
        "turn_start": "enemy_intent_set",
        "enemy_low_hp": "low_hp_enemy",
        "player_low_hp": "low_hp_player",
        "card_played_defense": "card_played_block",
        "card_played_utility": "card_played_ritual",
    }

    FALLBACK = {
        "combat_start": ("La Trama te observa.", "Respiro y marco el pulso."),
        "enemy_intent_set": ("Ya decidí el próximo paso.", "Leo tu intención antes del golpe."),
        "card_played_attack": ("Eso apenas rasga el velo.", "Cada ataque dibuja destino."),
        "card_played_block": ("Un muro no basta.", "Bloqueo y vuelvo con temple."),
        "card_played_ritual": ("Rituales... interesante.", "La Chakana ordena este caos."),
        "low_hp_enemy": ("No caeré...", "Tu forma ya se quiebra."),
        "low_hp_player": ("Tu fin se acerca.", "Todavía no termina."),
        "victory": ("...", "La Trama se inclina a mi paso."),
        "defeat": ("Otro hilo cortado.", "Aprenderé de esta caída."),
    }

    def __init__(self, lore_engine, cooldown_ms: int = 800):
        self.lore_engine = lore_engine
        self.cooldown_ms = max(150, int(cooldown_ms))
        self.last_ms = 0
        self.last_priority = -1

    def _norm(self, trigger: str) -> str:
        return self.ALIASES.get(str(trigger or ""), str(trigger or "combat_start"))

    def pick(self, enemy_id: str, trigger: str, ctx: dict | None = None) -> tuple[str, str, str] | None:
        _ = ctx or {}
        now = pygame.time.get_ticks()
        trig = self._norm(trigger)
        prio = self.PRIORITY.get(trig, 20)
        forced = trig in {"defeat", "victory", "combat_start"}
        if not forced and (now - self.last_ms < self.cooldown_ms) and prio <= self.last_priority:
            return None
        enemy, hero = self.lore_engine.get_combat_lines(enemy_id, trig)
        if not enemy.strip() or not hero.strip():
            enemy, hero = self.FALLBACK.get(trig, ("...", "..."))
        self.last_ms = now
        self.last_priority = prio
        return enemy, hero, trig
