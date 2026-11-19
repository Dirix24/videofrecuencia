"""Interfaz gráfica de VideoFrecuencia."""

from __future__ import annotations

import csv
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np
from PIL import Image, ImageTk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .analysis import FrequencyAnalyzer, roi_mean_intensity
from .capture import VideoCaptureThread
from .generator import SyntheticSignalGenerator

BG = "#0b1220"
PANEL_BG = "#172338"
ACCENT = "#5eead4"
FG = "#f1f5f9"
MUTED = "#94a3b8"
BLUE = "#2563eb"
RED = "#b91c1c"


class VideoFrequencyApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("VideoFrecuencia - Analizador de frecuencia en vídeo")
        self.root.geometry("1100x780")
        self.root.minsize(900, 650)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.capture: VideoCaptureThread | None = None
        self.generator: SyntheticSignalGenerator | None = None
        self.analyzer = FrequencyAnalyzer()
        self.history: list[tuple[float, float]] = []  # (t, freq_dominante)
        self._t0 = time.monotonic()
        self._tick_job = None
        self._last_plot_at = 0.0

        self._build_layout()
        self._tick()

    # ------------------------------------------------------------------ UI
    def _build_layout(self) -> None:
        title = tk.Label(
            self.root,
            text="VIDEOFRECUENCIA  /  LABORATORIO ÓPTICO",
            font=("DejaVu Sans", 17, "bold"),
            fg=ACCENT,
            bg=BG,
        )
        title.pack(pady=(16, 4))
        tk.Label(self.root, text="Analiza variaciones de brillo de una cámara o comprueba el algoritmo con una señal conocida.",
                 bg=BG, fg=MUTED, font=("DejaVu Sans", 10)).pack(pady=(0, 8))

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # --- Panel de control ---
        control = tk.Frame(main, bg=PANEL_BG, width=280)
        control.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        control.pack_propagate(False)

        tk.Label(
            control, text="PANEL DE CONTROL", font=("DejaVu Sans", 11, "bold"), fg=FG, bg=PANEL_BG
        ).pack(pady=10)

        self.btn_capturar = tk.Button(
            control,
            text="Iniciar captura (cámara)",
            command=self.toggle_captura,
            bg=BLUE,
            fg=FG,
            font=("Arial", 10, "bold"),
        )
        self.btn_capturar.pack(fill=tk.X, padx=15, pady=6)

        tk.Label(
            control,
            text="Frecuencia señal de prueba (Hz)",
            fg=FG,
            bg=PANEL_BG,
            font=("Arial", 9),
        ).pack(pady=(15, 0))
        self.slider_gen = tk.Scale(
            control,
            from_=0.5,
            to=15.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            fg=FG,
            bg="#263449",
            highlightbackground=PANEL_BG,
        )
        self.slider_gen.set(3.0)
        self.slider_gen.pack(fill=tk.X, padx=15, pady=5)

        self.btn_generar = tk.Button(
            control,
            text="Generar señal de prueba",
            command=self.toggle_generacion,
            bg=BLUE,
            fg=FG,
            font=("Arial", 10, "bold"),
        )
        self.btn_generar.pack(fill=tk.X, padx=15, pady=6)

        self.btn_guardar = tk.Button(
            control,
            text="Exportar histórico a CSV",
            command=self.exportar_csv,
            bg="#334155",
            fg=FG,
            font=("Arial", 10),
        )
        self.btn_guardar.pack(fill=tk.X, padx=15, pady=(20, 6))

        tk.Label(control, text="GUÍA RÁPIDA", bg=PANEL_BG, fg=ACCENT,
                 font=("DejaVu Sans", 10, "bold")).pack(anchor="w", padx=15, pady=(20, 4))
        tk.Label(control, text="1. Prueba con señal sintética.\n2. Activa la cámara y enfoca una luz.\n3. Espera a que se llene la ventana.\n4. Consulta Hz, FPS y el espectro.",
                 bg=PANEL_BG, fg=MUTED, justify=tk.LEFT, wraplength=245,
                 font=("DejaVu Sans", 9)).pack(anchor="w", padx=15)

        self.status_label = tk.Label(
            control,
            text="Estado: en espera",
            font=("Arial", 10),
            fg="#fbbf24",
            bg=PANEL_BG,
            wraplength=250,
            justify=tk.LEFT,
        )
        self.status_label.pack(pady=10, padx=10, anchor="w")

        self.freq_label = tk.Label(
            control,
            text="Frecuencia: sin medición",
            font=("Arial", 12, "bold"),
            fg=ACCENT,
            bg=PANEL_BG,
        )
        self.freq_label.pack(pady=(20, 2))

        self.bpm_label = tk.Label(
            control,
            text="",
            font=("Arial", 9),
            fg="#aaaaaa",
            bg=PANEL_BG,
            wraplength=250,
            justify=tk.LEFT,
        )
        self.bpm_label.pack(pady=2)
        self.metrics_label = tk.Label(control, text="FPS: --  ·  Límite: --",
                                      fg=MUTED, bg=PANEL_BG, font=("DejaVu Sans", 9))
        self.metrics_label.pack(pady=(12, 2))
        self.quality_label = tk.Label(control, text="Calidad: esperando muestras",
                                      fg=MUTED, bg=PANEL_BG, font=("DejaVu Sans", 9),
                                      wraplength=250, justify=tk.LEFT)
        self.quality_label.pack(pady=4)

        # --- Panel derecho: vídeo + espectro ---
        right = tk.Frame(main, bg=BG)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        video_frame = tk.Frame(right, bg="#000000", height=320)
        video_frame.pack(fill=tk.BOTH, expand=True)
        video_frame.pack_propagate(False)
        self.video_label = tk.Label(video_frame, bg="#000000")
        self.video_label.pack(fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(5, 2.6), dpi=100, facecolor=BG)
        self.ax = self.fig.add_subplot(111, facecolor="#1a1a1a")
        self.ax.set_title("ESPECTRO DE FRECUENCIAS", color=FG, fontsize=10, loc="left", pad=12)
        self.ax.set_xlabel("Frecuencia (Hz)", color=MUTED, fontsize=9)
        self.ax.set_ylabel("Magnitud relativa", color=MUTED, fontsize=9)
        self.ax.tick_params(colors=FG, labelsize=7)
        self.ax.grid(True, alpha=0.13, color="#94a3b8")
        for spine in self.ax.spines.values():
            spine.set_color("#444444")
        (self.line,) = self.ax.plot([], [], color=ACCENT, linewidth=1.3)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    # -------------------------------------------------------------- lógica
    def toggle_captura(self) -> None:
        if self.capture is not None:
            self._detener_captura()
            return
        self._detener_generacion()
        if self.capture is None:
            self.capture = VideoCaptureThread(0)
            if self.capture.start():
                self._reset_measurement()
                self.btn_capturar.config(text="Detener captura", bg="#c0392b")
                self.status_label.config(text="Capturando desde la cámara…")
            else:
                messagebox.showerror("Error", self.capture.last_error or "No se pudo abrir la cámara.")
                self.capture = None
        else:
            self._detener_captura()

    def toggle_generacion(self) -> None:
        if self.generator is not None:
            self._detener_generacion()
            return
        self._detener_captura()
        if self.generator is None:
            self.generator = SyntheticSignalGenerator(freq_hz=self.slider_gen.get())
            self._reset_measurement()
            self.btn_generar.config(text="Detener señal de prueba", bg="#27ae60")
            self.status_label.config(
                text=f"Generando señal sintética a {self.slider_gen.get():.1f} Hz "
                "para probar el analizador."
            )
        else:
            self._detener_generacion()

    def _reset_measurement(self) -> None:
        self.analyzer.reset()
        self.history.clear()
        self._t0 = time.monotonic()
        self.freq_label.config(text="Frecuencia: recopilando datos…")
        self.metrics_label.config(text="FPS: --  ·  Límite: --")
        self.quality_label.config(text="Calidad: esperando muestras")
        self.bpm_label.config(text="")
        self.line.set_data([], [])
        self.canvas.draw_idle()

    def _detener_captura(self) -> None:
        if self.capture is not None:
            self.capture.stop()
            self.capture = None
            self.btn_capturar.config(text="Iniciar captura (cámara)", bg=BLUE)
            self.status_label.config(text="Estado: en espera")

    def _detener_generacion(self) -> None:
        if self.generator is not None:
            self.generator = None
            self.btn_generar.config(text="Generar señal de prueba", bg=BLUE)
            self.status_label.config(text="Estado: en espera")

    def exportar_csv(self) -> None:
        if not self.history:
            messagebox.showinfo("Exportar", "Todavía no hay datos que exportar.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="videofrecuencia_historico.csv",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["t_segundos", "frecuencia_dominante_hz"])
                writer.writerows(self.history)
        except OSError as exc:
            messagebox.showerror("Exportar", f"No se pudo guardar el CSV: {exc}")
            return
        messagebox.showinfo("Exportar", f"Guardado en:\n{path}")

    def _on_close(self) -> None:
        if self._tick_job is not None:
            self.root.after_cancel(self._tick_job)
        self._detener_captura()
        self._detener_generacion()
        self.root.destroy()

    # --------------------------------------------------------------- bucle
    def _tick(self) -> None:
        frame_bgr = None

        if self.capture is not None:
            item = self.capture.read()
            if item is not None:
                frame_bgr = item.image_bgr
                self.analyzer.add_sample(roi_mean_intensity(frame_bgr), item.timestamp)
            if self.capture.last_error:
                messagebox.showwarning("Cámara", self.capture.last_error)
                self._detener_captura()

        elif self.generator is not None:
            self.generator.freq_hz = self.slider_gen.get()
            frame_bgr = self.generator.frame()
            self.analyzer.add_sample(
                roi_mean_intensity(frame_bgr, roi_fraction=1.0), time.monotonic()
            )

        if frame_bgr is not None:
            self._render_frame(frame_bgr)
            self._update_spectrum()

        self._tick_job = self.root.after(30, self._tick)

    def _render_frame(self, frame_bgr: np.ndarray) -> None:
        h, w = frame_bgr.shape[:2]
        roi_w, roi_h = int(w * 0.3), int(h * 0.3)
        x0, y0 = (w - roi_w) // 2, (h - roi_h) // 2
        display = frame_bgr.copy()
        cv2.rectangle(display, (x0, y0), (x0 + roi_w, y0 + roi_h), (0, 255, 204), 2)

        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb).resize((480, 360), Image.Resampling.BILINEAR)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.config(image=imgtk)

    def _update_spectrum(self) -> None:
        result = self.analyzer.compute()
        if result is None:
            return

        self.metrics_label.config(text=f"FPS: {result.estimated_fps:.1f}  ·  Límite: {result.nyquist_hz:.1f} Hz")
        self.line.set_data(result.freqs_hz, result.magnitudes)
        if len(result.freqs_hz):
            self.ax.set_xlim(0, min(15, result.freqs_hz[-1]))
        if result.magnitudes.size:
            self.ax.set_ylim(0, max(result.magnitudes.max() * 1.1, 1))
        if time.monotonic() - self._last_plot_at >= 0.15:
            self.canvas.draw_idle()
            self._last_plot_at = time.monotonic()

        if result.dominant_freq_hz is not None:
            self.freq_label.config(text=f"Frecuencia: {result.dominant_freq_hz:.2f} Hz")
            self.quality_label.config(text=f"Señal periódica detectada · contraste espectral {result.peak_snr:.1f}×", fg=ACCENT)
            if 0.7 <= result.dominant_freq_hz <= 3.3 and result.bpm is not None:
                self.bpm_label.config(
                    text=f"≈ {result.bpm:.0f} lpm si es una señal de pulso "
                    "(estimación, no es un dispositivo médico)."
                )
            else:
                self.bpm_label.config(text="")
            self.history.append((time.monotonic() - self._t0, result.dominant_freq_hz))
        else:
            self.freq_label.config(text="Frecuencia: sin detección fiable")
            self.quality_label.config(text="Sin pico suficientemente claro: evita interpretar ruido como una medición.", fg="#fbbf24")
            self.bpm_label.config(text="")


def run() -> None:
    root = tk.Tk()
    VideoFrequencyApp(root)
    root.mainloop()
