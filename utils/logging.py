"""Rich logging setup used by every subsystem."""

from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from .paths import LOGS


def setup_logging(debug: bool = False) -> logging.Logger:
    LOGS.mkdir(exist_ok=True)
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )
    file_handler = RotatingFileHandler(LOGS / "wizardos.log", maxBytes=2_000_000, backupCount=3)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    file_handler.setLevel(level)
    root = logging.getLogger()
    root.addHandler(file_handler)
    return logging.getLogger("wizardos")
