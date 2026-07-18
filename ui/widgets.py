"""Reusable UI widgets."""

from __future__ import annotations
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class GlassPanel(QFrame):
    def __init__(self, title: str | None = None) -> None:
        super().__init__()
        self.setObjectName("GlassPanel")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("Metric")
            self.layout.addWidget(label)
