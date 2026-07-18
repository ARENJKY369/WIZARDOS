"""Persistent statistics and achievements."""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
from utils.paths import USER_DATA


@dataclass
class Stats:
    daily_casts: int = 0
    weekly_casts: int = 0
    total_casts: int = 0
    average_accuracy: float = 0.0
    favorite_spell: str = "None"
    longest_combo: int = 0
    total_practice_time_seconds: int = 0
    highest_streak: int = 0
    achievements: list[str] = field(default_factory=list)


class StatsManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or USER_DATA / "stats.json"
        self.stats = self.load()

    def load(self) -> Stats:
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as f:
                return Stats(**json.load(f))
        return Stats()

    def save(self) -> None:
        self.path.parent.mkdir(exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(asdict(self.stats), f, indent=2)

    def record_cast(self, spell_name: str, accuracy: float) -> list[str]:
        s = self.stats
        s.total_casts += 1
        s.daily_casts += 1
        s.weekly_casts += 1
        s.average_accuracy = ((s.average_accuracy * (s.total_casts - 1)) + accuracy) / s.total_casts
        s.favorite_spell = spell_name
        unlocked: list[str] = []
        checks = {
            "First Spell": s.total_casts >= 1,
            "100 Casts": s.total_casts >= 100,
            "Perfect Accuracy": accuracy >= 0.98,
            "Fast Caster": accuracy >= 0.85,
            "Spell Master": s.total_casts >= 50 and s.average_accuracy >= 0.8,
            "Legendary Wizard": s.total_casts >= 500,
        }
        for name, ok in checks.items():
            if ok and name not in s.achievements:
                s.achievements.append(name)
                unlocked.append(name)
        self.save()
        return unlocked
