"""Centralized Wand Controller module."""

from __future__ import annotations
import time
from collections import deque
from .coordinate_mapper import CoordinateMapper


class WandController:
    """The Wand Controller is the single source of truth for the active wand's position.

    It coordinates tracking data from the hand tracker, camera feed, gesture recognition,
    and OpenGL rendering modules using a shared coordinate mapper.
    """

    def __init__(self, max_stroke_len: int = 220) -> None:
        self.mapper = CoordinateMapper()
        self.current_tip: tuple[float, float] | None = None
        self.velocity: float = 0.0
        self.confidence: float = 0.0
        self.source: str = "none"
        self.detected: bool = False
        self.last_tip_time: float = 0.0

        # Centralized active stroke in standard video/camera coordinates
        self.stroke: deque[tuple[float, float]] = deque(maxlen=max_stroke_len)

    def update_position(
        self,
        detected: bool,
        tip: tuple[float, float] | None,
        source: str,
        confidence: float,
        velocity: float,
        stroke_timeout_ms: float = 850.0,
    ) -> None:
        self.detected = detected
        self.current_tip = tip
        self.source = source
        self.confidence = confidence
        self.velocity = velocity

        now = time.monotonic()
        if detected and tip is not None:
            self.last_tip_time = now
            # Ignore tiny hover jitter; record only deliberate movement or a new stroke
            if velocity > 35.0 or len(self.stroke) < 4:
                self.stroke.append(tip)
        elif now - self.last_tip_time > (stroke_timeout_ms / 1000.0):
            self.stroke.clear()

    def add_widget_point(self, wx: float, wy: float) -> None:
        """Add a stroke point drawn with the mouse (in widget coordinates) back into video coordinates."""
        rx, ry = self.mapper.to_video(wx, wy)
        self.stroke.append((rx, ry))

    def clear_stroke(self) -> None:
        self.stroke.clear()

    def get_widget_tip(self) -> tuple[float, float] | None:
        if self.current_tip is None:
            return None
        return self.mapper.to_widget(*self.current_tip)

    def get_widget_stroke(self) -> list[tuple[float, float]]:
        return [self.mapper.to_widget(x, y) for x, y in self.stroke]
