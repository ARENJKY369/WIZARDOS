"""MediaPipe Hands + wand detection wrapper."""

from __future__ import annotations
from dataclasses import dataclass
from collections import deque
import time
import numpy as np
from .wand_detector import WandDetector, WandDetection

try:  # Optional at runtime for documentation builds/tests.
    import mediapipe as mp
except Exception:  # pragma: no cover
    mp = None  # type: ignore


@dataclass
class HandTrackingResult:
    detected: bool
    tip: tuple[float, float] | None
    landmarks: list[tuple[float, float]]
    source: str = "none"  # "wand", "finger", or "none"
    confidence: float = 0.0
    velocity: float = 0.0
    wand: WandDetection | None = None


class OneEuroLikeSmoother:
    """Adaptive exponential smoother tuned for low-latency cursor/wand motion."""

    def __init__(self, alpha: float = 0.68, fast_alpha: float = 0.38, fast_speed: float = 900.0) -> None:
        self.alpha = alpha
        self.fast_alpha = fast_alpha
        self.fast_speed = fast_speed
        self.value: np.ndarray | None = None
        self.last_time: float | None = None

    def update(self, point: tuple[float, float]) -> tuple[tuple[float, float], float]:
        now = time.perf_counter()
        p = np.array(point, dtype=np.float32)
        velocity = 0.0
        if self.value is None:
            self.value = p
        else:
            dt = max(now - (self.last_time or now), 1e-3)
            velocity = float(np.linalg.norm(p - self.value) / dt)
            # Less smoothing during fast spell strokes, more smoothing while hovering.
            t = max(0.0, min(1.0, velocity / self.fast_speed))
            alpha = self.alpha * (1 - t) + self.fast_alpha * t
            self.value = alpha * self.value + (1 - alpha) * p
        self.last_time = now
        return (float(self.value[0]), float(self.value[1])), velocity


class HandTracker:
    def __init__(
        self,
        detection_confidence: float = 0.55,
        tracking_confidence: float = 0.5,
        smoothing: float = 0.68,
        prefer_wand: bool = True,
    ) -> None:
        self.smoother = OneEuroLikeSmoother(alpha=smoothing)
        self.tip_history: deque[tuple[float, float]] = deque(maxlen=256)
        self.wand_detector = WandDetector()
        self.prefer_wand = prefer_wand
        if mp is None:
            self.hands = None
        else:
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                model_complexity=1,
                min_detection_confidence=detection_confidence,
                min_tracking_confidence=tracking_confidence,
            )

    def process(self, frame_bgr: np.ndarray) -> HandTrackingResult:
        landmarks: list[tuple[float, float]] = []
        finger_tip: tuple[float, float] | None = None
        detected = False
        hand_confidence = 0.0

        if self.hands is not None:
            rgb = frame_bgr[:, :, ::-1]
            result = self.hands.process(rgb)
            if result.multi_hand_landmarks:
                h, w = frame_bgr.shape[:2]
                landmarks = [(lm.x * w, lm.y * h) for lm in result.multi_hand_landmarks[0].landmark]
                finger_tip = landmarks[8]
                detected = True
                hand_confidence = 0.82

        wand = self.wand_detector.detect(frame_bgr, finger_tip if detected else None)
        raw_tip: tuple[float, float] | None = None
        source = "none"
        confidence = 0.0
        if self.prefer_wand and wand.detected and wand.tip is not None and wand.confidence >= 0.32:
            raw_tip = wand.tip
            source = "wand"
            confidence = max(wand.confidence, hand_confidence)
            detected = True
        elif finger_tip is not None:
            raw_tip = finger_tip
            source = "finger"
            confidence = hand_confidence

        if raw_tip is None:
            return HandTrackingResult(False, None, landmarks, "none", 0.0, 0.0, wand)

        tip, velocity = self.smoother.update(raw_tip)
        self.tip_history.append(tip)
        return HandTrackingResult(detected, tip, landmarks, source, confidence, velocity, wand)

    def close(self) -> None:
        if self.hands is not None:
            self.hands.close()
