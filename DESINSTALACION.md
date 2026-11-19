# Comandos para desinstalar VideoFrecuencia

Esta guía corresponde a instalaciones realizadas clonando el repositorio. **Guarda antes tus CSV y cambios locales**: borrar una carpeta es irreversible. El repositorio remoto de GitHub no se borra.

## Linux (MX Linux, Debian, Ubuntu)

Si tienes el archivo `uninstall.py` en tu copia (disponible en la rama `feat/desinstalador-multiplataforma`), cierra la aplicación y ejecuta desde su carpeta:

```bash
cd ~/videofrecuencia
.venv/bin/python uninstall.py
```

Cuando aparezca la pregunta, escribe `DESINSTALAR` y pulsa Enter. Esta opción solo funciona si el desinstalador está presente.

### Alternativa manual para una copia clonada

Primero **comprueba la ruta**:

```bash
ls -ld -- "$HOME/videofrecuencia"
```

Si es la carpeta correcta y has guardado tus datos, bórrala con:

```bash
rm -rI -- "$HOME/videofrecuencia"
```

`rm -rI` solicita confirmación general, no por cada archivo como `rm -ri`. No uses `sudo` para borrar una instalación dentro de tu carpeta personal.

### Verificar

```bash
if [ -d "$HOME/videofrecuencia" ]; then
    echo "Todavía existe la carpeta de VideoFrecuencia"
else
    echo "La carpeta de VideoFrecuencia se ha eliminado"
fi
```

Para localizar archivos adicionales **directamente** en tu carpeta personal:

```bash
find "$HOME" -maxdepth 1 -iname '*videofrecuencia*' -print
```

En una prueba real de MX Linux quedaron fuera de la instalación `~/videofrecuencia_historico.csv` y `~/videofrecuencia-respaldo-20261119-190150`. Tras comprobar que ya no se necesitaban, se borraron con estos comandos **específicos de esa prueba**:

```bash
rm -f -- "$HOME/videofrecuencia_historico.csv"
rm -rf -- "$HOME/videofrecuencia-respaldo-20261119-190150"
```

**Advertencia:** `rm -rf` borra sin preguntar. No copies estos comandos para otros archivos o nombres de respaldo sin verificar sus rutas. No se deben eliminar automáticamente los CSV guardados fuera del proyecto.

## Windows (PowerShell)

Cierra VideoFrecuencia y entra en la carpeta del repositorio. Si contiene `uninstall.py`, puedes ejecutar:

```powershell
cd "$HOME\videofrecuencia"
py uninstall.py
```

Confirma escribiendo `DESINSTALAR`. La implementación de Windows todavía requiere pruebas reales.

Para una copia clonada sin `uninstall.py`, revisa primero que `$HOME\videofrecuencia` sea la ruta correcta y guarda tus datos. Desde **otra carpeta**, ejecuta:

```powershell
cd $HOME
Remove-Item -LiteralPath "$HOME\videofrecuencia" -Recurse -Confirm
```

Comprueba:

```powershell
Test-Path -LiteralPath "$HOME\videofrecuencia"
```

`False` significa que esa ruta ya no existe.

## macOS (Terminal)

Cierra VideoFrecuencia. Si el repositorio incluye `uninstall.py`:

```bash
cd ~/videofrecuencia
python3 uninstall.py
```

Escribe `DESINSTALAR` cuando se solicite. Para una copia clonada sin ese archivo, guarda primero tus datos, revisa la ruta y utiliza:

```bash
ls -ld -- "$HOME/videofrecuencia"
rm -rI -- "$HOME/videofrecuencia"
```

En macOS, algunas versiones de `rm` no admiten `-I`. Si aparece un error de opción no válida, utiliza `rm -ri -- "$HOME/videofrecuencia"` (pide confirmación por archivo), o revisa cuidadosamente la ruta antes de ejecutar `rm -r -- "$HOME/videofrecuencia"`.

Comprueba con `test ! -e "$HOME/videofrecuencia" && echo "Eliminado"`.

## Alcance

Estos comandos eliminan **la copia local indicada**, no Python del sistema, el repositorio de GitHub ni los archivos exportados a otras ubicaciones. Tampoco eliminan accesos directos o instalaciones hechas por un empaquetador externo. La desinstalación manual se verificó en MX Linux; las instrucciones de Windows y macOS están documentadas, pero no se han probado aún en esos sistemas.
