"""Spell database, cooldowns, and persistent mastery stats."""

from __future__ import annotations
import json
import time
from pathlib import Path
from .spell import Spell
from utils.paths import SPELLBOOK, USER_DATA


class SpellbookManager:
    def __init__(self, path: Path | None = None) -> None:
        self.source_path = path or SPELLBOOK / "spells.json"
        self.user_path = USER_DATA / "spellbook.json"
        self.spells: list[Spell] = self.load()
        self._last_cast: dict[str, float] = {}

    def load(self) -> list[Spell]:
        path = self.user_path if self.user_path.exists() else self.source_path
        with path.open("r", encoding="utf-8") as f:
            return [Spell.from_dict(item) for item in json.load(f)]

    def save(self) -> None:
        self.user_path.parent.mkdir(exist_ok=True)
        with self.user_path.open("w", encoding="utf-8") as f:
            json.dump([s.to_dict() for s in self.spells], f, indent=2)

    def by_gesture(self, gesture: str) -> Spell | None:
        matches = [s for s in self.spells if s.gesture == gesture]
        if not matches:
            return None
        favorites = [s for s in matches if s.favorite]
        return (favorites or matches)[0]

    def can_cast(self, spell: Spell) -> tuple[bool, float]:
        elapsed = time.monotonic() - self._last_cast.get(spell.name, 0)
        remaining = max(0.0, spell.cooldown - elapsed)
        return remaining <= 0.0, remaining

    def record_cast(self, spell: Spell, accuracy: float) -> None:
        self._last_cast[spell.name] = time.monotonic()
        spell.times_cast += 1
        spell.accuracy = ((spell.accuracy * (spell.times_cast - 1)) + accuracy) / spell.times_cast
        spell.mastery_level = min(100, int(spell.accuracy * 100))
        self.save()
