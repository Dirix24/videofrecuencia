"""Pruebas del descubrimiento de cámaras sin hardware real."""
from unittest.mock import MagicMock, patch

import numpy as np

from videofrecuencia.devices import discover_cameras


def test_only_cameras_with_readable_frames_are_listed():
    def fake_camera(index):
        cap = MagicMock()
        cap.isOpened.return_value = index != 2
        cap.read.return_value = (index == 0, np.zeros((12, 16, 3), dtype=np.uint8) if index == 0 else None)
        cap.get.side_effect = lambda key: 16 if key == 3 else 12
        return cap

    with patch("videofrecuencia.devices.camera_candidates", return_value=[0, 2]), \
         patch("videofrecuencia.devices.cv2.VideoCapture", side_effect=fake_camera):
        found = discover_cameras()
    assert len(found) == 1
    assert found[0][0] == 0
    assert "Cámara 0" in found[0][1]


def test_camera_handles_are_released_even_when_read_fails():
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.read.side_effect = OSError("dispositivo ocupado")
    with patch("videofrecuencia.devices.camera_candidates", return_value=[1]), \
         patch("videofrecuencia.devices.cv2.VideoCapture", return_value=cap):
        assert discover_cameras() == []
    cap.release.assert_called_once()
