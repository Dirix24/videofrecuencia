# VideoFrecuencia

**Laboratorio de análisis de frecuencia visual con webcam y FFT.**

VideoFrecuencia es una aplicación de escritorio en Python que mide **variaciones periódicas del brillo** de una zona de la imagen. Presenta el vídeo, un espectro de frecuencias y una estimación de la frecuencia dominante cuando hay una señal suficientemente clara. También incorpora un generador sintético para comprobar el algoritmo sin cámara.

> **Importante:** no mide radiofrecuencias ni el refresco de una pantalla de forma directa. No es un dispositivo médico ni un instrumento calibrado. Un valor mostrado es una estimación condicionada por el muestreo y la iluminación.

## Qué puedes hacer

| Función | Descripción |
| --- | --- |
| Cámara en directo | Captura vídeo con OpenCV sin bloquear la ventana; selección de cámara por índice (0–9) |
| Región de interés (ROI) | Ajusta el cuadrado central entre el 10 % y el 100 % de la imagen |
| FFT | Calcula el espectro con ventana configurable de 3 a 12 segundos |
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

La señal sintética se genera desde el reloj del ordenador y la frecuencia real observada puede variar si la interfaz no puede dibujar frames con suficiente rapidez. La interfaz impide interpretar como válida una prueba configurada a partir del 40 % de los FPS observados, dejando margen respecto a Nyquist. **Ejemplo real:** 15 Hz con 23,7 FPS no se puede medir correctamente; puede aparecer una frecuencia falsa cercana a 8–9 Hz por *aliasing*. Para pruebas repetibles, empieza con 2–5 Hz y comprueba el indicador FPS.

### 2. Analiza una fuente real

1. Selecciona el índice de cámara (normalmente **0**; prueba **1** si tienes una segunda cámara) y pulsa **Iniciar captura (cámara)** y autoriza el acceso si tu sistema lo solicita.
2. Apunta a una zona con iluminación estable y procura mantener la cámara quieta.
3. Coloca la fuente que quieres estudiar dentro del **cuadrado central** y ajusta el tamaño de la región (ROI).
4. Ajusta la ventana de análisis (3–12 s), espera a que se recopilen muestras y observa el gráfico, los FPS y el estado de calidad.
5. Si aparece **«sin detección fiable»**, no interpretes el pico más alto como una frecuencia confirmada.

La luz ambiente, los movimientos, la exposición automática, el balance de blancos y los FPS variables pueden alterar las mediciones.

### 3. Exporta resultados

Usa **Exportar histórico a CSV**. El archivo contiene `t_segundos` y `frecuencia_dominante_hz` para las mediciones con pico detectado. Al iniciar una nueva captura o señal de prueba se limpia el histórico para no mezclar sesiones.

## Cómo interpretar las medidas

- **Hz:** ciclos de cambio de brillo por segundo; por ejemplo, 3 Hz son tres oscilaciones por segundo.
- **FPS:** número estimado de muestras de vídeo por segundo, calculado a partir de los timestamps.
- **Límite (Nyquist):** teóricamente FPS / 2; por prudencia el analizador busca picos solo hasta el 40 % de los FPS estimados. Una webcam de 30 FPS no puede medir de forma fiable un parpadeo de 50/60 Hz con este método.
- **Contraste espectral:** relación entre el pico y el fondo del espectro; no es un porcentaje de precisión ni una garantía de detección correcta.
- **Sin detección fiable:** falta duración, variación luminosa suficiente o un pico claramente destacado. Es preferible a mostrar una cifra engañosa.

La FFT se calcula sobre el brillo medio de la ROI, interpolando las muestras a intervalos uniformes y aplicando eliminación de tendencia y ventana de Hann. Este método es didáctico y no compensa todos los artefactos de la cámara.

## ¿Qué cámara se recomienda?

No necesitas una cámara de marca específica. Para empezar, **cualquier webcam USB compatible con UVC y OpenCV** que entregue vídeo estable suele servir. En Linux conviene comprobar que aparece como `/dev/video0` (o `/dev/video1`) y que funciona con otra aplicación de cámara.

- **Para aprender y detectar oscilaciones lentas (1–5 Hz):** una webcam integrada o USB que entregue **30 FPS reales** con iluminación adecuada es suficiente para experimentar.
- **Para mayor margen:** una webcam USB UVC con **720p a 60 FPS reales**, si el ordenador y el controlador admiten ese modo. Reducir resolución puede ayudar a sostener los FPS.
- **Preferible:** exposición, ganancia y enfoque configurables manualmente, y opción de desactivar exposición automática. Las correcciones automáticas de brillo introducen variaciones no deseadas.
- **No recomendado para mediciones serias:** depender únicamente de los FPS anunciados en la caja; revisa siempre los FPS que muestra la aplicación. Tampoco una webcam de 60 FPS permite medir directamente un parpadeo de 50/60 Hz con este algoritmo.

El índice de cámara selecciona el dispositivo, **no configura su resolución ni garantiza una tasa de FPS concreta**. El método mide cambios de luminosidad media, no la frecuencia de refresco real de una pantalla ni PWM de alta frecuencia. Para 50/60 Hz y superiores se requiere otro sensor o un sistema de adquisición adecuado.

## Pruebas automáticas

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -v
python -m compileall -q videofrecuencia
```

Las pruebas verifican detección de señales sintéticas, ausencia de detección en imágenes planas o con ruido débil, validación de datos y situaciones simuladas de desconexión de cámara. **No sustituyen la comprobación con una webcam real y tu sistema operativo.**

## Nuevas opciones de la interfaz

- **Dispositivo de cámara:** elige índice 0–9 antes de iniciar la captura.
- **Región central (%):** ajusta qué porcentaje del vídeo se usa para calcular el brillo medio.
- **Ventana (s):** una ventana larga mejora la resolución de frecuencia, pero tarda más en reaccionar a los cambios.
- **Reiniciar medición:** limpia el espectro y el histórico de la sesión actual.
- **Prueba sintética:** por defecto se limita el deslizador a 10 Hz; la interfaz avisa si el valor seleccionado supera el margen de muestreo real.

**Límite fundamental:** ninguna detección basada solo en FPS puede demostrar que una señal real no está aliasada; por eso los resultados siguen siendo experimentales.

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

## Licencia y créditos

Este proyecto se distribuye bajo la **licencia MIT**. Puedes utilizarlo, estudiarlo, modificarlo, redistribuirlo e incorporarlo a proyectos personales o comerciales, siempre que conserves el aviso de copyright y el texto de la licencia. Consulta [LICENSE](LICENSE).

**Autor y responsable del proyecto:** [Dirix24](https://github.com/Dirix24).

**Transparencia sobre inteligencia artificial:** parte del código, las correcciones, las pruebas, el diseño de la interfaz y la documentación se han desarrollado con asistencia de **ChatGPT, una inteligencia artificial de OpenAI**, a partir de indicaciones y revisiones del responsable del repositorio. La IA se ha utilizado como herramienta de desarrollo; esto no implica que todo el código original haya sido generado por IA ni que OpenAI avale el proyecto.

