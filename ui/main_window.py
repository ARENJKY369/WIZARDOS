"""Main desktop application window."""
from __future__ import annotations
import time
from collections import deque
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QColor, QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QProgressBar, QTabWidget, QTextEdit, QComboBox, QMessageBox, QSplitter,
    QFormLayout, QSpinBox, QCheckBox
)
from camera.camera_manager import CameraWorker
from config.settings import SettingsManager
from gesture.recognizer import GestureRecognizer
from renderer.opengl_renderer import MagicRenderer
from spellbook.spellbook_manager import SpellbookManager
from audio.sound_engine import SoundEngine
from training.training_manager import TrainingManager
from ui.theme import DARK_QSS
from ui.widgets import GlassPanel
from utils.actions import DesktopActionRunner
from utils.stats import StatsManager
from vision.hand_tracker import HandTracker, HandTrackingResult


class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsManager) -> None:
        super().__init__()
        self.settings = settings
        self.setWindowTitle("WizardOS — AI Spell Recognition System")
        self.resize(1480, 900)
        self.setStyleSheet(DARK_QSS)

        self.recognizer = GestureRecognizer()
        self.training = TrainingManager(self.recognizer)
        self.spellbook = SpellbookManager()
        self.stats = StatsManager()
        self.sound = SoundEngine(settings.get("audio.enabled", True), settings.get("audio.master_volume", 0.75))
        self.actions = DesktopActionRunner(toggle_dark_mode=self.toggle_dark_mode)
        self.stroke: deque[tuple[float, float]] = deque(maxlen=220)
        self.last_tip_time = 0.0
        self.last_recognized_at = 0.0
        self.source_size = (settings.get("camera.width", 1280), settings.get("camera.height", 720))
        self.dark_mode = True

        self._build_ui()
        self._create_shortcuts()
        self._start_camera()

        self.recognition_timer = QTimer(self)
        self.recognition_timer.timeout.connect(self._recognize_live_stroke)
        self.recognition_timer.start(120)

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._dashboard(), "Dashboard")
        tabs.addTab(self._spellbook_tab(), "Spellbook")
        tabs.addTab(self._training_tab(), "Training Room")
        tabs.addTab(self._settings_tab(), "Settings")
        tabs.addTab(self._stats_tab(), "Statistics")
        tabs.addTab(self._credits_tab(), "Credits")
        self.setCentralWidget(tabs)

    def _dashboard(self) -> QWidget:
        root = QWidget()
        layout = QHBoxLayout(root)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        left = GlassPanel("Scrying Camera")
        self.camera_label = QLabel("Camera feed loading…")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setMinimumSize(640, 360)
        self.camera_label.setStyleSheet("border-radius: 18px; background: #02040A; color:#75E7FF;")
        self.renderer = MagicRenderer()
        self.renderer.setMinimumSize(640, 360)
        self.renderer.mouse_stroke_changed.connect(self._recognize_mouse_stroke)
        left.layout.addWidget(self.camera_label, 1)
        left.layout.addWidget(self.renderer, 1)
        splitter.addWidget(left)

        right = GlassPanel("Arcane Telemetry")
        self.title = QLabel("WIZARDOS")
        self.title.setObjectName("Title")
        right.layout.addWidget(self.title)
        self.fps_label = QLabel("FPS: --")
        self.hand_label = QLabel("Detected hand: no")
        self.tip_source_label = QLabel("Tracking source: none")
        self.velocity_label = QLabel("Wand speed: 0 px/s")
        self.camera_status_label = QLabel("Webcam: starting…")
        self.confidence_label = QLabel("Recognition confidence: 0%")
        self.current_spell_label = QLabel("Current spell: none")
        for label in (self.fps_label, self.hand_label, self.tip_source_label, self.velocity_label, self.camera_status_label, self.confidence_label, self.current_spell_label):
            label.setObjectName("Metric")
            right.layout.addWidget(label)
        self.mana = QProgressBar(); self.mana.setRange(0, 100); self.mana.setValue(100); self.mana.setFormat("Mana %p%")
        self.xp = QProgressBar(); self.xp.setRange(0, 100); self.xp.setValue(12); self.xp.setFormat("Experience %p%")
        right.layout.addWidget(self.mana); right.layout.addWidget(self.xp)
        self.history = QListWidget(); self.history.addItem("Spell history will appear here")
        right.layout.addWidget(self.history, 1)
        cast_lumos = QPushButton("Demo Burst: Lumos")
        cast_lumos.clicked.connect(lambda: self._cast_by_gesture("circle", 0.99))
        right.layout.addWidget(cast_lumos)
        splitter.addWidget(right)
        splitter.setSizes([980, 420])
        return root

    def _spellbook_tab(self) -> QWidget:
        root = QWidget(); layout = QHBoxLayout(root)
        self.spell_list = QListWidget()
        details = QTextEdit(); details.setReadOnly(True)
        def update_details() -> None:
            idx = self.spell_list.currentRow()
            if idx < 0: return
            s = self.spellbook.spells[idx]
            details.setHtml(f"<h1 style='color:{s.color}'>{s.name}</h1><p><b>Gesture:</b> {s.gesture}</p><p>{s.description}</p><p>Mana {s.mana_cost} · Cooldown {s.cooldown}s · Difficulty {s.difficulty}/5</p><p>Mastery {s.mastery_level}% · Accuracy {s.accuracy:.0%} · Casts {s.times_cast}</p><p>Action: {s.desktop_action}</p>")
        for spell in self.spellbook.spells:
            self.spell_list.addItem(f"★ {spell.name}" if spell.favorite else spell.name)
        self.spell_list.currentRowChanged.connect(update_details)
        self.spell_list.setCurrentRow(0)
        layout.addWidget(self.spell_list, 1); layout.addWidget(details, 2)
        return root

    def _training_tab(self) -> QWidget:
        root = QWidget(); layout = QVBoxLayout(root)
        layout.addWidget(QLabel("Select a spell, then draw in the renderer with the mouse or cast via webcam. Training compares trajectory accuracy, speed, and smoothness."))
        self.training_combo = QComboBox()
        for spell in self.spellbook.spells:
            self.training_combo.addItem(f"{spell.name} ({spell.gesture})", spell.gesture)
        self.training_result = QTextEdit(); self.training_result.setReadOnly(True)
        layout.addWidget(self.training_combo); layout.addWidget(self.training_result, 1)
        return root

    def _settings_tab(self) -> QWidget:
        root = QWidget(); layout = QVBoxLayout(root)
        layout.addWidget(QLabel("Advanced webcam controls. WizardOS now prefers the real webcam, auto-reconnects, and can track either a wand-like prop or your index finger."))
        form = QFormLayout()
        self.camera_index_spin = QSpinBox(); self.camera_index_spin.setRange(0, 10); self.camera_index_spin.setValue(self.settings.get("camera.index", 0))
        self.camera_width_spin = QSpinBox(); self.camera_width_spin.setRange(320, 3840); self.camera_width_spin.setSingleStep(160); self.camera_width_spin.setValue(self.settings.get("camera.width", 1280))
        self.camera_height_spin = QSpinBox(); self.camera_height_spin.setRange(240, 2160); self.camera_height_spin.setSingleStep(120); self.camera_height_spin.setValue(self.settings.get("camera.height", 720))
        self.camera_fps_spin = QSpinBox(); self.camera_fps_spin.setRange(15, 240); self.camera_fps_spin.setValue(self.settings.get("camera.fps", 60))
        self.prefer_wand_check = QCheckBox("Prefer wand/pen/stylus tip when visible"); self.prefer_wand_check.setChecked(self.settings.get("vision.prefer_wand", True))
        form.addRow("Camera index", self.camera_index_spin)
        form.addRow("Width", self.camera_width_spin)
        form.addRow("Height", self.camera_height_spin)
        form.addRow("Target FPS", self.camera_fps_spin)
        form.addRow("Wand mode", self.prefer_wand_check)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        scan = QPushButton("Scan Webcams")
        scan.clicked.connect(self._scan_cameras)
        apply_restart = QPushButton("Apply & Restart Webcam")
        apply_restart.clicked.connect(self._apply_camera_settings)
        save = QPushButton("Save Current Settings")
        save.clicked.connect(self.settings.save)
        buttons.addWidget(scan); buttons.addWidget(apply_restart); buttons.addWidget(save)
        layout.addLayout(buttons)
        self.camera_scan_result = QLabel("Tip: choose camera 0 for most laptop webcams.")
        self.camera_scan_result.setObjectName("Metric")
        layout.addWidget(self.camera_scan_result)
        layout.addStretch(1)
        return root

    def _stats_tab(self) -> QWidget:
        root = QWidget(); layout = QVBoxLayout(root)
        self.stats_text = QTextEdit(); self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)
        self._refresh_stats()
        return root

    def _credits_tab(self) -> QWidget:
        root = QWidget(); layout = QVBoxLayout(root)
        layout.addWidget(QLabel("WizardOS is a local-only educational computer vision fantasy demo. No cloud services are used. Dangerous spells are visual/training only."))
        layout.addWidget(QLabel("Built with Python, PySide6, OpenCV, MediaPipe, NumPy, pygame, and procedural OpenGL-widget effects."))
        layout.addStretch(1)
        return root

    def _create_shortcuts(self) -> None:
        fullscreen = QAction("Toggle Fullscreen", self)
        fullscreen.setShortcut(QKeySequence("F11"))
        fullscreen.triggered.connect(lambda: self.showNormal() if self.isFullScreen() else self.showFullScreen())
        self.addAction(fullscreen)
        quit_action = QAction("Quit", self); quit_action.setShortcut(QKeySequence("Ctrl+Q")); quit_action.triggered.connect(self.close); self.addAction(quit_action)

    def _start_camera(self) -> None:
        if hasattr(self, "camera") and self.camera.isRunning():
            self.camera.stop()
        tracker = HandTracker(
            self.settings.get("vision.min_detection_confidence", 0.55),
            self.settings.get("vision.min_tracking_confidence", 0.5),
            self.settings.get("vision.smoothing", 0.68),
            self.settings.get("vision.prefer_wand", True),
        )
        self.camera = CameraWorker(self.settings.get("camera.index", 0), self.settings.get("camera.width", 1280), self.settings.get("camera.height", 720), self.settings.get("camera.fps", 60), tracker)
        self.camera.frame_ready.connect(self._on_frame)
        self.camera.tracking_ready.connect(self._on_tracking)
        self.camera.fps_ready.connect(lambda fps: self.fps_label.setText(f"FPS: {fps:.1f}"))
        self.camera.status_ready.connect(self._on_camera_status)
        self.camera.start()

    def _on_camera_status(self, msg: str) -> None:
        if hasattr(self, "camera_status_label"):
            self.camera_status_label.setText(f"Webcam: {msg}")
        if hasattr(self, "history"):
            self.history.addItem(msg)

    def _scan_cameras(self) -> None:
        found = CameraWorker.probe_cameras(8)
        text = "Available webcams: " + (", ".join(map(str, found)) if found else "none detected by OpenCV")
        if hasattr(self, "camera_scan_result"):
            self.camera_scan_result.setText(text)
        self.history.addItem(text)

    def _apply_camera_settings(self) -> None:
        self.settings.set("camera.index", self.camera_index_spin.value())
        self.settings.set("camera.width", self.camera_width_spin.value())
        self.settings.set("camera.height", self.camera_height_spin.value())
        self.settings.set("camera.fps", self.camera_fps_spin.value())
        self.settings.set("vision.prefer_wand", self.prefer_wand_check.isChecked())
        self.source_size = (self.camera_width_spin.value(), self.camera_height_spin.value())
        self._start_camera()
        self.history.addItem("Webcam settings applied and camera restarted")

    def _on_frame(self, image: QImage) -> None:
        self.source_size = (image.width(), image.height())
        pix = QPixmap.fromImage(image).scaled(self.camera_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.camera_label.setPixmap(pix)

    def _on_tracking(self, result: HandTrackingResult) -> None:
        self.hand_label.setText(f"Detected hand/wand: {'yes' if result.detected else 'no'}")
        self.tip_source_label.setText(f"Tracking source: {result.source} ({result.confidence:.0%})")
        self.velocity_label.setText(f"Wand speed: {result.velocity:.0f} px/s")
        now = time.monotonic()
        if result.tip:
            self.last_tip_time = now
            # Ignore tiny hover jitter; record only deliberate movement or a new stroke.
            if result.velocity > 35 or len(self.stroke) < 4:
                self.stroke.append(result.tip)
            self.renderer.update_tip(result.tip, self.source_size)
        elif now - self.last_tip_time > self.settings.get("recognition.stroke_timeout_ms", 850) / 1000:
            self.stroke.clear()

    def _recognize_live_stroke(self) -> None:
        if len(self.stroke) < self.settings.get("recognition.min_points", 18):
            return
        if time.monotonic() - self.last_recognized_at < 1.0:
            return
        result = self.recognizer.recognize(list(self.stroke))
        self.confidence_label.setText(f"Recognition confidence: {result.confidence:.0%} ({result.gesture})")
        if result.confidence >= self.settings.get("recognition.confidence_threshold", 0.70):
            self._cast_by_gesture(result.gesture, result.confidence)
            self.stroke.clear()
            self.last_recognized_at = time.monotonic()

    def _recognize_mouse_stroke(self, stroke: list[tuple[float, float]]) -> None:
        if len(stroke) < 12:
            return
        result = self.recognizer.recognize(stroke)
        self.confidence_label.setText(f"Recognition confidence: {result.confidence:.0%} ({result.gesture})")
        if result.confidence >= 0.62:
            self._cast_by_gesture(result.gesture, result.confidence)
            expected = self.training_combo.currentData() if hasattr(self, "training_combo") else result.gesture
            score = self.training.score(stroke, expected, 1.5)
            self.training_result.setText(f"Accuracy: {score.accuracy:.0%}\nSpeed: {score.speed:.0%}\nSmoothness: {score.smoothness:.0%}\nConfidence: {score.confidence:.0%}\nSuggestion: {score.suggestion}")

    def _cast_by_gesture(self, gesture: str, confidence: float) -> None:
        spell = self.spellbook.by_gesture(gesture)
        if not spell:
            return
        can_cast, remaining = self.spellbook.can_cast(spell)
        if not can_cast:
            self.current_spell_label.setText(f"{spell.name} cooling down ({remaining:.1f}s)")
            return
        self.current_spell_label.setText(f"Current spell: {spell.name}")
        self.renderer.cast_effect(spell.particle_effect, spell.color, f"{spell.name} · {confidence:.0%}")
        self.sound.play(spell.audio_effect)
        action_message = self.actions.run(spell.desktop_action)
        self.spellbook.record_cast(spell, confidence)
        unlocked = self.stats.record_cast(spell.name, confidence)
        self.history.insertItem(0, f"{spell.name} ({gesture}) {confidence:.0%} — {action_message}")
        for ach in unlocked:
            self.history.insertItem(0, f"Achievement unlocked: {ach}")
        self._refresh_stats()
        self.mana.setValue(max(0, self.mana.value() - spell.mana_cost))

    def _refresh_stats(self) -> None:
        if not hasattr(self, "stats_text"):
            return
        s = self.stats.stats
        self.stats_text.setText(
            f"Daily casts: {s.daily_casts}\nWeekly casts: {s.weekly_casts}\nTotal casts: {s.total_casts}\nAverage accuracy: {s.average_accuracy:.0%}\nFavorite spell: {s.favorite_spell}\nLongest combo: {s.longest_combo}\nPractice time: {s.total_practice_time_seconds}s\nHighest streak: {s.highest_streak}\nAchievements: {', '.join(s.achievements) or 'None'}"
        )

    def toggle_dark_mode(self) -> None:
        self.dark_mode = not self.dark_mode
        self.setStyleSheet(DARK_QSS if self.dark_mode else "QWidget { background:#F5F0E6; color:#15213A; } QPushButton { padding:10px; }")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if hasattr(self, "camera"):
            self.camera.stop()
        self.sound.shutdown()
        super().closeEvent(event)
