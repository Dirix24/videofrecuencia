"""Pruebas de fiabilidad: una frecuencia solo debe aparecer si hay señal."""
import numpy as np

from videofrecuencia.analysis import FrequencyAnalyzer


def _feed(analyzer, values, fps=30.0):
    for i, value in enumerate(values):
        analyzer.add_sample(float(value), i / fps)
    return analyzer.compute()


def test_constant_light_has_no_detected_frequency():
    result = _feed(FrequencyAnalyzer(), np.full(120, 120.0))
    assert result is not None
    assert result.dominant_freq_hz is None
    assert result.bpm is None


def test_small_camera_noise_is_not_reported_as_a_signal():
    rng = np.random.default_rng(42)
    result = _feed(FrequencyAnalyzer(), 120 + rng.normal(0, 0.05, 150))
    assert result is not None
    assert result.dominant_freq_hz is None


def test_clear_periodic_signal_is_detected():
    t = np.arange(150) / 30.0
    result = _feed(FrequencyAnalyzer(), 120 + 20 * np.sin(2 * np.pi * 3 * t))
    assert result is not None
    assert result.dominant_freq_hz is not None
    assert abs(result.dominant_freq_hz - 3.0) < 0.3
    assert result.peak_snr is not None and result.peak_snr >= 5.0
    assert abs(result.nyquist_hz - 15.0) < 0.01


def test_short_signal_is_not_presented_as_reliable():
    t = np.arange(30) / 30.0
    result = _feed(FrequencyAnalyzer(), 100 + 25 * np.sin(2 * np.pi * 3 * t))
    assert result is not None
    assert result.dominant_freq_hz is None
