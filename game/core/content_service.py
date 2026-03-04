from __future__ import annotations

from pathlib import Path

from game.core.paths import data_dir
from game.core.safe_io import load_json


class ContentService:
    def __init__(self):
        self.base = data_dir()
        self.status = "OK"
        self.errors: list[str] = []
        self.cards = []
        self.enemies = []
        self.bosses = []
        self.dialogues_combat = {}
        self.dialogues_events = {}
        self.naming_style = ""
        self._load_all()

    def _fail(self, msg: str):
        self.status = "FALLBACK"
        self.errors.append(msg)

    def _safe_read_json(self, path: Path, fallback):
        data = load_json(path, default=None)
        if data is None:
            self._fail(f"missing_or_invalid:{path}")
            return fallback
        return data

    def _load_all(self):
        p_cards = self.base / "cards" / "cards_60.json"
        p_enemies = self.base / "enemies" / "enemies_30.json"
        p_bosses = self.base / "enemies" / "bosses_3.json"
        p_dcombat = self.base / "lore" / "dialogues_combat.json"
        p_devents = self.base / "lore" / "dialogues_events.json"

        cards = self._safe_read_json(p_cards, fallback=[])
        enemies = self._safe_read_json(p_enemies, fallback=[])
        bosses = self._safe_read_json(p_bosses, fallback=[])
        dcombat = self._safe_read_json(p_dcombat, fallback={})
        devents = self._safe_read_json(p_devents, fallback={})
        try:
            self.naming_style = (self.base / "lore" / "naming_style.txt").read_text(encoding="utf-8")
        except Exception:
            self.naming_style = ""
            self._fail(f"missing_or_invalid:{self.base / 'lore' / 'naming_style.txt'}")

        self.cards = cards if isinstance(cards, list) else []
        self.enemies = enemies if isinstance(enemies, list) else []
        self.bosses = bosses if isinstance(bosses, list) else []
        self.dialogues_combat = dcombat if isinstance(dcombat, dict) else {}
        self.dialogues_events = devents if isinstance(devents, dict) else {}

        if len(self.cards) != 60:
            self._fail(f"cards_count:{len(self.cards)} expected 60 @ {p_cards}")
        if len(self.enemies) != 30:
            self._fail(f"enemies_count:{len(self.enemies)} expected 30 @ {p_enemies}")
        if len(self.bosses) != 3:
            self._fail(f"bosses_count:{len(self.bosses)} expected 3 @ {p_bosses}")

        # dialogue coverage
        ids = [e.get("id") for e in self.enemies if isinstance(e, dict) and e.get("id")]
        for bid in [b.get("id") for b in self.bosses if isinstance(b, dict) and b.get("id")]:
            if bid not in ids:
                ids.append(bid)
        for eid in ids:
            item = self.dialogues_combat.get(eid)
            if not isinstance(item, dict) or "start" not in item:
                self._fail(f"dialogue_missing_start:{eid} @ {p_dcombat}")

    def debug_counts(self) -> dict:
        return {
            "cards": len(self.cards),
            "enemies": len(self.enemies),
            "bosses": len(self.bosses),
            "dialogues_combat": bool(self.dialogues_combat),
            "dialogues_events": bool(self.dialogues_events),
        }
