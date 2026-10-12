# OpenFollow en la pantalla de inicio del iPhone

Esta app web permite ver y controlar OpenFollow mientras funciona en el PC.
La interfaz y los controles son los de OpenFollow; el procesamiento del vídeo
y el envío de datos se realizan en Windows.

1. Extrae `OpenFollow-Windows-iPhone.zip` completo en el PC y abre
   `OpenFollow\OpenFollow.exe`.
2. Conecta el iPhone y el PC a la misma red. El PC puede estar por cable
   Ethernet y el iPhone por Wi-Fi del mismo router.
3. Abre Safari en el iPhone y escribe `http://IP_DEL_PC:8080`, sustituyendo
   `IP_DEL_PC` por la IPv4 de tu PC. Puedes verla en Windows en Configuración,
   Red e Internet, Propiedades. Si OpenFollow muestra otro puerto, usa ese.
4. En Safari pulsa Compartir, «Añadir a pantalla de inicio» y «Añadir».
   Activa «Abrir como app web» si Safari ofrece esa opción.
5. Abre el icono OpenFollow para acceder a los controles de la aplicación.

El PC debe permanecer encendido con OpenFollow abierto. Esta conexión local
no requiere Internet ni App Store. Si Windows pide acceso a la red, permite
OpenFollow en la red privada que uses para conectar ambos dispositivos.

La app web necesita la conexión al PC; no guarda una copia desconectada de
los controles. Si cambia la dirección del PC, abre la dirección nueva en
Safari y vuelve a añadirla a la pantalla de inicio.

El paquete reutiliza el ejecutable nativo de Windows ya compilado y actualiza
sus recursos web. No se han ejecutado pruebas de funcionamiento en Windows
11 ni en un iPhone, por petición del usuario.
