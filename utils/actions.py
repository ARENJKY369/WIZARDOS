"""Harmless desktop actions. All actions avoid elevation and destructive commands."""
from __future__ import annotations
import os
import platform
import subprocess
import webbrowser
from pathlib import Path
from typing import Callable


class DesktopActionRunner:
    def __init__(self, toggle_dark_mode: Callable[[], None] | None = None) -> None:
        self.toggle_dark_mode = toggle_dark_mode

    def run(self, action: str) -> str:
        if not action or action == "none":
            return "No desktop action configured."
        method = getattr(self, f"_action_{action}", None)
        if method is None:
            return f"Unknown action: {action}"
        try:
            method()
            return f"Action completed: {action}"
        except Exception as exc:  # pragma: no cover - platform dependent
            return f"Action failed: {exc}"

    def _action_launch_calculator(self) -> None:
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["calc.exe"])
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", "Calculator"])
        else:
            for cmd in (["gnome-calculator"], ["kcalc"], ["xcalc"]):
                try:
                    subprocess.Popen(cmd)
                    return
                except FileNotFoundError:
                    continue
            raise RuntimeError("No calculator executable found")

    def _action_open_browser(self) -> None:
        webbrowser.open("https://www.python.org")

    def _action_open_notepad(self) -> None:
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["notepad.exe"])
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", "TextEdit"])
        else:
            subprocess.Popen(["xdg-open", str(Path.home())])

    def _action_take_screenshot(self) -> None:
        # Implemented in UI by Qt shortcut in future; here we open Pictures safely as placeholder.
        path = Path.home() / "Pictures"
        if path.exists():
            self._open_path(path)

    def _action_open_home_folder(self) -> None:
        self._open_path(Path.home())

    def _action_toggle_app_dark_mode(self) -> None:
        if self.toggle_dark_mode:
            self.toggle_dark_mode()

    def _open_path(self, path: Path) -> None:
        system = platform.system()
        if system == "Windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
