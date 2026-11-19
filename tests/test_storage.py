"""Pruebas de guardado CSV en Linux, Windows y macOS (sin interfaz gráfica)."""
import csv

import pytest

from videofrecuencia.storage import HEADER, append_measurements, export_measurements, initialize_measurements


def test_autosave_creates_header_and_appends_without_overwriting(tmp_path):
    path = tmp_path / "mediciones.csv"
    assert append_measurements(path, [(1.0, 3.0)]) == 1
    assert append_measurements(path, [(2.0, 3.1)]) == 1
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert rows == [list(HEADER), ["1.0", "3.0"], ["2.0", "3.1"]]


def test_autosave_empty_batch_does_not_create_file(tmp_path):
    path = tmp_path / "empty.csv"
    assert append_measurements(path, []) == 0
    assert not path.exists()


def test_autosave_refuses_unrelated_file(tmp_path):
    path = tmp_path / "existing.csv"
    path.write_text("other,header\nold,data\n", encoding="utf-8")
    with pytest.raises(ValueError):
        append_measurements(path, [(1.0, 2.0)])
    assert path.read_text(encoding="utf-8") == "other,header\nold,data\n"


def test_manual_export_writes_chosen_filename(tmp_path):
    path = tmp_path / "mi archivo.csv"
    export_measurements(path, [(5.0, 2.5)])
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert rows == [list(HEADER), ["5.0", "2.5"]]


def test_autosave_accepts_utf8_bom_header(tmp_path):
    path = tmp_path / "mediciones.csv"
    path.write_text("\ufefft_segundos,frecuencia_dominante_hz\n", encoding="utf-8")
    append_measurements(path, [(1.0, 4.0)])
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[-1] == ["1.0", "4.0"]


def test_selected_autosave_file_is_created_before_first_measurement(tmp_path):
    path = tmp_path / "carpeta con espacios" / "mis datos.csv"
    path.parent.mkdir()
    initialize_measurements(path)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ",".join(HEADER) + "\n"


def test_missing_frequency_is_saved_as_blank_not_fake_zero(tmp_path):
    path = tmp_path / "mediciones.csv"
    append_measurements(path, [(1.0, None), (2.0, 3.0)])
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[1] == ["1.0", ""]
    assert rows[2] == ["2.0", "3.0"]
