# VideoFrecuencia

**Laboratorio de análisis de frecuencia visual con webcam y FFT.**

VideoFrecuencia es una aplicación de escritorio en Python que mide **variaciones periódicas del brillo** de una zona de la imagen. Presenta el vídeo, un espectro de frecuencias y una estimación de la frecuencia dominante cuando hay una señal suficientemente clara. También incorpora un generador sintético para comprobar el algoritmo sin cámara.

> **Importante:** no mide radiofrecuencias ni el refresco de una pantalla de forma directa. No es un dispositivo médico ni un instrumento calibrado. Un valor mostrado es una estimación condicionada por el muestreo y la iluminación.

## Qué puedes hacer

| Función | Descripción |
| --- | --- |
| Cámara en directo | Captura vídeo con OpenCV sin bloquear la ventana |
| Región de interés (ROI) | Analiza el brillo medio del cuadrado central |
| FFT | Calcula el espectro de la señal de luminosidad en una ventana temporal |
| Detección de señal | Evita mostrar frecuencias cuando la imagen es prácticamente plana, la ventana es demasiado corta o no destaca un pico claro |
| Diagnóstico | Indica FPS estimados, límite de Nyquist y contraste del pico |
| Señal sintética | Genera un parpadeo configurable para verificar el analizador |
| CSV | Exporta el histórico de frecuencias detectadas |

## Inicio rápido

Necesitas **Python 3.10 o superior**, una instalación de Tkinter y, para la captura real, una webcam reconocida por OpenCV.

En Debian/Ubuntu/MX Linux, si falta Tkinter:

```bash
sudo apt update
sudo apt install python3-tk python3-venv
```

Instalación desde GitHub:

```bash
git clone https://github.com/Dirix24/videofrecuencia.git
cd videofrecuencia
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

En Windows, activa el entorno con `.venv\Scripts\activate` y ejecuta `python app.py`.

## Cómo utilizarlo

### 1. Comprueba el algoritmo sin webcam

1. Abre la aplicación y ajusta **Frecuencia señal de prueba** a 3,0 Hz.
2. Pulsa **Generar señal de prueba**.
3. Espera unos segundos hasta que se acumule una ventana suficiente.
4. Comprueba que el espectro muestra un pico cerca de 3 Hz y que la frecuencia indicada se aproxima a la configurada.
5. Detén la señal antes de cambiar de modo.

La señal sintética se genera desde el reloj del ordenador y la frecuencia real observada puede variar si la interfaz no puede dibujar frames con suficiente rapidez. Por encima de la mitad de los FPS reales pueden aparecer frecuencias falsas por *aliasing*.

### 2. Analiza una fuente real

1. Pulsa **Iniciar captura (cámara)** y autoriza el acceso si tu sistema lo solicita.
2. Apunta a una zona con iluminación estable y procura mantener la cámara quieta.
3. Coloca la fuente que quieres estudiar dentro del **cuadrado central**.
4. Espera a que se recopilen muestras y observa el gráfico, los FPS y el estado de calidad.
5. Si aparece **«sin detección fiable»**, no interpretes el pico más alto como una frecuencia confirmada.

La luz ambiente, los movimientos, la exposición automática, el balance de blancos y los FPS variables pueden alterar las mediciones.

### 3. Exporta resultados

Usa **Exportar histórico a CSV**. El archivo contiene `t_segundos` y `frecuencia_dominante_hz` para las mediciones con pico detectado. Al iniciar una nueva captura o señal de prueba se limpia el histórico para no mezclar sesiones.

## Cómo interpretar las medidas

- **Hz:** ciclos de cambio de brillo por segundo; por ejemplo, 3 Hz son tres oscilaciones por segundo.
- **FPS:** número estimado de muestras de vídeo por segundo, calculado a partir de los timestamps.
- **Límite (Nyquist):** aproximadamente FPS / 2; una webcam de 30 FPS no puede medir de forma fiable un parpadeo de 50/60 Hz con este método.
- **Contraste espectral:** relación entre el pico y el fondo del espectro; no es un porcentaje de precisión ni una garantía de detección correcta.
- **Sin detección fiable:** falta duración, variación luminosa suficiente o un pico claramente destacado. Es preferible a mostrar una cifra engañosa.

La FFT se calcula sobre el brillo medio de la ROI, interpolando las muestras a intervalos uniformes y aplicando eliminación de tendencia y ventana de Hann. Este método es didáctico y no compensa todos los artefactos de la cámara.

## Pruebas automáticas

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -v
python -m compileall -q videofrecuencia
```

Las pruebas verifican detección de señales sintéticas, ausencia de detección en imágenes planas o con ruido débil, validación de datos y situaciones simuladas de desconexión de cámara. **No sustituyen la comprobación con una webcam real y tu sistema operativo.**

## Solución de problemas

| Problema | Qué revisar |
| --- | --- |
| La cámara no abre | Cierra otras aplicaciones que la usen y comprueba los permisos del sistema |
| No aparece frecuencia | Espera unos segundos, mejora la iluminación y reduce los movimientos |
| Resultado inesperado | Comprueba FPS y Nyquist; evita frecuencias de prueba cercanas al límite |
| No abre la ventana | Comprueba que Tkinter está instalado y que tienes una sesión gráfica |
| No se guarda el CSV | Elige una carpeta con permisos de escritura |

## Arquitectura

- `app.py`: entrada de la aplicación.
- `videofrecuencia/gui.py`: interfaz Tkinter y gráfico Matplotlib.
- `videofrecuencia/capture.py`: adquisición de vídeo en hilo independiente.
- `videofrecuencia/analysis.py`: ROI, serie temporal, FFT y validación de picos.
- `videofrecuencia/generator.py`: señal de prueba.
- `tests/`: pruebas de regresión.

## Estado del proyecto y límites

Proyecto experimental de análisis óptico, no un medidor de laboratorio. Los resultados de la webcam dependen del hardware, los controladores y las condiciones de captura. **No utilizar para diagnóstico médico, decisiones de seguridad ni mediciones certificadas.**

Autor: [Dirix24](https://github.com/Dirix24). No se declara una licencia hasta que el propietario añada un archivo `LICENSE`.
