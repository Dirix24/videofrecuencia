"""Regresiones para nodos V4L2 y guardado al cambiar de fuente."""
from pathlib import Path
from unittest.mock import patch

from videofrecuencia.devices import camera_candidates
from videofrecuencia.storage import append_measurements, initialize_measurements


def test_autosave_file_keeps_rows_across_source_switches(tmp_path):
    path = tmp_path / "elegido" / "mediciones.csv"
    path.parent.mkdir()
    initialize_measurements(path)
    append_measurements(path, [(1.0, 3.0)])
    append_measurements(path, [(2.0, None), (3.0, 4.0)])
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4
    assert lines[1] == "1.0,3.0"
    assert lines[2] == "2.0,"
    assert lines[3] == "3.0,4.0"


def test_linux_skips_secondary_metadata_camera_nodes():
    devices = [Path("/dev/video0"), Path("/dev/video1"), Path("/dev/video2")]
    real_exists = Path.exists
    real_read_text = Path.read_text

    def fake_exists(path):
        if str(path).startswith("/sys/class/video4linux/"):
            return True
        return real_exists(path)

    def fake_read_text(path, *args, **kwargs):
        if str(path).startswith("/sys/class/video4linux/"):
            return "1" if path.parent.name == "video1" else "0"
        return real_read_text(path, *args, **kwargs)

    with patch("videofrecuencia.devices.sys.platform", "linux"), \
         patch("videofrecuencia.devices.Path.glob", return_value=devices), \
         patch("videofrecuencia.devices.Path.exists", fake_exists), \
         patch("videofrecuencia.devices.Path.read_text", fake_read_text):
        assert camera_candidates() == [0, 2]
