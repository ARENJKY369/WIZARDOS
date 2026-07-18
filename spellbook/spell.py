"""Spell domain model."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Spell:
    name: str
    gesture: str
    description: str
    mana_cost: int
    cooldown: float
    particle_effect: str
    audio_effect: str
    desktop_action: str
    difficulty: int
    mastery_level: int
    accuracy: float
    times_cast: int
    favorite: bool
    unlock_level: int
    color: str = "#FFFFFF"

    @classmethod
    def from_dict(cls, data: dict) -> "Spell":
        return cls(**data)

    def to_dict(self) -> dict:
        return self.__dict__.copy()
