"""QOpenGLWidget renderer for trails, particles, and spell bursts."""

from __future__ import annotations
import time
from collections import deque
from PySide6.QtCore import Qt, QTimer, QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QRadialGradient, QMouseEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from effects.particle_engine import ParticleEngine
from vision.wand_controller import WandController


class MagicRenderer(QOpenGLWidget):
    mouse_stroke_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.engine = ParticleEngine()
        self.trail: deque[QPointF] = deque(maxlen=72)
        self.mouse_stroke: list[tuple[float, float]] = []
        self._last = time.perf_counter()
        self._current_color = QColor("#75E7FF")
        self._status_text = ""
        self.wand_controller: WandController | None = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

    def set_wand_controller(self, wand_controller: WandController) -> None:
        self.wand_controller = wand_controller

    def update_tip(self, tip: tuple[float, float] | None, source_size: tuple[int, int] | None = None) -> None:
        if tip is None:
            return
        
        # Sync mapper size in wand_controller
        if self.wand_controller and source_size:
            sw, sh = source_size
            self.wand_controller.mapper.set_sizes(sw, sh, self.width(), self.height())
            wx, wy = self.wand_controller.mapper.to_widget(tip[0], tip[1])
            self.trail.append(QPointF(wx, wy))
        else:
            # Fallback for old/direct behavior
            x, y = tip
            if source_size:
                sw, sh = source_size
                if sw > 0 and sh > 0:
                    x = x / sw * self.width()
                    y = y / sh * self.height()
            self.trail.append(QPointF(x, y))

    def cast_effect(self, effect: str, color: str, text: str) -> None:
        self._current_color = QColor(color)
        origin_pt = None
        if self.wand_controller:
            tip = self.wand_controller.get_widget_tip()
            if tip:
                origin_pt = QPointF(tip[0], tip[1])
            else:
                stroke = self.wand_controller.get_widget_stroke()
                if stroke:
                    origin_pt = QPointF(stroke[-1][0], stroke[-1][1])
        if origin_pt is None:
            origin_pt = self.trail[-1] if self.trail else QPointF(self.width() / 2, self.height() / 2)
        self.engine.burst(origin_pt.x(), origin_pt.y(), self._current_color, effect)
        self._status_text = text

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = min(0.05, now - self._last)
        self._last = now
        self.engine.update(dt, self.width(), self.height())
        if self.wand_controller:
            tip = self.wand_controller.get_widget_tip()
            if tip:
                self.engine.add_trail_particles(tip[0], tip[1], self._current_color, amount=3)
        self.update()

    def paintGL(self) -> None:
        if self.wand_controller:
            # Maintain mapper widget size synchronization on paint
            self.wand_controller.mapper.set_sizes(
                self.wand_controller.mapper.video_width,
                self.wand_controller.mapper.video_height,
                self.width(),
                self.height(),
            )
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_background(painter)
        self._paint_particles(painter)
        self._paint_trail(painter)
        self._paint_status(painter)
        painter.end()

    def _paint_background(self, painter: QPainter) -> None:
        grad = QRadialGradient(self.rect().center(), max(self.width(), self.height()) * 0.7)
        grad.setColorAt(0, QColor(18, 38, 80, 95))
        grad.setColorAt(1, QColor(2, 4, 10, 210))
        painter.fillRect(self.rect(), grad)

    def _paint_particles(self, painter: QPainter) -> None:
        for p in self.engine.particles:
            alpha = int(max(0, min(255, p.color.alpha() * (p.life / max(p.max_life, 0.01)))))
            c = QColor(p.color)
            c.setAlpha(alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(c))
            painter.drawEllipse(p.pos, p.size, p.size)

    def _paint_trail(self, painter: QPainter) -> None:
        if self.wand_controller:
            stroke = self.wand_controller.get_widget_stroke()
            if len(stroke) >= 2:
                points = [QPointF(pt[0], pt[1]) for pt in stroke]
                for i in range(1, len(points)):
                    strength = i / len(points)
                    c = QColor(self._current_color)
                    c.setAlpha(int(30 + 190 * strength))
                    pen = QPen(c, 2 + 10 * strength, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    painter.setPen(pen)
                    painter.drawLine(points[i - 1], points[i])
            tip = self.wand_controller.get_widget_tip()
            if tip:
                head = QPointF(tip[0], tip[1])
                painter.setBrush(QBrush(QColor(220, 250, 255, 230)))
                painter.setPen(QPen(QColor(120, 235, 255), 2))
                painter.drawEllipse(head, 8, 8)
        else:
            if len(self.trail) < 2:
                return
            points = list(self.trail)
            for i in range(1, len(points)):
                strength = i / len(points)
                c = QColor(self._current_color)
                c.setAlpha(int(30 + 190 * strength))
                pen = QPen(c, 2 + 10 * strength, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.drawLine(points[i - 1], points[i])
            head = points[-1]
            painter.setBrush(QBrush(QColor(220, 250, 255, 230)))
            painter.setPen(QPen(QColor(120, 235, 255), 2))
            painter.drawEllipse(head, 8, 8)

    def _paint_status(self, painter: QPainter) -> None:
        if not self._status_text:
            return
        painter.setPen(QPen(QColor("#F5D476"), 2))
        painter.drawText(24, self.height() - 28, self._status_text)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        p = event.position()
        if self.wand_controller:
            self.wand_controller.clear_stroke()
            rx, ry = self.wand_controller.mapper.to_video(p.x(), p.y())
            self.wand_controller.update_position(True, (rx, ry), "mouse", 1.0, 100.0)
            self.wand_controller.add_widget_point(p.x(), p.y())
            self.mouse_stroke = list(self.wand_controller.stroke)
        self.trail.clear()
        self.trail.append(p)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        p = event.position()
        if event.buttons() & Qt.MouseButton.LeftButton:
            if self.wand_controller:
                rx, ry = self.wand_controller.mapper.to_video(p.x(), p.y())
                self.wand_controller.update_position(True, (rx, ry), "mouse", 1.0, 100.0)
                self.wand_controller.add_widget_point(p.x(), p.y())
                self.mouse_stroke = list(self.wand_controller.stroke)
                self.mouse_stroke_changed.emit(self.mouse_stroke)
            self.trail.append(p)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.wand_controller:
            self.wand_controller.update_position(False, None, "none", 0.0, 0.0)
            self.mouse_stroke_changed.emit(list(self.wand_controller.stroke))
