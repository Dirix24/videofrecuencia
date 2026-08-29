"""
Generador de una señal de vídeo sintética con parpadeo a una frecuencia
conocida, para poder probar y calibrar el analizador sin necesitar una
fuente de flicker real.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np


@dataclass
class SyntheticSignalGenerator:
    freq_hz: float = 3.0
    width: int = 480
    height: int = 360
    base_color: tuple[int, int, int] = (40, 40, 40)
    amplitude: float = 100.0
    start_time: float = 0.0

    def __post_init__(self) -> None:
        self.start_time = time.monotonic()

    def frame(self) -> np.ndarray:
        t = time.monotonic() - self.start_time
        intensity = self.amplitude * (0.5 + 0.5 * np.sin(2 * np.pi * self.freq_hz * t))
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        b, g, r = self.base_color
        img[:, :, 0] = np.clip(b + intensity, 0, 255)
        img[:, :, 1] = np.clip(g + intensity, 0, 255)
        img[:, :, 2] = np.clip(r + intensity, 0, 255)
        return img
