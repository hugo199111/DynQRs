# OpenFollow para Windows 11 x64

El paquete contiene el ejecutable nativo `OpenFollow.exe`, GTK 3, GStreamer
y las dependencias de la aplicación. Conserva la ventana y la interfaz web
de OpenFollow. No necesita Python instalado ni WSL.

## Abrir el programa

Extrae el ZIP completo y abre `OpenFollow\OpenFollow.exe`. La carpeta
`_internal` debe permanecer junto al ejecutable.

La configuración se guarda en `%LOCALAPPDATA%\OpenFollow`, sin sobrescribir
la configuración existente. El primer arranque utiliza el patrón de vídeo
de prueba. «Open Web UI» abre la interfaz web en el navegador del PC.

## Ver y controlar desde un iPhone

1. Abre OpenFollow en el PC y conecta el iPhone a la misma red. El PC puede
   usar Ethernet y el iPhone Wi-Fi del mismo router.
2. En Safari, abre la dirección de red del PC con el puerto de la interfaz
   web. El puerto inicial es 8080: `http://IP_DEL_PC:8080`. Sustituye
   `IP_DEL_PC` por la dirección IPv4 del PC y usa el puerto que muestre
   OpenFollow si es diferente. La dirección local del navegador del PC no
   sirve en el teléfono.
3. Pulsa Compartir, «Añadir a pantalla de inicio» y «Añadir». Si aparece
   «Abrir como app web», actívalo. El nombre del icono es OpenFollow.
4. Abre ese icono para acceder a la interfaz y los controles del PC.

El PC debe permanecer encendido con OpenFollow abierto. No se necesita
Internet ni una cuenta de desarrollador de Apple para esta conexión local.
Si Windows solicita acceso a la red, permite OpenFollow en la red privada
que uses para conectar ambos dispositivos.

## Compilar en Windows

GitHub Actions, en «Build Windows», compila el ejecutable y publica
`OpenFollow-Windows-x64.zip` junto con el código fuente correspondiente.
El flujo usa `-SkipRuntimeChecks`, por petición del usuario: no ejecuta
la aplicación ni genera capturas o informes de funcionamiento.

Para compilar localmente se necesitan Windows x64, Python 3.13 x64, Git,
Visual Studio 2022 con desarrollo de escritorio C++ y Windows SDK, y MSYS2
en `C:\msys64` con el paquete `patch`. Desde la raíz de este código:

```powershell
& .\packaging\windows\Build-Windows.ps1 -SkipRuntimeChecks
```

El resultado se guarda en
`%LOCALAPPDATA%\OpenFollow-build\dist\OpenFollow-Windows-x64.zip`.
Las descargas de dependencias conservan la verificación TLS y de hashes.

El flujo «Package Windows for iPhone» reutiliza un ejecutable nativo ya
compilado y añade las plantillas, los iconos y los recursos web actuales.
Solo permite reutilizarlo si no han cambiado las fuentes del programa,
las dependencias ni los scripts de compilación nativa.

## Alcance de la entrega

La compilación nativa se completó en Windows de GitHub Actions. No se han
ejecutado pruebas de funcionamiento en Windows 11 ni en un iPhone, por
petición del usuario. El vídeo real, los mandos, MIDI y los receptores
PSN/OTP/OSC/RTTrPM necesitan sus respectivos equipos y configuración.

La compilación incluye SRT y entrada de cámara USB mediante GStreamer.
NDI requiere su SDK y un plugin GStreamer NDI compatibles, por separado.
V4L2, CSI, systemd y las actualizaciones `.deb` son funciones de Linux.

La licencia AGPL-3.0-or-later y los avisos originales acompañan al paquete.
La distribución modificada incluye también su código fuente correspondiente.
