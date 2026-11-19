"""El desinstalador solo debe aceptar la carpeta del proyecto y pedir confirmación."""
from pathlib import Path

import pytest

from uninstall import project_directory, uninstall


def test_rejects_unrecognized_directory(tmp_path):
    with pytest.raises(ValueError, match="No se reconoce"):
        project_directory(tmp_path / "uninstall.py")


def test_recognizes_project_layout(tmp_path):
    (tmp_path / "videofrecuencia").mkdir()
    (tmp_path / "videofrecuencia" / "analysis.py").write_text("")
    (tmp_path / "app.py").write_text("")
    assert project_directory(tmp_path / "uninstall.py") == tmp_path


def test_uninstall_removes_only_project_directory(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    (project / "app.py").write_text("")
    other = tmp_path / "keep.txt"
    other.write_text("conservar")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr("uninstall.os.chdir", lambda _path: None)
    uninstall(project, platform="linux")
    assert not project.exists()
    assert other.read_text() == "conservar"
