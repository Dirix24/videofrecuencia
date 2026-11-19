"""Desinstalador local de VideoFrecuencia para Linux, macOS y Windows.

Uso: python uninstall.py (desde la carpeta del proyecto).
Elimina únicamente la carpeta de esta copia, previa confirmación explícita.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


def project_directory(script_file: str | Path) -> Path:
    root = Path(script_file).resolve().parent
    if not (root / "app.py").is_file() or not (root / "videofrecuencia" / "analysis.py").is_file():
        raise ValueError("No se reconoce una instalación de VideoFrecuencia.")
    if root == Path.home().resolve() or root == Path(root.anchor):
        raise ValueError("Ruta insegura: no se puede borrar la carpeta personal ni la raíz.")
    return root


def uninstall(root: Path, *, platform: str | None = None) -> None:
    """Borra la copia local; Windows espera a que termine el intérprete."""
    platform = platform or sys.platform
    os.chdir(Path.home())
    if platform == "win32":
        # El ejecutable de .venv puede estar bloqueado hasta que Python termine.
        # cmd.exe no depende del intérprete que se está desinstalando.
        command = 'ping 127.0.0.1 -n 4 >NUL & rmdir /s /q "{}"'.format(str(root).replace('"', ''))
        subprocess.Popen(
            ["cmd.exe", "/d", "/c", command],
            cwd=str(Path.home()),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            close_fds=True,
        )
        print("Eliminación programada. Termina al cerrar este proceso.")
    else:
        shutil.rmtree(root)
        print("VideoFrecuencia eliminado de este ordenador.")


def main() -> int:
    try:
        root = project_directory(__file__)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Se eliminará permanentemente: {root}")
    print("Incluye .venv, código, CSV y cualquier archivo guardado DENTRO de esa carpeta.")
    print("No elimina archivos fuera de ella, Python del sistema ni el repositorio de GitHub.")
    try:
        answer = input("Escribe DESINSTALAR para confirmar: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelado.")
        return 1
    if answer != "DESINSTALAR":
        print("Cancelado: no se ha borrado nada.")
        return 1
    try:
        uninstall(root)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"No se pudo completar la desinstalación: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
