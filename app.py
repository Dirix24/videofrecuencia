import tkinter as tk
import cv2
import numpy as np
from PIL import Image, ImageTk

class VideoFrequencyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VideoFrecuencia - Analizador y Transmisor")
        self.root.geometry("850x650")
        self.root.configure(bg="#121212")

        self.is_capturing = False
        self.is_generating = False
        self.cap = None

        title_label = tk.Label(root, text="Sistemas de VideoFrecuencia (SDR/Análisis)", font=("Arial", 14, "bold"), fg="#00ffcc", bg="#121212")
        title_label.pack(pady=10)

        main_frame = tk.Frame(root, bg="#121212")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        control_frame = tk.Frame(main_frame, bg="#1e1e1e", width=300)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(control_frame, text="Control de Frecuencia", font=("Arial", 11, "bold"), fg="#ffffff", bg="#1e1e1e").pack(pady=10)

        self.slider = tk.Scale(control_frame, from_=400.0, to=900.0, resolution=1.0, orient=tk.HORIZONTAL, 
                               label="MHz (Banda de Video)", fg="#ffffff", bg="#2d2d2d", highlightbackground="#1e1e1e")
        self.slider.set(433.0)
        self.slider.pack(fill=tk.X, padx=15, pady=5)

        self.btn_capturar = tk.Button(control_frame, text="Capturar y Analizar", command=self.toggle_captura, bg="#007acc", fg="#ffffff", font=("Arial", 10, "bold"))
        self.btn_capturar.pack(fill=tk.X, padx=15, pady=10)

        self.btn_generar = tk.Button(control_frame, text="Crear VideoFrecuencia (Test)", command=self.toggle_generacion, bg="#d9534f", fg="#ffffff", font=("Arial", 10, "bold"))
        self.btn_generar.pack(fill=tk.X, padx=15, pady=10)

        self.status_label = tk.Label(control_frame, text="Estado: En espera", font=("Arial", 10), fg="#ffcc00", bg="#1e1e1e", wraplength=250)
        self.status_label.pack(pady=20)

        self.video_frame = tk.Frame(main_frame, bg="#000000", width=500, height=400)
        self.video_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.video_label = tk.Label(self.video_frame, bg="#000000")
        self.video_label.pack(fill=tk.BOTH, expand=True)

        self.update_frame()

    def toggle_captura(self):
        if not self.is_capturing:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.is_capturing = True
                self.is_generating = False
                self.btn_capturar.config(text="Detener Captura", bg="#c0392b")
                self.btn_generar.config(text="Crear VideoFrecuencia (Test)", bg="#d9534f")
                self.status_label.config(text=f"Analizando señal en {self.slider.get()} MHz")
            else:
                self.status_label.config(text="Error: No se detectó dispositivo de captura.")
        else:
            self.detener_todo()

    def toggle_generacion(self):
        if not self.is_generating:
            self.detener_todo()
            self.is_generating = True
            self.btn_generar.config(text="Detener Transmisión", bg="#27ae60")
            self.status_label.config(text=f"Emitiendo VideoFrecuencia artificial en {self.slider.get()} MHz")
        else:
            self.detener_todo()

    def detener_todo(self):
        self.is_capturing = False
        self.is_generating = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.btn_capturar.config(text="Capturar y Analizar", bg="#007acc")
        self.btn_generar.config(text="Crear VideoFrecuencia (Test)", bg="#d9534f")
        self.status_label.config(text="Estado: En espera")
        self.video_label.config(image='')

    def update_frame(self):
        if self.is_capturing and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                freq = self.slider.get()
                cv2.putText(frame, f"FREQ: {freq} MHz", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(cv2image)
                img = img.resize((480, 360))
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.config(image=imgtk)

        elif self.is_generating:
            freq = self.slider.get()
            frame = np.zeros((360, 480, 3), dtype=np.uint8)
            color_val = int((freq - 400) / 500 * 255)
            frame[:] = (color_val, 50, 150)
            cv2.putText(frame, "GENERANDO VIDEOCANAL", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, f"Canal de Frecuencia: {freq} MHz", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)

        self.root.after(15, self.update_frame)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoFrequencyApp(root)
    root.mainloop()
