from __future__ import annotations

from dataclasses import dataclass, field
import copy
from pathlib import Path

from game.core.paths import data_dir
from game.core.safe_io import load_json


@dataclass
class ContentStatus:
    status: str = "OK"
    errors: list[str] = field(default_factory=list)




_CONTENT_CACHE = {"stamp": None, "payload": None}

class ContentService:
    def __init__(self, base: Path | None = None):
        project_root = Path(__file__).resolve().parents[2]
        fallback = project_root / "game" / "data"
        self.base = base or (fallback if fallback.exists() else data_dir())

    def _source_stamp(self):
        files = [
            self.base / "cards.json",
            self.base / "enemies" / "enemies_30.json",
            self.base / "enemies" / "bosses_3.json",
            self.base / "lore" / "dialogues_combat.json",
            self.base / "lore" / "dialogues_events.json",
        ]
        stamp = []
        for f in files:
            try:
                stamp.append((str(f), int(f.stat().st_mtime_ns)))
            except Exception:
                stamp.append((str(f), -1))
        return tuple(stamp)

    def _step(self, progress_cb, label, pct):
        if progress_cb:
            progress_cb(label, pct)

    def _read_json(self, path: Path, fallback, status: ContentStatus):
        data = load_json(path, default=None)
        if data is None:
            status.status = "FALLBACK"
            status.errors.append(f"missing_or_invalid:{path}")
            return fallback
        return data

    def load_cards(self, status: ContentStatus):
        return self._read_json(self.base / "cards.json", [], status)

    def load_enemies(self, status: ContentStatus):
        return self._read_json(self.base / "enemies" / "enemies_30.json", [], status)

    def load_bosses(self, status: ContentStatus):
        return self._read_json(self.base / "enemies" / "bosses_3.json", [], status)

    def load_dialogues(self, status: ContentStatus):
        c = self._read_json(self.base / "lore" / "dialogues_combat.json", {}, status)
        e = self._read_json(self.base / "lore" / "dialogues_events.json", {}, status)
        return c if isinstance(c, dict) else {}, e if isinstance(e, dict) else {}

    def load_all(self, progress_cb=None) -> dict:
        stamp = self._source_stamp()
        if _CONTENT_CACHE.get("stamp") == stamp and isinstance(_CONTENT_CACHE.get("payload"), dict):
            return copy.deepcopy(_CONTENT_CACHE["payload"])

        st = ContentStatus()
        self._step(progress_cb, "Cargando cartas", 0.05)
        cards = self.load_cards(st)
        self._step(progress_cb, "Cargando enemigos", 0.12)
        enemies = self.load_enemies(st)
        self._step(progress_cb, "Cargando jefes", 0.18)
        bosses = self.load_bosses(st)
        self._step(progress_cb, "Cargando diálogos", 0.24)
        dcombat, devents = self.load_dialogues(st)

        if len(cards) != 30:
            st.status = "FALLBACK"; st.errors.append(f"cards_count:{len(cards)} expected 30")
        if len(enemies) != 31:
            st.status = "FALLBACK"; st.errors.append(f"enemies_count:{len(enemies)} expected 31")
        if len(bosses) != 4:
            st.status = "FALLBACK"; st.errors.append(f"bosses_count:{len(bosses)} expected 4")

        enemy_ids = [e.get("id") for e in enemies if isinstance(e, dict) and e.get("id")]
        for eid in enemy_ids:
            row = dcombat.get(eid) if isinstance(dcombat, dict) else None
            if not isinstance(row, dict) or "start" not in row:
                dcombat[eid] = {
                    "start": {"enemy": "La Trama te prueba.", "chakana": "Respiro. Calculo. Ejecuto."},
                    "victory": {"enemy": "Aún no termina.", "chakana": "Sigo en pie."},
                }

        payload = {
            "cards": cards if isinstance(cards, list) else [],
            "enemies": enemies if isinstance(enemies, list) else [],
            "bosses": bosses if isinstance(bosses, list) else [],
            "dialogues_combat": dcombat,
            "dialogues_events": devents,
            "status": st.status,
            "errors": st.errors,
        }
        _CONTENT_CACHE["stamp"] = stamp
        _CONTENT_CACHE["payload"] = copy.deepcopy(payload)
        return payload
