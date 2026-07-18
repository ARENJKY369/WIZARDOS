"""Template-based gesture recognizer inspired by the $1 recognizer.

It is fast, deterministic, trainable from examples, and tolerant of drawing speed,
translation, and scale. Custom examples can be persisted as JSON.
"""
from __future__ import annotations
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import numpy as np

Point = tuple[float, float]


@dataclass
class RecognitionResult:
    gesture: str
    confidence: float
    distance: float


class GestureRecognizer:
    def __init__(self, templates: dict[str, list[Point]] | None = None, sample_count: int = 64) -> None:
        self.sample_count = sample_count
        self.templates: dict[str, np.ndarray] = {}
        self.rotation_angles = np.deg2rad(np.array([-18, -12, -6, 0, 6, 12, 18], dtype=np.float32))
        for name, pts in (templates or default_templates()).items():
            self.add_template(name, pts)

    def add_template(self, name: str, points: Iterable[Point]) -> None:
        pts = list(points)
        if len(pts) < 3:
            raise ValueError("A gesture template needs at least 3 points")
        self.templates[name] = self.normalize(pts)

    def recognize(self, points: Iterable[Point]) -> RecognitionResult:
        pts = list(points)
        if len(pts) < 8 or not self.templates:
            return RecognitionResult("unknown", 0.0, float("inf"))
        candidate = self.normalize(pts)
        best_name = "unknown"
        best_dist = float("inf")
        for name, template in self.templates.items():
            # Direction is intentionally preserved so circle and reverse_circle remain distinct.
            # We do a small rotation search to tolerate camera tilt and different casting angles.
            dist = self._best_rotated_distance(candidate, template)
            if dist < best_dist:
                best_dist = dist
                best_name = name
        # A normalized mean distance of 0 is perfect; ~0.38 is poor.
        confidence = max(0.0, min(1.0, 1.0 - best_dist / 0.38))
        return RecognitionResult(best_name, confidence, best_dist)

    def normalize(self, points: Iterable[Point]) -> np.ndarray:
        arr = np.array(list(points), dtype=np.float32)
        arr = self._resample(arr, self.sample_count)
        arr -= arr.mean(axis=0)
        scale = max(float(np.max(np.ptp(arr, axis=0))), 1e-6)
        arr /= scale
        return arr

    def _best_rotated_distance(self, candidate: np.ndarray, template: np.ndarray) -> float:
        best = float("inf")
        for angle in self.rotation_angles:
            c, s = float(np.cos(angle)), float(np.sin(angle))
            rot = np.array([[c, -s], [s, c]], dtype=np.float32)
            rotated = candidate @ rot.T
            dist = float(np.mean(np.linalg.norm(rotated - template, axis=1)))
            if dist < best:
                best = dist
        return best

    def save_custom_templates(self, path: Path) -> None:
        data = {name: pts.tolist() for name, pts in self.templates.items()}
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_custom_templates(self, path: Path) -> None:
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as f:
            for name, pts in json.load(f).items():
                self.add_template(name, pts)

    def _resample(self, points: np.ndarray, n: int) -> np.ndarray:
        if len(points) == n:
            return points.copy()
        deltas = np.diff(points, axis=0)
        distances = np.linalg.norm(deltas, axis=1)
        cumulative = np.concatenate([[0.0], np.cumsum(distances)])
        total = cumulative[-1]
        if total < 1e-6:
            return np.repeat(points[:1], n, axis=0)
        targets = np.linspace(0, total, n)
        x = np.interp(targets, cumulative, points[:, 0])
        y = np.interp(targets, cumulative, points[:, 1])
        return np.stack([x, y], axis=1).astype(np.float32)


def _poly(points: list[Point], close: bool = False) -> list[Point]:
    if close:
        points = points + [points[0]]
    out: list[Point] = []
    for a, b in zip(points, points[1:]):
        for t in np.linspace(0, 1, 12, endpoint=False):
            out.append((a[0] * (1 - t) + b[0] * t, a[1] * (1 - t) + b[1] * t))
    out.append(points[-1])
    return out


def default_templates() -> dict[str, list[Point]]:
    circle = [(math.cos(t), math.sin(t)) for t in np.linspace(0, 2 * math.pi, 96)]
    reverse_circle = list(reversed(circle))
    spiral = [(t / 7 * math.cos(t), t / 7 * math.sin(t)) for t in np.linspace(0.2, 4 * math.pi, 96)]
    heart = [(16 * math.sin(t) ** 3 / 18, -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t)) / 18) for t in np.linspace(0, 2*math.pi, 96)]
    infinity = [(math.sin(t), math.sin(t) * math.cos(t)) for t in np.linspace(0, 2 * math.pi, 96)]
    wave = [(x, 0.45 * math.sin(2.8 * x)) for x in np.linspace(-1, 1, 96)]
    star_points = []
    for i in range(5):
        a = -math.pi/2 + i * 2*math.pi/5
        star_points.append((math.cos(a), math.sin(a)))
        a2 = a + math.pi/5
        star_points.append((0.42*math.cos(a2), 0.42*math.sin(a2)))
    return {
        "circle": circle,
        "reverse_circle": reverse_circle,
        "triangle": _poly([(0, -1), (0.92, 0.65), (-0.92, 0.65)], True),
        "square": _poly([(-1, -1), (1, -1), (1, 1), (-1, 1)], True),
        "star": _poly(star_points, True),
        "heart": heart,
        "lightning": _poly([(-0.4, -1), (0.35, -0.2), (-0.05, -0.2), (0.45, 1)]),
        "spiral": spiral,
        "infinity": infinity,
        "x": _poly([(-1, -1), (1, 1), (0, 0), (1, -1), (-1, 1)]),
        "z": _poly([(-1, -1), (1, -1), (-1, 1), (1, 1)]),
        "wave": wave,
    }
