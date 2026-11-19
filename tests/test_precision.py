"""Estimación de frecuencia con bins intermedios y FPS inestables."""
import numpy as np

from videofrecuencia.analysis import FrequencyAnalyzer


def test_refined_peak_for_non_integer_fft_bin():
    analyzer = FrequencyAnalyzer(window_seconds=6)
    frequency = 3.37
    for i in range(180):
        t = i / 30
        analyzer.add_sample(100 + 25 * np.sin(2 * np.pi * frequency * t), t)
    result = analyzer.compute()
    assert result is not None
    assert result.dominant_freq_hz is not None
    assert abs(result.dominant_freq_hz - frequency) < 0.08
    assert result.resolution_hz is not None


def test_unstable_frame_timing_is_not_reported_as_reliable():
    analyzer = FrequencyAnalyzer(window_seconds=6)
    t = 0.0
    for i in range(130):
        t += 0.02 if i % 2 else 0.055
        analyzer.add_sample(100 + 25 * np.sin(2 * np.pi * 3 * t), t)
    result = analyzer.compute()
    assert result is not None
    assert result.sampling_jitter is not None
    assert result.sampling_jitter > 0.25
    assert result.dominant_freq_hz is None
