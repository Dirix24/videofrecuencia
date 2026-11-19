"""Persistencia CSV portable para sesiones de medición.

Solo se escribe en rutas elegidas explícitamente por la persona usuaria.
"""
from __future__ import annotations

import csv
from pathlib import Path

HEADER = ("t_segundos", "frecuencia_dominante_hz")


def initialize_measurements(path: str | Path) -> Path:
    """Crea inmediatamente el CSV elegido o valida su cabecera.

    No modifica archivos ajenos al formato de mediciones.
    """
    target = Path(path).expanduser()
    if target.exists() and target.stat().st_size:
        with target.open("r", newline="", encoding="utf-8-sig") as handle:
            if tuple(next(csv.reader(handle), ())) != HEADER:
                raise ValueError("El archivo existente no tiene la cabecera CSV esperada.")
    else:
        with target.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(HEADER)
    return target


def append_measurements(path: str | Path, rows: list[tuple[float, float]]) -> int:
    """Añade medidas a un CSV; no destruye datos existentes.

    Comprueba la cabecera de los CSV existentes antes de escribir.
    Devuelve cuántas filas se han escrito.
    """
    if not rows:
        return 0
    target = initialize_measurements(path)
    with target.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)
        handle.flush()
    return len(rows)


def export_measurements(path: str | Path, rows: list[tuple[float, float]]) -> None:
    """Exporta una sesión completa a la ruta seleccionada."""
    with Path(path).expanduser().open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)
