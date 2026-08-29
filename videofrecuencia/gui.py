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

BG = "#121212"
PANEL_BG = "#1e1e1e"
ACCENT = "#00ffcc"
FG = "#ffffff"


class VideoFrequencyApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("VideoFrecuencia - Analizador de frecuencia en vídeo")
        self.root.geometry("980x720")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.capture: VideoCaptureThread | None = None
        self.generator: SyntheticSignalGenerator | None = None
        self.analyzer = FrequencyAnalyzer()
        self.history: list[tuple[float, float]] = []  # (t, freq_dominante)
        self._t0 = time.monotonic()

        self._build_layout()
        self._tick()

    # ------------------------------------------------------------------ UI
    def _build_layout(self) -> None:
        title = tk.Label(
            self.root,
            text="Analizador de VideoFrecuencia",
            font=("Arial", 15, "bold"),
            fg=ACCENT,
            bg=BG,
        )
        title.pack(pady=8)

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # --- Panel de control ---
        control = tk.Frame(main, bg=PANEL_BG, width=280)
        control.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        control.pack_propagate(False)

        tk.Label(
            control, text="Control", font=("Arial", 11, "bold"), fg=FG, bg=PANEL_BG
        ).pack(pady=10)

        self.btn_capturar = tk.Button(
            control,
            text="Iniciar captura (cámara)",
            command=self.toggle_captura,
            bg="#007acc",
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
            bg="#2d2d2d",
            highlightbackground=PANEL_BG,
        )
        self.slider_gen.set(3.0)
        self.slider_gen.pack(fill=tk.X, padx=15, pady=5)

        self.btn_generar = tk.Button(
            control,
            text="Generar señal de prueba",
            command=self.toggle_generacion,
            bg="#d9534f",
            fg=FG,
            font=("Arial", 10, "bold"),
        )
        self.btn_generar.pack(fill=tk.X, padx=15, pady=6)

        self.btn_guardar = tk.Button(
            control,
            text="Exportar histórico a CSV",
            command=self.exportar_csv,
            bg="#555555",
            fg=FG,
            font=("Arial", 10),
        )
        self.btn_guardar.pack(fill=tk.X, padx=15, pady=(20, 6))

        self.status_label = tk.Label(
            control,
            text="Estado: en espera",
            font=("Arial", 10),
            fg="#ffcc00",
            bg=PANEL_BG,
            wraplength=250,
            justify=tk.LEFT,
        )
        self.status_label.pack(pady=10, padx=10, anchor="w")

        self.freq_label = tk.Label(
            control,
            text="Frecuencia dominante: --",
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
        self.ax.set_xlabel("Hz", color=FG, fontsize=8)
        self.ax.set_ylabel("Magnitud", color=FG, fontsize=8)
        self.ax.tick_params(colors=FG, labelsize=7)
        for spine in self.ax.spines.values():
            spine.set_color("#444444")
        (self.line,) = self.ax.plot([], [], color=ACCENT, linewidth=1.3)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    # -------------------------------------------------------------- lógica
    def toggle_captura(self) -> None:
        self._detener_generacion()
        if self.capture is None:
            self.capture = VideoCaptureThread(0)
            if self.capture.start():
                self.analyzer.reset()
                self.btn_capturar.config(text="Detener captura", bg="#c0392b")
                self.status_label.config(text="Capturando desde la cámara…")
            else:
                messagebox.showerror("Error", self.capture.last_error or "No se pudo abrir la cámara.")
                self.capture = None
        else:
            self._detener_captura()

    def toggle_generacion(self) -> None:
        self._detener_captura()
        if self.generator is None:
            self.generator = SyntheticSignalGenerator(freq_hz=self.slider_gen.get())
            self.analyzer.reset()
            self.btn_generar.config(text="Detener señal de prueba", bg="#27ae60")
            self.status_label.config(
                text=f"Generando señal sintética a {self.slider_gen.get():.1f} Hz "
                "para probar el analizador."
            )
        else:
            self._detener_generacion()

    def _detener_captura(self) -> None:
        if self.capture is not None:
            self.capture.stop()
            self.capture = None
            self.btn_capturar.config(text="Iniciar captura (cámara)", bg="#007acc")
            self.status_label.config(text="Estado: en espera")

    def _detener_generacion(self) -> None:
        if self.generator is not None:
            self.generator = None
            self.btn_generar.config(text="Generar señal de prueba", bg="#d9534f")
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
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["t_segundos", "frecuencia_dominante_hz"])
            writer.writerows(self.history)
        messagebox.showinfo("Exportar", f"Guardado en:\n{path}")

    def _on_close(self) -> None:
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

        self.root.after(30, self._tick)

    def _render_frame(self, frame_bgr: np.ndarray) -> None:
        h, w = frame_bgr.shape[:2]
        roi_w, roi_h = int(w * 0.3), int(h * 0.3)
        x0, y0 = (w - roi_w) // 2, (h - roi_h) // 2
        display = frame_bgr.copy()
        cv2.rectangle(display, (x0, y0), (x0 + roi_w, y0 + roi_h), (0, 255, 204), 2)

        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb).resize((480, 360))
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.config(image=imgtk)

    def _update_spectrum(self) -> None:
        result = self.analyzer.compute()
        if result is None:
            return

        self.line.set_data(result.freqs_hz, result.magnitudes)
        if len(result.freqs_hz):
            self.ax.set_xlim(0, min(15, result.freqs_hz[-1]))
        if result.magnitudes.size:
            self.ax.set_ylim(0, max(result.magnitudes.max() * 1.1, 1))
        self.canvas.draw_idle()

        if result.dominant_freq_hz is not None:
            self.freq_label.config(text=f"Frecuencia dominante: {result.dominant_freq_hz:.2f} Hz")
            if 0.7 <= result.dominant_freq_hz <= 3.3 and result.bpm is not None:
                self.bpm_label.config(
                    text=f"≈ {result.bpm:.0f} lpm si es una señal de pulso "
                    "(estimación, no es un dispositivo médico)."
                )
            else:
                self.bpm_label.config(text="")
            self.history.append((time.monotonic() - self._t0, result.dominant_freq_hz))
        else:
            self.freq_label.config(text="Frecuencia dominante: --")
            self.bpm_label.config(text="")


def run() -> None:
    root = tk.Tk()
    VideoFrequencyApp(root)
    root.mainloop()
