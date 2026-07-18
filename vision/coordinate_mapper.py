"""Coordinate mapping helper to convert between camera resolution and widget display."""

from __future__ import annotations


class CoordinateMapper:
    """Calculates forward and inverse coordinate mapping between camera resolution

    and centered KeepAspectRatio widget viewports.
    """

    def __init__(self) -> None:
        self.video_width: float = 1280.0
        self.video_height: float = 720.0
        self.widget_width: float = 640.0
        self.widget_height: float = 360.0

    def set_sizes(self, video_width: float, video_height: float, widget_width: float, widget_height: float) -> None:
        self.video_width = max(1.0, float(video_width))
        self.video_height = max(1.0, float(video_height))
        self.widget_width = max(1.0, float(widget_width))
        self.widget_height = max(1.0, float(widget_height))

    def to_widget(self, rx: float, ry: float) -> tuple[float, float]:
        scale = min(self.widget_width / self.video_width, self.widget_height / self.video_height)
        scaled_w = self.video_width * scale
        scaled_h = self.video_height * scale
        offset_x = (self.widget_width - scaled_w) / 2.0
        offset_y = (self.widget_height - scaled_h) / 2.0
        wx = offset_x + rx * scale
        wy = offset_y + ry * scale
        return wx, wy

    def to_video(self, wx: float, wy: float) -> tuple[float, float]:
        scale = min(self.widget_width / self.video_width, self.widget_height / self.video_height)
        scaled_w = self.video_width * scale
        scaled_h = self.video_height * scale
        offset_x = (self.widget_width - scaled_w) / 2.0
        offset_y = (self.widget_height - scaled_h) / 2.0
        if scale > 0.0:
            rx = (wx - offset_x) / scale
            ry = (wy - offset_y) / scale
            return rx, ry
        return 0.0, 0.0
