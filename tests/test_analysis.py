import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from videofrecuencia.analysis import FrequencyAnalyzer, roi_mean_intensity


def test_detects_known_frequency():
    """Alimenta el analizador con una senoidal de 3 Hz muestreada a 30 fps
    y comprueba que detecta el pico cerca de esa frecuencia."""
    analyzer = FrequencyAnalyzer(window_seconds=4.0, max_samples=256)
    fps = 30.0
    freq = 3.0
    n = int(fps * 4.0)
    for i in range(n):
        t = i / fps
        value = 50.0 + 20.0 * np.sin(2 * np.pi * freq * t)
        analyzer.add_sample(value, t)

    result = analyzer.compute()
    assert result is not None
    assert result.dominant_freq_hz is not None
    assert abs(result.dominant_freq_hz - freq) < 0.3


def test_not_enough_samples_returns_none():
    analyzer = FrequencyAnalyzer()
    for i in range(5):
        analyzer.add_sample(1.0, float(i))
    assert analyzer.compute() is None


def test_roi_mean_intensity_shape():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[:, :] = (10, 20, 30)
    value = roi_mean_intensity(frame, roi_fraction=0.5)
    assert value > 0


def test_window_purges_old_samples():
    analyzer = FrequencyAnalyzer(window_seconds=1.0, max_samples=1000)
    for i in range(200):
        analyzer.add_sample(float(i), i * 0.01)  # 2 segundos de datos a 100 Hz
    # Solo debería quedar ~1 segundo de muestras.
    assert analyzer.sample_count <= 101
