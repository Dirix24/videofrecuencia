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
        indices = []
        for device in devices:
            if not device.name[5:].isdigit():
                continue
            # V4L2 puede exponer nodos secundarios de metadatos (index > 0).
            sysfs_index = Path("/sys/class/video4linux") / device.name / "index"
            try:
                if sysfs_index.exists() and int(sysfs_index.read_text().strip()) != 0:
                    continue
            except (OSError, ValueError):
                pass
            indices.append(int(device.name[5:]))
        return sorted(set(indices))[:max_devices] if devices else list(range(min(max_devices, 3)))
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
