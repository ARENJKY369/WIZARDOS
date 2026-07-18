"""Qt camera worker that captures frames and runs hand/wand tracking off the UI thread."""

from __future__ import annotations
import time
import cv2
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from vision.hand_tracker import HandTracker, HandTrackingResult


class CameraWorker(QThread):
    frame_ready = Signal(QImage)
    tracking_ready = Signal(object)
    fps_ready = Signal(float)
    status_ready = Signal(str)

    def __init__(self, index: int = 0, width: int = 1280, height: int = 720, fps: int = 60, tracker: HandTracker | None = None) -> None:
        super().__init__()
        self.index = index
        self.width = width
        self.height = height
        self.target_fps = fps
        self.tracker = tracker or HandTracker()
        self._running = False
        self._active_index: int | None = None
        self.current_fps = 0.0

    @staticmethod
    def probe_cameras(max_index: int = 6) -> list[int]:  # pragma: no cover - hardware dependent
        """Return available webcam indices for the settings screen."""
        found: list[int] = []
        for idx in range(max_index + 1):
            cap = cv2.VideoCapture(idx)
            ok = cap.isOpened()
            if ok:
                grabbed, _ = cap.read()
                if grabbed:
                    found.append(idx)
            cap.release()
        return found

    def _open_camera(self) -> cv2.VideoCapture | None:  # pragma: no cover - hardware dependent
        candidates = [self.index] + [i for i in range(6) if i != self.index]
        for idx in candidates:
            cap = cv2.VideoCapture(idx)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if cap.isOpened():
                self._active_index = idx
                self.status_ready.emit(f"Webcam online: camera {idx} at {self.width}x{self.height}@{self.target_fps}")
                return cap
            cap.release()
        self.status_ready.emit("No webcam opened. Check OS camera permission or choose another camera index.")
        return None

    def run(self) -> None:  # pragma: no cover - needs camera
        self._running = True
        cap = self._open_camera()
        last = time.perf_counter()
        frames = 0
        failures = 0
        while self._running:
            if cap is None:
                time.sleep(0.75)
                cap = self._open_camera()
                continue

            ok, frame = cap.read()
            if not ok:
                failures += 1
                if failures > 12:
                    self.status_ready.emit("Webcam stream interrupted; automatically reconnecting…")
                    cap.release()
                    cap = None
                    failures = 0
                time.sleep(0.08)
                continue
            failures = 0
            frame = cv2.flip(frame, 1)
            tracking: HandTrackingResult = self.tracker.process(frame)
            self.tracking_ready.emit(tracking)
            self._draw_overlay(frame, tracking)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
            self.frame_ready.emit(image)
            frames += 1
            now = time.perf_counter()
            if now - last >= 1.0:
                self.current_fps = frames / (now - last)
                self.fps_ready.emit(self.current_fps)
                frames = 0
                last = now
            sleep_time = max(0.0, (1 / max(self.target_fps, 1)) - (time.perf_counter() - now))
            if sleep_time:
                time.sleep(sleep_time)
        if cap is not None:
            cap.release()
        self.tracker.close()

    def _draw_overlay(self, frame, tracking: HandTrackingResult) -> None:  # pragma: no cover - visual only
        # Landmark bones for the hand skeleton.
        if tracking.landmarks:
            bones = [
                (0, 1),
                (1, 2),
                (2, 3),
                (3, 4),
                (0, 5),
                (5, 6),
                (6, 7),
                (7, 8),
                (0, 9),
                (9, 10),
                (10, 11),
                (11, 12),
                (0, 13),
                (13, 14),
                (14, 15),
                (15, 16),
                (0, 17),
                (17, 18),
                (18, 19),
                (19, 20),
                (5, 9),
                (9, 13),
                (13, 17),
            ]
            for a, b in bones:
                pa = tuple(map(int, tracking.landmarks[a]))
                pb = tuple(map(int, tracking.landmarks[b]))
                cv2.line(frame, pa, pb, (80, 220, 255), 2, cv2.LINE_AA)
            for p in tracking.landmarks:
                cv2.circle(frame, tuple(map(int, p)), 3, (245, 215, 100), -1, cv2.LINE_AA)

        if tracking.wand and tracking.wand.detected and tracking.wand.tip and tracking.wand.base:
            cv2.line(frame, tuple(map(int, tracking.wand.base)), tuple(map(int, tracking.wand.tip)), (255, 80, 230), 3, cv2.LINE_AA)
            cv2.circle(frame, tuple(map(int, tracking.wand.tip)), 8, (255, 255, 255), -1, cv2.LINE_AA)

        if tracking.tip:
            x, y = map(int, tracking.tip)
            cv2.circle(frame, (x, y), 12, (255, 240, 120), 2, cv2.LINE_AA)
            cv2.circle(frame, (x, y), 4, (255, 255, 255), -1, cv2.LINE_AA)
        
        # Upper info label
        label = f"Tip: {tracking.source}  confidence {tracking.confidence:.0%}  velocity {tracking.velocity:.0f}px/s"
        cv2.putText(frame, label, (18, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (10, 10, 10), 4, cv2.LINE_AA)
        cv2.putText(frame, label, (18, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (130, 235, 255), 2, cv2.LINE_AA)

        # Detailed Debug Overlay checklist requirements:
        # - Current fingertip coordinates
        # - Wand sensor coordinates
        # - Tracking confidence
        # - FPS
        # - Detection status
        debug_lines = []
        status_str = "Detected" if tracking.detected else "No Hand/Wand"
        debug_lines.append(f"Detection status: {status_str}")
        debug_lines.append(f"FPS: {self.current_fps:.1f}")
        debug_lines.append(f"Tracking confidence: {tracking.confidence:.0%}")
        
        if tracking.landmarks and len(tracking.landmarks) > 8:
            fx, fy = tracking.landmarks[8]
            debug_lines.append(f"Fingertip (lm8) coords: {fx:.1f}, {fy:.1f}")
        else:
            debug_lines.append("Fingertip (lm8) coords: N/A")
            
        if tracking.tip:
            tx, ty = tracking.tip
            debug_lines.append(f"Wand sensor coords: {tx:.1f}, {ty:.1f}")
        else:
            debug_lines.append("Wand sensor coords: N/A")
            
        y_pos = 70
        for line in debug_lines:
            cv2.putText(frame, line, (18, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (10, 10, 10), 3, cv2.LINE_AA)
            cv2.putText(frame, line, (18, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 255, 150), 1, cv2.LINE_AA)
            y_pos += 24

    def stop(self) -> None:
        self._running = False
        self.wait(1800)
