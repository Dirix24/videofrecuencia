"""
Análisis espectral de una señal de vídeo (serie temporal de intensidad).

Idea general
------------
Cada frame se reduce a un único número (la intensidad media de una región
de interés, en escala de grises). Con una ventana deslizante de esos valores
en el tiempo, se aplica una FFT para encontrar a qué frecuencia oscila el
brillo de la escena. Esto tiene aplicaciones reales:

- Detectar parpadeo (flicker) de luces o pantallas: fluorescentes/LED con
  PWM suelen parpadear a 50/60 Hz o a frecuencias de refresco específicas.
- Estimación aproximada del pulso cardíaco (rPPG) apuntando la cámara a la
  yema del dedo o al rostro: la sangre bombeada cambia ligeramente el color
  reflejado con cada latido (rango típico 0.7-3.3 Hz = 42-200 lpm).

Esto NO es un dispositivo médico ni un medidor de precisión: sirve como
demostración didáctica de procesado de señal sobre vídeo real.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np


@dataclass
class SpectrumResult:
    freqs_hz: np.ndarray
    magnitudes: np.ndarray
    dominant_freq_hz: float | None
    estimated_fps: float | None
    bpm: float | None
    peak_snr: float | None = None
    nyquist_hz: float | None = None
    duration_seconds: float | None = None
    sampling_jitter: float | None = None
    resolution_hz: float | None = None
    confidence: str = "insuficiente"


@dataclass
class FrequencyAnalyzer:
    """Mantiene un buffer temporal de intensidades y calcula su espectro."""

    window_seconds: float = 6.0
    max_samples: int = 512
    min_freq_hz: float = 0.5
    max_freq_hz: float = 15.0
    min_duration_seconds: float = 1.5
    min_signal_std: float = 0.35
    min_peak_snr: float = 5.0
    _values: deque = field(default_factory=deque, init=False)
    _timestamps: deque = field(default_factory=deque, init=False)

    def add_sample(self, value: float, timestamp: float) -> None:
        if not np.isfinite(value) or not np.isfinite(timestamp):
            raise ValueError("La intensidad y el tiempo deben ser finitos")
        if self._timestamps and timestamp <= self._timestamps[-1]:
            raise ValueError("Los tiempos deben aumentar estrictamente")
        self._values.append(value)
        self._timestamps.append(timestamp)
        # Purga muestras fuera de la ventana temporal.
        while self._timestamps and (timestamp - self._timestamps[0]) > self.window_seconds:
            self._timestamps.popleft()
            self._values.popleft()
        while len(self._values) > self.max_samples:
            self._timestamps.popleft()
            self._values.popleft()

    def reset(self) -> None:
        self._values.clear()
        self._timestamps.clear()

    @property
    def sample_count(self) -> int:
        return len(self._values)

    def compute(self) -> SpectrumResult | None:
        n = len(self._values)
        if n < 16:
            return None

        timestamps = np.asarray(self._timestamps, dtype=np.float64)
        values = np.asarray(self._values, dtype=np.float64)

        duration = timestamps[-1] - timestamps[0]
        if duration <= 0:
            return None
        intervals = np.diff(timestamps)
        median_interval = float(np.median(intervals))
        sampling_jitter = float(np.std(intervals) / median_interval) if median_interval > 0 else float("inf")
        estimated_fps = (n - 1) / duration
        if not np.isfinite(estimated_fps) or estimated_fps <= 0:
            return None

        # Re-muestreo a intervalos regulares (la cámara no entrega frames
        # a intervalos perfectamente constantes) mediante interpolación lineal.
        regular_t = np.linspace(timestamps[0], timestamps[-1], n)
        regular_values = np.interp(regular_t, timestamps, values)

        # Quita la tendencia y aplica ventana de Hann para reducir fugas
        # espectrales antes de la FFT.
        # Ajustar sobre tiempo relativo evita errores de precisión con
        # marcas monotónicas grandes y muestra si la señal es plana.
        relative_t = regular_t - regular_t[0]
        detrended = regular_values - np.polyval(
            np.polyfit(relative_t, regular_values, 1), relative_t
        )
        window = np.hanning(n)
        windowed = detrended * window

        spectrum = np.fft.rfft(windowed)
        freqs = np.fft.rfftfreq(n, d=1.0 / estimated_fps)
        magnitudes = np.abs(spectrum)

        # Margen del 20 % respecto a Nyquist: evita reportar picos cerca del límite,
        # donde las estimaciones con cámaras de FPS variables son poco fiables.
        # No puede descartar aliasing de señales reales por encima de Nyquist.
        # Ignora la banda fuera del rango de interés (incluye la componente DC).
        # Los extremos de rfftfreq pueden superar el límite por redondeo
        # (por ejemplo 9.600000000000001 frente a 9.6). Aplicamos
        # tolerancia al redondeo para no declarar una frecuencia fuera del
        # margen nominal de muestreo.
        safe_max_hz = min(self.max_freq_hz, estimated_fps * 0.4)
        band = (freqs >= self.min_freq_hz) & (freqs < np.nextafter(safe_max_hz, -np.inf))
        dominant_freq = None
        bpm = None
        peak_snr = None
        resolution_hz = estimated_fps / n
        if np.any(band):
            band_freqs = freqs[band]
            band_mag = magnitudes[band]
            if band_mag.size:
                peak = float(band_mag.max())
                # Comparamos el pico con el nivel de fondo robusto.
                noise_floor = float(np.median(band_mag))
                peak_snr = peak / max(noise_floor, 1e-9)
                if (duration >= self.min_duration_seconds
                        and float(np.std(detrended)) >= self.min_signal_std
                        and peak_snr >= self.min_peak_snr):
                    peak_index = int(np.argmax(band_mag))
                    dominant_freq = float(band_freqs[peak_index])
                    # Interpolación parabólica sub-bin: mejora estimaciones
                    # entre bins sin prometer resolución instrumental.
                    if 0 < peak_index < len(band_mag) - 1:
                        left, center, right = np.log(np.maximum(
                            band_mag[peak_index - 1:peak_index + 2], 1e-12
                        ))
                        denominator = left - 2 * center + right
                        if denominator < -1e-12:
                            offset = float(np.clip(0.5 * (left - right) / denominator, -0.5, 0.5))
                            candidate = dominant_freq + offset * resolution_hz
                            if self.min_freq_hz <= candidate < safe_max_hz:
                                dominant_freq = candidate
                    # Si los intervalos de captura fluctúan demasiado, no
                    # mostramos una cifra que parezca más fiable de lo que es.
                    if sampling_jitter <= 0.25:
                        bpm = dominant_freq * 60.0
                    else:
                        dominant_freq = None

        return SpectrumResult(
            freqs_hz=freqs,
            magnitudes=magnitudes,
            dominant_freq_hz=dominant_freq,
            estimated_fps=estimated_fps,
            bpm=bpm,
            peak_snr=peak_snr,
            nyquist_hz=estimated_fps / 2,
            duration_seconds=duration,
            sampling_jitter=sampling_jitter,
            resolution_hz=resolution_hz,
            confidence=(
                "insuficiente" if dominant_freq is None else
                "estable" if peak_snr is not None and peak_snr >= 10 and sampling_jitter <= 0.10 else
                "orientativa"
            ),
        )


def roi_mean_intensity(frame_bgr: np.ndarray, roi_fraction: float = 0.3) -> float:
    """Intensidad media en escala de grises de una región central del frame.

    Usar una región central (en vez del frame completo) reduce el ruido de
    fondo y hace que el flicker de una fuente de luz concreta, o el color de
    un dedo apoyado en la cámara, dominen la señal.
    """
    if not 0 < roi_fraction <= 1:
        raise ValueError("roi_fraction debe estar entre 0 y 1")
    if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
        raise ValueError("Se necesita una imagen BGR con tres canales")
    h, w = frame_bgr.shape[:2]
    if h == 0 or w == 0:
        raise ValueError("La imagen no puede estar vacía")
    rh, rw = max(1, int(h * roi_fraction)), max(1, int(w * roi_fraction))
    y0, x0 = (h - rh) // 2, (w - rw) // 2
    roi = frame_bgr[y0 : y0 + rh, x0 : x0 + rw]
    gray = np.dot(roi[..., :3].astype(np.float64), [0.114, 0.587, 0.299])  # BGR -> luma
    return float(gray.mean())
