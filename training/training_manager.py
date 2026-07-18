"""Training scoring helpers for selected spell practice."""

from __future__ import annotations
from dataclasses import dataclass
from gesture.recognizer import GestureRecognizer


@dataclass
class TrainingScore:
    accuracy: float
    speed: float
    smoothness: float
    confidence: float
    suggestion: str


class TrainingManager:
    def __init__(self, recognizer: GestureRecognizer) -> None:
        self.recognizer = recognizer

    def score(self, points: list[tuple[float, float]], expected_gesture: str, duration_seconds: float) -> TrainingScore:
        result = self.recognizer.recognize(points)
        accuracy = result.confidence if result.gesture == expected_gesture else result.confidence * 0.5
        speed = max(0.0, min(1.0, 1.0 - abs(duration_seconds - 1.7) / 3.0))
        smoothness = self._smoothness(points)
        suggestions = []
        if accuracy < 0.7:
            suggestions.append("Trace the guide shape more completely")
        if speed < 0.55:
            suggestions.append("Aim for a steady medium casting speed")
        if smoothness < 0.65:
            suggestions.append("Relax your wrist to reduce jitter")
        return TrainingScore(accuracy, speed, smoothness, result.confidence, "; ".join(suggestions) or "Excellent wand control")

    def _smoothness(self, points: list[tuple[float, float]]) -> float:
        if len(points) < 4:
            return 0.0
        angles = []
        for a, b, c in zip(points, points[1:], points[2:]):
            v1 = (b[0] - a[0], b[1] - a[1])
            v2 = (c[0] - b[0], c[1] - b[1])
            n1 = max((v1[0] ** 2 + v1[1] ** 2) ** 0.5, 1e-6)
            n2 = max((v2[0] ** 2 + v2[1] ** 2) ** 0.5, 1e-6)
            dot = max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
            angles.append(abs(dot))
        return sum(angles) / len(angles)
