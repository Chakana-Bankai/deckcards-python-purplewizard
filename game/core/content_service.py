from __future__ import annotations

import json
from pathlib import Path

from game.core.paths import data_dir
from game.core.safe_io import load_json


class ContentService:
    def __init__(self):
        self.base = data_dir()
        self.status = "OK"
        self.cards = []
        self.enemies = []
        self.bosses = []
        self.dialogues_combat = {}
        self.dialogues_events = {}
        self.naming_style = ""
        self._load_all()

    def _safe_read_json(self, path: Path, fallback):
        data = load_json(path, default=fallback)
        if not data:
            self.status = "FALLBACK"
            return fallback
        return data

    def _load_all(self):
        cards = self._safe_read_json(self.base / "cards" / "cards_60.json", fallback=[])
        enemies = self._safe_read_json(self.base / "enemies" / "enemies_30.json", fallback=[])
        bosses = self._safe_read_json(self.base / "enemies" / "bosses_3.json", fallback=[])
        dcombat = self._safe_read_json(self.base / "lore" / "dialogues_combat.json", fallback={})
        devents = self._safe_read_json(self.base / "lore" / "dialogues_events.json", fallback={})
        try:
            self.naming_style = (self.base / "lore" / "naming_style.txt").read_text(encoding="utf-8")
        except Exception:
            self.naming_style = ""
            self.status = "FALLBACK"
        self.cards = cards if isinstance(cards, list) else []
        self.enemies = enemies if isinstance(enemies, list) else []
        self.bosses = bosses if isinstance(bosses, list) else []
        self.dialogues_combat = dcombat if isinstance(dcombat, dict) else {}
        self.dialogues_events = devents if isinstance(devents, dict) else {}
