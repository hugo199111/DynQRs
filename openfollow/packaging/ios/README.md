# OpenFollow nativo para iPhone

App iOS nativa en SwiftUI que se conecta al OpenFollow del PC mediante su API.
Tiene pantallas propias de conexión, estado, vídeo, selección de marcadores y
ajustes. El procesamiento del vídeo, el seguimiento y las salidas se realizan
en el PC. Requiere iOS 17 o posterior.

## Instalar desde Windows sin Apple Developer de pago

El archivo `OpenFollow-iPhone.ipa` contiene la aplicación compilada para un
iPhone real. Se entrega sin firma: no se instala directamente al tocarlo.
AltStore Classic y AltServer lo firman con tu cuenta gratuita de Apple.

1. Descarga AltServer para Windows desde el sitio oficial de
   [AltStore](https://altstore.io/) y sigue sus instrucciones para Windows,
   incluidas las dependencias de Apple que indique la versión actual.
2. Conecta el iPhone al PC por USB, acepta «Confiar en este ordenador» y usa
   AltServer para instalar AltStore Classic en el iPhone.
3. Introduce tu cuenta de Apple en AltServer/AltStore cuando lo solicite.
   No compartas tu contraseña, certificados ni códigos en este repositorio.
4. En el iPhone habilita Modo de desarrollador si iOS lo solicita. Guarda
   `OpenFollow-iPhone.ipa` en Archivos y ábrelo desde AltStore Classic para
   firmarlo e instalarlo.
5. Las instalaciones con cuenta gratuita caducan a los siete días. Renueva
   la app con AltStore y AltServer siguiendo las instrucciones oficiales.

La cuenta gratuita tiene límites de aplicaciones activas y de identificadores.
TestFlight y distribución mediante App Store requieren Apple Developer de pago.

## Conectar por Internet

1. Instala [Tailscale en Windows](https://tailscale.com/download/windows) y
   [Tailscale en el iPhone](https://tailscale.com/download/ios).
2. Inicia sesión en ambos con la misma cuenta y activa su conexión privada.
   Usa una política de acceso que permita al iPhone llegar al PC en el puerto
   web de OpenFollow. No hace falta abrir puertos del router.
3. Abre OpenFollow en Windows. El PC debe mantenerse encendido y conectado
   a Internet cuando quieras usarlo desde fuera de la red local.
4. En la app del iPhone pulsa «Conectar al PC» y escribe
   `http://IP_TAILSCALE_DEL_PC:8080`. Sustituye el marcador por la IPv4 que
   Tailscale muestra para el PC, y usa el puerto real de OpenFollow si es otro.
5. Introduce el PIN de OpenFollow si lo configuraste en el PC y pulsa Conectar.

Tailscale cifra el tráfico entre los dispositivos. La app no necesita un
servidor de escritorio remoto: solicita datos y envía cambios a la API del PC.
La red privada requiere Tailscale activo en los dos dispositivos y depende de
su servicio para establecer la conexión; consulta sus condiciones actuales.
En la misma LAN también puedes usar directamente la IPv4 privada del PC.

La app acepta HTTP solo para IPv4 privada o del rango de Tailscale. Acepta
HTTPS con la validación de certificados del sistema para otros destinos.
No usa HTTP público, no desactiva TLS y no sigue redirecciones HTTP.
Los PIN se guardan en el llavero local del iPhone, no en archivos de preferencias.

## Pantallas y alcance

- Inicio: conexión, versión, estado del vídeo, seguimiento, mandos y CPU.
- Vídeo: fotogramas JPEG de la API de OpenFollow, actualizados aproximadamente
  una vez por segundo; no es una transmisión de vídeo a velocidad completa.
- Marcadores: selección de los marcadores que controla y muestra este PC.
- Ajustes: formularios nativos de las secciones admitidas por la API.
  Guarda solo los campos modificados y vuelve a leer lo que conservó el PC.

Los campos de interfaz de red que la API considera locales se configuran
desde Windows. Las pantallas no replican todas las herramientas del navegador,
como la galería de medios o el asistente gráfico completo de calibración.
No se añade un joystick ni se cambia el comportamiento de los protocolos del PC.

## Compilar

El flujo «Build native iPhone app» de GitHub Actions usa macOS y el SDK oficial
de iOS para generar una IPA de dispositivo sin firma. No ejecuta la aplicación,
pruebas ni simuladores, por petición del usuario.

En un Mac con Xcode:

```sh
python3 packaging/ios/generate_project.py
open packaging/ios/OpenFollowMobile.xcodeproj
```

El proyecto no tiene dependencias externas. Para una instalación con Xcode
selecciona tu equipo de desarrollo y el iPhone de destino; para TestFlight
necesitas una cuenta Apple Developer de pago y su firma.

La licencia es AGPL-3.0-or-later. El código fuente correspondiente se entrega
en un artefacto aparte y está en la rama `openfollow-windows` de
`hugo199111/DynQRs`, dentro de `openfollow/packaging/ios`.
La app no se ha ejecutado en un iPhone ni se ha probado su conexión real,
por petición del usuario. La compilación por sí sola no verifica la instalación.
