"""Regression tests for safe sampling limits and configurable ROI."""
import numpy as np

from videofrecuencia.analysis import FrequencyAnalyzer, roi_mean_intensity


def test_does_not_report_peak_near_nyquist():
    analyzer = FrequencyAnalyzer(window_seconds=5)
    fps = 24.0
    for i in range(120):
        t = i / fps
        analyzer.add_sample(100 + 30 * np.sin(2 * np.pi * 10 * t), t)
    result = analyzer.compute()
    assert result is not None
    assert result.nyquist_hz is not None
    assert abs(result.nyquist_hz - 12) < 0.01
    assert result.dominant_freq_hz is None or result.dominant_freq_hz < fps * 0.4


def test_roi_size_changes_measured_area():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    image[40:60, 40:60] = 200
    small = roi_mean_intensity(image, 0.1)
    full = roi_mean_intensity(image, 1.0)
    assert small > full


def test_synthetic_three_hz_still_detected():
    analyzer = FrequencyAnalyzer()
    for i in range(150):
        t = i / 30.0
        analyzer.add_sample(100 + 30 * np.sin(2 * np.pi * 3 * t), t)
    result = analyzer.compute()
    assert result is not None
    assert result.dominant_freq_hz is not None
    assert abs(result.dominant_freq_hz - 3) < 0.3
