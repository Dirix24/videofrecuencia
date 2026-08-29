"""
Captura de vídeo en un hilo independiente.

Se ejecuta en background para no bloquear el bucle principal de Tkinter.
Cada frame capturado se coloca en una cola (con tamaño máximo 1, quedándose
siempre con el más reciente) para que el hilo de la GUI lo consuma cuando
pueda, sin acumular retraso.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Frame:
    image_bgr: np.ndarray
    timestamp: float


class VideoCaptureThread:
    """Envuelve cv2.VideoCapture en un hilo con lectura no bloqueante."""

    def __init__(self, source: int = 0):
        self.source = source
        self._cap: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None
        self._running = threading.Event()
        self._queue: "queue.Queue[Frame]" = queue.Queue(maxsize=1)
        self.last_error: str | None = None

    def start(self) -> bool:
        self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            self.last_error = "No se pudo abrir el dispositivo de vídeo."
            self._cap = None
            return False

        self._running.set()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def _loop(self) -> None:
        while self._running.is_set() and self._cap is not None:
            ok, frame = self._cap.read()
            if not ok:
                self.last_error = "Se perdió la señal de la cámara."
                break
            item = Frame(image_bgr=frame, timestamp=time.monotonic())
            # Nos quedamos siempre con el frame más reciente.
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
            self._queue.put_nowait(item)

    def read(self) -> Frame | None:
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self) -> None:
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def is_running(self) -> bool:
        return self._running.is_set()
