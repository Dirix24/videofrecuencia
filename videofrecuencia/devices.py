"""Descubrimiento de cámaras accesibles con OpenCV.

Se comprueba una imagen real, no solo que el dispositivo se abra.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2


def camera_candidates(max_devices: int = 6) -> list[int]:
    """Índices probables; en Linux evita escanear nodos inexistentes."""
    if sys.platform.startswith("linux"):
        devices = sorted(Path("/dev").glob("video[0-9]*"))
        indices = sorted({int(p.name[5:]) for p in devices if p.name[5:].isdigit()})
        return indices[:max_devices] if indices else list(range(min(max_devices, 3)))
    return list(range(max_devices))


def discover_cameras(max_devices: int = 6) -> list[tuple[int, str]]:
    """Devuelve cámaras que entregan frames. Ejecutar fuera del hilo Tk."""
    found = []
    for index in camera_candidates(max_devices):
        cap = None
        try:
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                continue
            ok, frame = cap.read()
            if not ok or frame is None or frame.size == 0:
                continue
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            details = f" ({width}×{height})" if width and height else ""
            found.append((index, f"Cámara {index}{details}"))
        except (OSError, cv2.error):
            continue
        finally:
            if cap is not None:
                cap.release()
    return found
