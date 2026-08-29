# VideoFrecuencia 📡📺

Aplicación de escritorio que analiza, **de verdad**, la frecuencia temporal
de una señal de vídeo mediante FFT (transformada rápida de Fourier) sobre
el brillo medio de una región de la imagen a lo largo del tiempo.

> Esta versión sustituye a la anterior, que solo simulaba un "receptor/
> transmisor de radiofrecuencia" con un slider decorativo (los MHz no
> afectaban a nada real). Ahora la app hace análisis de señal genuino sobre
> vídeo, que es lo que su nombre sugiere y lo que una webcam puede medir.

## ¿Qué hace?

- **Captura en vivo** desde la webcam en un hilo aparte (no bloquea la GUI).
- Calcula la intensidad media (luma) de una región central del frame en
  cada instante y mantiene una ventana deslizante de esos valores.
- Aplica **FFT** sobre esa serie temporal para encontrar la frecuencia
  dominante de oscilación del brillo, y la muestra en un espectro en vivo.
- **Casos de uso reales**:
  - Detectar **parpadeo (flicker)** de luces LED/fluorescentes o de
    pantallas con PWM (habitualmente en el rango de 50–1000+ Hz, aunque
    con una webcam normal solo se puede muestrear de forma fiable hasta
    la mitad de sus fps).
  - **Estimación aproximada de pulso** (fotopletismografía remota, rPPG):
    apoyando un dedo sobre la cámara con el flash/luz encendida, los
    cambios de color por el bombeo de sangre generan una oscilación en el
    rango 0.7–3.3 Hz (42–200 lpm). **No es un dispositivo médico.**
- **Generador de señal de prueba**: crea un vídeo sintético que parpadea a
  una frecuencia elegida por el usuario (0.5–15 Hz), útil para calibrar y
  verificar que el analizador detecta correctamente una frecuencia conocida
  sin depender de hardware externo.
- **Exportación a CSV** del histórico de frecuencia dominante detectada.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Requiere una cámara accesible por OpenCV (`cv2.VideoCapture(0)`).

## Uso

```bash
python app.py
```

1. Pulsa **"Iniciar captura (cámara)"** para analizar la señal de la webcam
   en vivo, o **"Generar señal de prueba"** para ver el analizador trabajar
   sobre una señal sintética con frecuencia conocida (ajustable con el
   deslizador).
2. El recuadro verde sobre el vídeo marca la región de interés (ROI) que se
   está midiendo.
3. El panel inferior muestra el espectro de frecuencias en tiempo real y la
   frecuencia dominante detectada.
4. Usa **"Exportar histórico a CSV"** para guardar la serie de frecuencias
   detectadas y analizarla después (por ejemplo, en una hoja de cálculo).

## Estructura del proyecto

```
videofrecuencia/
├── app.py                      # Punto de entrada
├── videofrecuencia/
│   ├── capture.py               # Captura de cámara en hilo aparte
│   ├── analysis.py              # Analizador FFT (ventana, FFT, pico dominante)
│   ├── generator.py             # Generador de señal sintética de prueba
│   └── gui.py                   # Interfaz Tkinter + gráfico matplotlib
├── tests/
│   └── test_analysis.py         # Tests del analizador (sin necesitar cámara)
├── requirements.txt
└── requirements-dev.txt
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Los tests verifican el módulo de análisis con señales sintéticas (no
requieren cámara ni entorno gráfico), incluyendo que una senoidal de
frecuencia conocida se detecta correctamente.

## Limitaciones honestas

- La frecuencia máxima detectable está limitada por los fps reales de la
  cámara (Nyquist = fps/2), normalmente 15 Hz como máximo en una webcam
  típica de 30 fps.
- No es un analizador de espectro de radiofrecuencia: no puede medir
  señales de radio en MHz/GHz, solo variaciones de brillo capturables por
  una cámara de vídeo.
- La estimación de pulso es solo demostrativa y sensible al ruido, al
  movimiento y a la iluminación.

## Licencia

MIT (o la que prefieras añadir).
