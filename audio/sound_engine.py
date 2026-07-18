"""Local spell audio with generated fallback tones.

If assets/sounds/<effect>.wav exists it will be played. Otherwise pygame emits a
short synthesized tone so the app remains self-contained.
"""
from __future__ import annotations
import math
import numpy as np
from pathlib import Path
from utils.paths import ASSETS

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore


class SoundEngine:
    def __init__(self, enabled: bool = True, master_volume: float = 0.75) -> None:
        self.enabled = enabled and pygame is not None
        self.master_volume = master_volume
        self.cache: dict[str, object] = {}
        if self.enabled:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                pygame.mixer.set_num_channels(24)
            except Exception:
                self.enabled = False

    def play(self, effect: str) -> None:
        if not self.enabled:
            return
        sound = self.cache.get(effect)
        if sound is None:
            sound = self._load_or_generate(effect)
            self.cache[effect] = sound
        sound.set_volume(self.master_volume)  # type: ignore[attr-defined]
        sound.play()  # type: ignore[attr-defined]

    def _load_or_generate(self, effect: str):
        path = ASSETS / "sounds" / f"{effect}.wav"
        if path.exists():
            return pygame.mixer.Sound(str(path))
        freq = 220 + (sum(ord(c) for c in effect) % 620)
        duration = 0.32
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        envelope = np.exp(-5 * t)
        wave = (np.sin(2 * math.pi * freq * t) + 0.4 * np.sin(2 * math.pi * freq * 1.5 * t)) * envelope
        stereo = np.column_stack([wave, wave])
        audio = np.int16(stereo * 32767 * 0.35)
        return pygame.sndarray.make_sound(audio)

    def shutdown(self) -> None:
        if self.enabled:
            pygame.mixer.quit()
