# Contribuir a VideoFrecuencia

¡Las mejoras son bienvenidas! Este proyecto es abierto y está orientado a experimentar con el análisis de variaciones de brillo mediante webcam y FFT.

## Cómo colaborar

1. Abre un **issue** con el problema, la propuesta o una pregunta.
2. Crea un **fork** y una rama descriptiva (por ejemplo, `fix/camera-reconnect`).
3. Mantén los cambios pequeños y documenta el comportamiento esperado.
4. Añade pruebas cuando modifiques el análisis, la captura o la exportación.
5. Ejecuta `python -m pip install -r requirements-dev.txt`, `python -m pytest -v` y `python -m compileall -q videofrecuencia`.
6. Abre un **pull request** describiendo qué cambió, cómo se probó y qué hardware o sistema operativo utilizaste.

## Reglas de calidad

- No presentes una medición como fiable si la señal o el muestreo no la respaldan.
- No afirmes que una webcam de 30 FPS mide directamente oscilaciones de 50/60 Hz.
- No introduzcas telemetría, acceso a cámara oculto ni subida de imágenes sin consentimiento explícito.
- Mantén mensajes claros en español y documenta cualquier nueva dependencia.
- Para errores de cámara, indica sistema operativo, modelo (si procede), FPS aproximados y pasos para reproducir; no adjuntes imágenes privadas.

## Uso de IA

Se permite utilizar asistentes de IA para código, documentación y pruebas. **Declara en el pull request qué partes recibieron asistencia de IA**, revisa personalmente los cambios y comprueba su comportamiento. La responsabilidad de la contribución corresponde a quien la presenta.

## Licencia

Al contribuir aceptas que tus aportaciones se distribuyan bajo la [licencia MIT](LICENSE) del repositorio.
