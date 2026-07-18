"""Record, label, import, and export custom local gestures."""
from __future__ import annotations
import json
from pathlib import Path
from .recognizer import Point
from utils.paths import USER_DATA


class CustomGestureStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or USER_DATA / "custom_gestures.json"
        self.gestures: dict[str, list[Point]] = self.load()

    def load(self) -> dict[str, list[Point]]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return {k: [tuple(p) for p in v] for k, v in raw.items()}

    def save(self) -> None:
        self.path.parent.mkdir(exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self.gestures, f, indent=2)

    def add(self, label: str, points: list[Point]) -> None:
        self.gestures[label] = points
        self.save()

    def export(self, destination: Path) -> None:
        with destination.open("w", encoding="utf-8") as f:
            json.dump(self.gestures, f, indent=2)

    def import_file(self, source: Path) -> None:
        with source.open("r", encoding="utf-8") as f:
            self.gestures.update(json.load(f))
        self.save()
