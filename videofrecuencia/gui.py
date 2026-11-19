"""Interfaz gráfica de VideoFrecuencia."""

from __future__ import annotations

import time
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .analysis import FrequencyAnalyzer, roi_mean_intensity
from .capture import VideoCaptureThread
from .camera_policy import camera_start_policy
from .devices import discover_cameras
from .generator import SyntheticSignalGenerator
from .storage import append_measurements, export_measurements, initialize_measurements

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
        self.root.title("Análisis de frecuencia visual")
        self.root.geometry("1180x800")
        self.root.minsize(950, 700)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.capture: VideoCaptureThread | None = None
        self.generator: SyntheticSignalGenerator | None = None
        self.analyzer = FrequencyAnalyzer()
        self.history: list[tuple[float, float | None]] = []  # (t, freq_dominante)
        self._t0 = time.monotonic()
        self._tick_job = None
        self._last_plot_at = 0.0
        self._last_frame_at = 0.0
        self._last_frequency_setting = 3.0
        self.autosave_path: str | None = None
        self.autosave_enabled = False
        self._autosave_index = 0
        self._last_autosave_at = time.monotonic()
        self._last_recorded_at = 0.0
        self._camera_results: queue.Queue = queue.Queue(maxsize=1)
        self._camera_scan_running = False
        self._camera_choices: dict[str, int] = {}
        self._camera_selection_required = False

        self._build_layout()
        self._tick()
        self.root.after(200, self._refresh_cameras)

    # ------------------------------------------------------------------ UI
    def _build_layout(self) -> None:
        tk.Label(self.root, text="Medición de variaciones periódicas de luz · cámara / prueba",
                 bg=BG, fg=MUTED, font=("DejaVu Sans", 10)).pack(pady=(12, 4))

        self.root.option_add("*Font", "TkDefaultFont 10")
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # --- Panel de control ---
        # Panel desplazable: mantiene todas las opciones accesibles en pantallas pequeñas.
        sidebar = tk.Frame(main, bg=PANEL_BG, width=310)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12), pady=5)
        sidebar.pack_propagate(False)
        scroll_canvas = tk.Canvas(sidebar, bg=PANEL_BG, highlightthickness=0, bd=0)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(sidebar, orient=tk.VERTICAL, command=scroll_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        control = tk.Frame(scroll_canvas, bg=PANEL_BG)
        control_window = scroll_canvas.create_window((0, 0), window=control, anchor="nw")
        control.bind("<Configure>", lambda _e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.bind("<Configure>", lambda e: scroll_canvas.itemconfigure(control_window, width=e.width))

        tk.Label(
            control, text="PANEL DE CONTROL", font=("DejaVu Sans", 11, "bold"), fg=FG, bg=PANEL_BG
        ).pack(pady=10)

        tk.Label(control, text="Dispositivo de cámara", fg=MUTED, bg=PANEL_BG).pack(anchor="w", padx=15, pady=(8, 0))
        self.camera_selection = tk.StringVar(value="Buscando cámaras…")
        self.camera_combo = ttk.Combobox(control, textvariable=self.camera_selection,
                                         state="readonly", width=28)
        self.camera_combo.pack(fill=tk.X, padx=15, pady=(3, 5))
        self.camera_combo.bind("<<ComboboxSelected>>", self._on_camera_selected)
        self.btn_refresh_cameras = tk.Button(control, text="Buscar cámaras disponibles",
                                              command=self._refresh_cameras, bg="#334155", fg=FG)
        self.btn_refresh_cameras.pack(fill=tk.X, padx=15, pady=(0, 8))
        self.camera_hint = tk.Label(control, text="Comprobando dispositivos…",
                                    bg=PANEL_BG, fg=MUTED, wraplength=265, justify=tk.LEFT)
        self.camera_hint.pack(anchor="w", padx=15, pady=(0, 8))
        tk.Label(control, text="Tamaño de región central (%)", fg=MUTED, bg=PANEL_BG).pack(anchor="w", padx=15)
        self.roi_slider = tk.Scale(control, from_=10, to=100, resolution=10, orient=tk.HORIZONTAL,
                                    bg=PANEL_BG, fg=FG, highlightthickness=0, troughcolor="#334155")
        self.roi_slider.set(30)
        self.roi_slider.pack(fill=tk.X, padx=15)
        tk.Label(control, text="Ventana de análisis (segundos)", fg=MUTED, bg=PANEL_BG).pack(anchor="w", padx=15)
        self.window_slider = tk.Scale(control, from_=3, to=12, resolution=1, orient=tk.HORIZONTAL,
                                       bg=PANEL_BG, fg=FG, highlightthickness=0, troughcolor="#334155",
                                       command=self._on_window_change)
        self.window_slider.set(6)
        self.window_slider.pack(fill=tk.X, padx=15)

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
            to=10.0,
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
        self.btn_guardar.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(control, text="GUARDADO DE DATOS", fg=ACCENT, bg=PANEL_BG,
                 font=("TkDefaultFont", 10, "bold")).pack(anchor="w", padx=15, pady=(12, 5))
        self.autosave_var = tk.BooleanVar(value=False)
        self.autosave_checkbox = tk.Checkbutton(
            control, text="Autoguardar en CSV", variable=self.autosave_var,
            command=self._toggle_autosave, bg=PANEL_BG, fg=FG, selectcolor="#334155",
            activebackground=PANEL_BG, activeforeground=FG, anchor="w")
        self.autosave_checkbox.pack(fill=tk.X, padx=12)
        tk.Button(control, text="Elegir archivo de autoguardado…", command=self._choose_autosave_file,
                  bg="#334155", fg=FG).pack(fill=tk.X, padx=15, pady=(4, 3))
        self.autosave_label = tk.Label(control, text="Desactivado · elige una ruta para activarlo",
                                      bg=PANEL_BG, fg=MUTED, wraplength=265, justify=tk.LEFT)
        self.autosave_label.pack(fill=tk.X, padx=15, pady=(1, 5))
        tk.Button(control, text="Reiniciar medición", command=self._reset_measurement,
                  bg="#334155", fg=FG).pack(fill=tk.X, padx=15, pady=4)

        tk.Label(control, text="Consejo: empieza con 3 Hz y comprueba los FPS.",
                 bg=PANEL_BG, fg=MUTED, justify=tk.LEFT, wraplength=245,
                 font=("DejaVu Sans", 9)).pack(anchor="w", padx=15, pady=(8, 2))

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

        video_frame = tk.Frame(right, bg="#000000", height=280)
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
            if self._camera_scan_running:
                messagebox.showinfo("Cámara", "Espera a que termine la búsqueda de cámaras.")
                return
            if self._camera_selection_required:
                messagebox.showinfo("Cámara", "Hay varias cámaras. Selecciona una en la lista antes de iniciar.")
                return
            source = self._camera_choices.get(self.camera_selection.get())
            if source is None:
                messagebox.showinfo("Cámara", "Pulsa Buscar cámaras disponibles y selecciona una.")
                return
            self.capture = VideoCaptureThread(source)
            if self.capture.start():
                self._reset_measurement()
                self.btn_capturar.config(text="Detener captura", bg="#c0392b")
                self.status_label.config(text="Capturando desde la cámara…")
            else:
                messagebox.showerror("Error", self.capture.last_error or "No se pudo abrir la cámara.")
                self.capture = None
        else:
            self._detener_captura()

    def _on_camera_selected(self, _event=None) -> None:
        if self.camera_selection.get() in self._camera_choices:
            self._camera_selection_required = False
            self.camera_hint.config(text=f"Seleccionada: {self.camera_selection.get()}. Pulsa Iniciar captura.", fg=ACCENT)

    def _refresh_cameras(self) -> None:
        if self._camera_scan_running:
            return
        if self.capture is not None:
            self.camera_hint.config(text="Detén la captura antes de buscar cámaras.")
            return
        self._camera_scan_running = True
        self.btn_refresh_cameras.config(state=tk.DISABLED)
        self.btn_capturar.config(state=tk.DISABLED)
        self.camera_hint.config(text="Buscando cámaras conectadas…")

        def worker() -> None:
            try:
                result = discover_cameras()
                self._camera_results.put((result, None))
            except Exception as exc:
                self._camera_results.put(([], str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_camera_results(self) -> None:
        try:
            found, error = self._camera_results.get_nowait()
        except queue.Empty:
            return
        self._camera_scan_running = False
        self.btn_refresh_cameras.config(state=tk.NORMAL)
        self.btn_capturar.config(state=tk.NORMAL)
        previous = self._camera_choices.get(self.camera_selection.get())
        self._camera_choices = {label: index for index, label in found}
        choices = list(self._camera_choices)
        self.camera_combo.config(values=choices)
        policy = camera_start_policy(
            len(found),
            capture_active=self.capture is not None,
            generator_active=self.generator is not None,
        )
        if policy == "unavailable":
            self._camera_selection_required = False
            self.camera_selection.set("Sin cámaras disponibles")
            self.camera_hint.config(text=error or "No se detectaron cámaras. Comprueba permisos y conexión.", fg="#fbbf24")
        elif policy == "auto_start":
            self._camera_selection_required = False
            self.camera_selection.set(choices[0])
            self.camera_hint.config(text="Una cámara detectada: iniciando automáticamente…", fg=ACCENT)
            self.toggle_captura()
        elif policy == "choose":
            # Nunca elegimos arbitrariamente una webcam cuando hay varias.
            # Si el usuario ya eligió una anteriormente, respetamos esa elección.
            selected = next((label for label, index in found if index == previous), None)
            self._camera_selection_required = selected is None
            self.camera_selection.set(selected or "Selecciona una cámara…")
            self.camera_hint.config(
                text=("Cámara anterior conservada. Pulsa Iniciar captura." if selected
                      else f"{len(found)} cámaras detectadas. Elige cuál utilizar en la lista."),
                fg=ACCENT if selected else "#fbbf24",
            )
        else:
            self._camera_selection_required = False
            selected = next((label for label, index in found if index == previous), None)
            self.camera_selection.set(selected or choices[0])
            self.camera_hint.config(text="Dispositivo detectado; se mantiene la fuente activa.", fg=MUTED)

    def toggle_generacion(self) -> None:
        if self.generator is not None:
            self._detener_generacion()
            return
        self._detener_captura()
        if self.generator is None:
            self.generator = SyntheticSignalGenerator(freq_hz=self.slider_gen.get())
            self._last_frequency_setting = self.slider_gen.get()
            self._reset_measurement()
            self.btn_generar.config(text="Detener señal de prueba", bg="#27ae60")
            self.status_label.config(
                text=f"Generando señal sintética a {self.slider_gen.get():.1f} Hz "
                "para probar el analizador."
            )
        else:
            self._detener_generacion()

    def _on_window_change(self, _value: str) -> None:
        self.analyzer.window_seconds = float(self.window_slider.get())
        if hasattr(self, "freq_label"):
            self._reset_measurement()

    def _reset_measurement(self) -> None:
        self.analyzer.reset()
        self._flush_autosave()
        self.history.clear()
        self._autosave_index = 0
        self._last_recorded_at = 0.0
        self._t0 = time.monotonic()
        self._last_frame_at = 0.0
        self._last_autosave_at = time.monotonic()
        self.freq_label.config(text="Frecuencia: recopilando datos…")
        self.metrics_label.config(text="FPS: --  ·  Límite: --")
        self.quality_label.config(text="Calidad: esperando muestras")
        self.bpm_label.config(text="")
        self.line.set_data([], [])
        self.canvas.draw_idle()

    def _detener_captura(self) -> None:
        if self.capture is not None:
            self._flush_autosave()
            self.capture.stop()
            self.capture = None
            self.btn_capturar.config(text="Iniciar captura (cámara)", bg=BLUE)
            self.status_label.config(text="Estado: en espera")

    def _detener_generacion(self) -> None:
        if self.generator is not None:
            self._flush_autosave()
            self.generator = None
            self.btn_generar.config(text="Generar señal de prueba", bg=BLUE)
            self.status_label.config(text="Estado: en espera")

    def _choose_autosave_file(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Selecciona el CSV de autoguardado",
            defaultextension=".csv", filetypes=[("Archivos CSV", "*.csv")],
            initialfile="mediciones.csv",
        )
        if not path:
            return
        # Crear la cabecera inmediatamente confirma la ruta y permisos.
        # El selector permite escoger carpeta y nombre en Linux/Windows/macOS.
        self._flush_autosave()
        try:
            initialize_measurements(path)
        except (OSError, ValueError, UnicodeError) as exc:
            messagebox.showerror("Autoguardado", f"No se pudo preparar el archivo:\\n{exc}")
            return
        self.autosave_path = str(Path(path).expanduser().resolve())
        self.autosave_enabled = True
        self.autosave_var.set(True)
        self._autosave_index = len(self.history)
        self.autosave_label.config(text=f"Guardando en: {self.autosave_path}", fg=ACCENT)

    def _toggle_autosave(self) -> None:
        if self.autosave_var.get():
            if not self.autosave_path:
                self._choose_autosave_file()
                if not self.autosave_path:
                    self.autosave_var.set(False)
                return
            self.autosave_enabled = True
            self._autosave_index = len(self.history)
            self.autosave_label.config(text=f"Activo · {self.autosave_path}", fg=ACCENT)
        else:
            self._flush_autosave()
            self.autosave_enabled = False
            self.autosave_label.config(text="Pausado · archivo conservado", fg=MUTED)

    def _flush_autosave(self) -> None:
        if not self.autosave_enabled or not self.autosave_path:
            return
        pending = self.history[self._autosave_index:]
        if not pending:
            return
        try:
            written = append_measurements(self.autosave_path, pending)
        except (OSError, ValueError, UnicodeError) as exc:
            self.autosave_enabled = False
            self.autosave_var.set(False)
            self.autosave_label.config(text="Error al guardar · exporta los datos manualmente", fg="#fbbf24")
            messagebox.showerror("Autoguardado", f"No se pudo guardar el CSV: {exc}")
            return
        self._autosave_index += written
        self._last_autosave_at = time.monotonic()
        self.autosave_label.config(text=f"Guardado · {self.autosave_path}", fg=ACCENT)

    def exportar_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="videofrecuencia_historico.csv",
        )
        if not path:
            return
        try:
            export_measurements(path, self.history)
        except OSError as exc:
            messagebox.showerror("Exportar", f"No se pudo guardar el CSV: {exc}")
            return
        messagebox.showinfo("Exportar", f"Guardado en:\n{path}")

    def _on_close(self) -> None:
        if self._tick_job is not None:
            self.root.after_cancel(self._tick_job)
        self._flush_autosave()
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
                self.analyzer.add_sample(roi_mean_intensity(frame_bgr, self.roi_slider.get() / 100.0), item.timestamp)
            if self.capture.last_error:
                messagebox.showwarning("Cámara", self.capture.last_error)
                self._detener_captura()

        elif self.generator is not None:
            requested = self.slider_gen.get()
            if requested != self._last_frequency_setting:
                self.generator.freq_hz = requested
                self._last_frequency_setting = requested
                self._reset_measurement()
            frame_bgr = self.generator.frame()
            now = time.monotonic()
            if now > self._last_frame_at:
                self.analyzer.add_sample(roi_mean_intensity(frame_bgr, roi_fraction=1.0), now)
                self._last_frame_at = now

        if frame_bgr is not None:
            self._render_frame(frame_bgr)
            self._update_spectrum()

        if self.autosave_enabled and time.monotonic() - self._last_autosave_at >= 2.0:
            self._flush_autosave()
        self._apply_camera_results()
        self._tick_job = self.root.after(30, self._tick)

    def _render_frame(self, frame_bgr: np.ndarray) -> None:
        h, w = frame_bgr.shape[:2]
        fraction = self.roi_slider.get() / 100.0
        roi_w, roi_h = max(1, int(w * fraction)), max(1, int(h * fraction))
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
        requested = self.slider_gen.get() if self.generator is not None else None
        # Cerca de Nyquist la señal sintética puede plegarse y dar una lectura falsa.
        invalid_test = requested is not None and requested >= 0.4 * result.estimated_fps
        self.line.set_data(result.freqs_hz, result.magnitudes)
        if len(result.freqs_hz):
            self.ax.set_xlim(0, min(15, result.freqs_hz[-1]))
        if result.magnitudes.size:
            self.ax.set_ylim(0, max(result.magnitudes.max() * 1.1, 1))
        if time.monotonic() - self._last_plot_at >= 0.15:
            self.canvas.draw_idle()
            self._last_plot_at = time.monotonic()

        if invalid_test:
            self.freq_label.config(text="Prueba fuera del rango fiable")
            self.quality_label.config(text=f"Baja la prueba por debajo de {0.4 * result.estimated_fps:.1f} Hz o mejora los FPS.", fg="#fbbf24")
            self.bpm_label.config(text="")
        elif result.dominant_freq_hz is not None:
            self.freq_label.config(text=f"Frecuencia: {result.dominant_freq_hz:.2f} Hz")
            self.quality_label.config(text=f"Señal periódica detectada · contraste espectral {result.peak_snr:.1f}×", fg=ACCENT)
            if 0.7 <= result.dominant_freq_hz <= 3.3 and result.bpm is not None:
                self.bpm_label.config(
                    text=f"≈ {result.bpm:.0f} lpm si es una señal de pulso "
                    "(estimación, no es un dispositivo médico)."
                )
            else:
                self.bpm_label.config(text="")
            now = time.monotonic()
            # Registrar una vez por segundo, no una fila por redibujado de GUI.

        else:
            self.freq_label.config(text="Frecuencia: sin detección fiable")
            self.quality_label.config(text="Sin pico suficientemente claro: evita interpretar ruido como una medición.", fg="#fbbf24")
            self.bpm_label.config(text="")

        # Guardar también los instantes sin detección: columna de frecuencia vacía.
        # Así siempre hay datos de sesión para exportar y el autoguardado no parece fallar.
        now = time.monotonic()
        if now - self._last_recorded_at >= 1.0:
            value = None if invalid_test else result.dominant_freq_hz
            self.history.append((now - self._t0, value))
            self._last_recorded_at = now


def run() -> None:
    root = tk.Tk()
    VideoFrequencyApp(root)
    root.mainloop()
