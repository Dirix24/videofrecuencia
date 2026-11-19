"""Regresión de selección automática de webcam."""
import pytest

from videofrecuencia.camera_policy import camera_start_policy


@pytest.mark.parametrize(
    "count,expected",
    [(0, "unavailable"), (1, "auto_start"), (2, "choose"), (3, "choose")],
)
def test_camera_count_controls_selection(count, expected):
    assert camera_start_policy(count, capture_active=False, generator_active=False) == expected


def test_existing_capture_is_not_restarted():
    assert camera_start_policy(1, capture_active=True, generator_active=False) == "keep_current"


def test_synthetic_signal_is_not_interrupted():
    assert camera_start_policy(1, capture_active=False, generator_active=True) == "keep_current"
