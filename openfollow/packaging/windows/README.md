# OpenFollow para Windows 11 x64

Esta adaptación conserva la ventana GTK, la superposición de vídeo y la interfaz
web del proyecto original. No se ha compilado ni probado todavía en Windows.
El entorno adjunto es Linux; los resultados de sus pruebas no verifican un `.exe`.

La ruta más sencilla para obtener el ejecutable es subir este código a un
repositorio propio y ejecutar **Actions → Build Windows → Run workflow**.
El flujo usa un equipo Windows de GitHub y entrega el ZIP, una captura de la
ventana real (`OpenFollow-running.png`) y la comprobación del paquete como
artefactos. Comprueba la página web y un fotograma JPEG desde el ejecutable
antes de empaquetar. El flujo está preparado, pero todavía no se ha ejecutado.

## Compilar en Windows

Requisitos: Windows 11 x64, Python 3.13 x64 con su lanzador `py`, Git,
Visual Studio 2022 con «Desarrollo para el escritorio con C++» y Windows SDK,
y MSYS2 en `C:\msys64`. En su terminal MSYS2 instala `patch` con
`pacman -S --needed patch`. Se requiere acceso a Internet para descargar
dependencias y compilar GTK 3 y GStreamer; la primera compilación puede tardar.

Desde PowerShell, en la raíz del código:

```powershell
& .\packaging\windows\Build-Windows.ps1
```

`-NativePrefix C:\ruta\gtk` reutiliza una instalación compilada con GTK 3,
GStreamer y las ruedas PyGObject/Pycairo para Python 3.13. `-Detection` incluye
las dependencias opcionales de inferencia; los modelos se añaden por separado.
El script conserva la comprobación TLS y los hashes de las descargas.

Si la compilación y la comprobación del paquete pasan, el resultado se escribe
en `%LOCALAPPDATA%\OpenFollow-build\dist\OpenFollow-Windows-x64.zip`.
Extrae la carpeta completa y abre `OpenFollow.exe`. Su carpeta `_internal`
debe permanecer junto al ejecutable. No requiere WSL.

La configuración y los archivos de la aplicación se guardan en
`%LOCALAPPDATA%\OpenFollow`, sin sobrescribir la configuración existente.
El primer arranque utiliza el patrón de prueba para poder comprobar la imagen.
«Open Web UI» abre el navegador de Windows; la interfaz web usa el puerto 8080.

## Validación pendiente

La comprobación del paquete revisa importaciones, plantillas y plugins básicos.
En Windows aún deben comprobarse la ventana, el vídeo real, los mandos, MIDI,
y PSN/OTP/OSC/RTTrPM con sus equipos receptores. La prueba de la aplicación
debe incluir una respuesta válida de la web y un fotograma JPEG real.

NDI necesita su SDK y un plugin GStreamer NDI compatibles, igual que el original.
La compilación incluye SRT y una entrada de cámara USB mediante GStreamer;
ambas están pendientes de validación en Windows. No instala un SDK NDI.
Las cámaras V4L2 y CSI, los servicios systemd y las actualizaciones `.deb`
corresponden a Linux. Sus funciones del sistema deben gestionarse desde Windows;
la equivalencia funcional requiere validar la aplicación con los equipos reales.

La licencia AGPL-3.0-or-later y los avisos originales acompañan al paquete.
Si se distribuye una compilación modificada, debe ofrecerse también su código
fuente completo correspondiente. Este archivo describe una preparación de
compilación, no un ejecutable entregado ni una compatibilidad ya certificada.
