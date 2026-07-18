"""Centralised filesystem paths for WizardOS."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
CONFIG = ROOT / "config"
SPELLBOOK = ROOT / "spellbook"
MODELS = ROOT / "models"
LOGS = ROOT / "logs"
USER_DATA = ROOT / "user_data"
USER_DATA.mkdir(exist_ok=True)
