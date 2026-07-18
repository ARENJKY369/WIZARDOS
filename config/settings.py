"""JSON settings loading/saving with safe defaults."""
from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from utils.paths import CONFIG, USER_DATA


class SettingsManager:
    def __init__(self, path: Path | None = None) -> None:
        self.default_path = CONFIG / "default_settings.json"
        self.user_path = path or USER_DATA / "settings.json"
        self.data = self._load()

    def _load_json(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _load(self) -> dict[str, Any]:
        defaults = self._load_json(self.default_path)
        if self.user_path.exists():
            return self._deep_merge(defaults, self._load_json(self.user_path))
        return defaults

    def save(self) -> None:
        self.user_path.parent.mkdir(exist_ok=True)
        with self.user_path.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict):
                return default
            node = node.get(part, default)
        return node

    def set(self, dotted: str, value: Any) -> None:
        node = self.data
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
        self.save()
