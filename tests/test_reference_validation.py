"""Pruebas de precisión y clasificación con señales de referencia conocidas."""
import numpy as np
import pytest

from videofrecuencia.analysis import FrequencyAnalyzer


@pytest.mark.parametrize("frequency", [1.0, 2.5, 3.3, 5.0])
def test_reference_signal_frequency_and_confidence(frequency):
    analyzer = FrequencyAnalyzer(window_seconds=6)
    fps = 30
    for i in range(180):
        t = i / fps
        analyzer.add_sample(120 + 20 * np.sin(2 * np.pi * frequency * t), t)
    result = analyzer.compute()
    assert result is not None
    assert result.dominant_freq_hz is not None
    assert abs(result.dominant_freq_hz - frequency) < 0.12
    assert result.confidence in ("estable", "orientativa")


def test_no_frequency_means_insufficient_confidence():
    analyzer = FrequencyAnalyzer()
    for i in range(180):
        analyzer.add_sample(100, i / 30)
    result = analyzer.compute()
    assert result is not None
    assert result.dominant_freq_hz is None
    assert result.confidence == "insuficiente"
