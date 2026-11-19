"""Regression tests for input validation and camera lifecycle."""
import numpy as np
import pytest

from videofrecuencia.analysis import FrequencyAnalyzer, roi_mean_intensity
from videofrecuencia.capture import VideoCaptureThread


def test_rejects_invalid_samples_and_out_of_order_timestamps():
    analyzer = FrequencyAnalyzer()
    analyzer.add_sample(1.0, 1.0)
    for value, timestamp in [(float("nan"), 2.0), (1.0, float("inf")), (2.0, 1.0)]:
        with pytest.raises(ValueError):
            analyzer.add_sample(value, timestamp)
    assert analyzer.sample_count == 1


@pytest.mark.parametrize("fraction", [0, -0.1, 1.1])
def test_invalid_roi_fraction(fraction):
    with pytest.raises(ValueError):
        roi_mean_intensity(np.zeros((10, 10, 3), dtype=np.uint8), fraction)


def test_tiny_roi_is_not_empty():
    frame = np.full((2, 2, 3), 100, dtype=np.uint8)
    assert roi_mean_intensity(frame, 0.1) == pytest.approx(100)


def test_invalid_frame_shape():
    with pytest.raises(ValueError):
        roi_mean_intensity(np.zeros((5, 5), dtype=np.uint8))


def test_capture_handles_camera_failure(monkeypatch):
    class FakeCapture:
        def __init__(self, source):
            pass
        def isOpened(self):
            return False
        def release(self):
            pass

    monkeypatch.setattr("videofrecuencia.capture.cv2.VideoCapture", FakeCapture)
    capture = VideoCaptureThread()
    assert capture.start() is False
    assert capture.is_running is False
    assert capture._cap is None


def test_capture_handles_disconnection(monkeypatch):
    class FakeCapture:
        def __init__(self, source):
            self.released = False
        def isOpened(self):
            return True
        def read(self):
            return False, None
        def release(self):
            self.released = True

    monkeypatch.setattr("videofrecuencia.capture.cv2.VideoCapture", FakeCapture)
    capture = VideoCaptureThread()
    assert capture.start() is True
    capture._thread.join(timeout=2)
    assert capture.is_running is False
    assert capture.last_error == "Se perdió la señal de la cámara."
    capture.stop()
    assert capture._cap is None
