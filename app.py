"""WizardOS application entrypoint."""

from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QTimer
from config.settings import SettingsManager
from ui.main_window import MainWindow
from utils.logging import setup_logging
from utils.paths import ASSETS


def main() -> int:
    settings = SettingsManager()
    setup_logging(settings.get("debug", False)).info("Starting WizardOS")
    app = QApplication(sys.argv)
    app.setApplicationName("WizardOS")
    app.setOrganizationName("Arena Wizardry Lab")
    logo_path = ASSETS / "logo.svg"
    app.setWindowIcon(QIcon(str(logo_path)))
    splash = QSplashScreen(QPixmap(str(logo_path)).scaled(420, 420, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
    splash.showMessage("Loading arcane subsystems…", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
    splash.show()
    window = MainWindow(settings)
    QTimer.singleShot(900, lambda: (window.show(), splash.finish(window)))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
