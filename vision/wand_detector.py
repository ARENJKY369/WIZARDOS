"""Classical computer-vision wand-tip detector.

The AI path uses MediaPipe for hands. This module adds a second, non-ML tracker that
looks for a thin bright/dark wand-like segment near the hand. It makes webcam mode
feel more advanced because users can cast with either their index finger or a pen,
chopstick, stylus, or reflective wand prop.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
import cv2
import numpy as np


@dataclass
class WandDetection:
    detected: bool
    tip: tuple[float, float] | None = None
    base: tuple[float, float] | None = None
    confidence: float = 0.0


class WandDetector:
    """Detects an elongated high-contrast wand and returns the farthest endpoint.

    The detector is intentionally lightweight: grayscale contrast enhancement,
    Canny edges, probabilistic Hough lines, then geometric scoring. If a hand tip
    exists, the wand endpoint farthest from the palm/index region is used as the
    magical tip. If no hand exists, the longest high-confidence line is used.
    """

    def __init__(self, min_length: int = 55) -> None:
        self.min_length = min_length

    def detect(self, frame_bgr: np.ndarray, hand_anchor: tuple[float, float] | None = None) -> WandDetection:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        gray = cv2.equalizeHist(gray)
        edges = cv2.Canny(gray, 45, 130)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=42,
            minLineLength=self.min_length,
            maxLineGap=14,
        )
        if lines is None:
            return WandDetection(False)

        best: tuple[float, tuple[int, int], tuple[int, int]] | None = None
        h, w = gray.shape[:2]
        diagonal = math.hypot(w, h)
        for raw in lines[:, 0, :]:
            x1, y1, x2, y2 = map(int, raw)
            length = math.hypot(x2 - x1, y2 - y1)
            if length < self.min_length:
                continue
            # Prefer lines near the hand when a hand is available; otherwise prefer length.
            anchor_bonus = 0.0
            if hand_anchor is not None:
                d1 = math.hypot(x1 - hand_anchor[0], y1 - hand_anchor[1])
                d2 = math.hypot(x2 - hand_anchor[0], y2 - hand_anchor[1])
                anchor_bonus = 1.0 - min(d1, d2) / max(diagonal * 0.55, 1.0)
            score = length / diagonal + max(0.0, anchor_bonus) * 0.75
            if best is None or score > best[0]:
                best = (score, (x1, y1), (x2, y2))

        if best is None:
            return WandDetection(False)
        score, a, b = best
        if hand_anchor is not None:
            da = math.hypot(a[0] - hand_anchor[0], a[1] - hand_anchor[1])
            db = math.hypot(b[0] - hand_anchor[0], b[1] - hand_anchor[1])
            tip, base = (a, b) if da > db else (b, a)
        else:
            tip, base = b, a
        confidence = max(0.0, min(1.0, score * 2.1))
        return WandDetection(True, (float(tip[0]), float(tip[1])), (float(base[0]), float(base[1])), confidence)
