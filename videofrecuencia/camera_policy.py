"""Política de selección automática de cámara, independiente de Tkinter."""
from __future__ import annotations


def camera_start_policy(camera_count: int, *, capture_active: bool, generator_active: bool) -> str:
    """Decide qué hacer después de descubrir dispositivos.

    Una cámara: iniciar automáticamente, si no hay otra fuente activa.
    Varias: esperar a que el usuario elija y pulse Iniciar.
    Ninguna: mostrar aviso.
    """
    if camera_count <= 0:
        return "unavailable"
    if capture_active or generator_active:
        return "keep_current"
    if camera_count == 1:
        return "auto_start"
    return "choose"
