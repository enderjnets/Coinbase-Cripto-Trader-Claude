================================================================================
BITTRADER WORKER INSTALLER v3.0 - SSH TUNNEL EDITION
Universal Worker - Funciona desde CUALQUIER ubicación
================================================================================

DESCRIPCIÓN
-----------
Este instalador configura un Worker Ray que se conecta al Head Node (MacBook Pro)
desde CUALQUIER ubicación usando SSH tunnel sobre Tailscale VPN.

El Worker puede instalarse en:
- ✅ MacBook Air (en casa o viajando)
- ✅ Cualquier Mac en cualquier ubicación
- ✅ Cualquier PC Linux
- ✅ Servidores cloud (AWS, GCP, Azure, DigitalOcean, etc.)

REQUISITOS PREVIOS
------------------
1. Python 3.9.6 instalado en esta máquina
   Descargar: https://www.python.org/ftp/python/3.9.6/

2. Tailscale instalado y conectado
   Descargar: https://tailscale.com/download

3. Acceso SSH al Head Node (MacBook Pro)
   IP Tailscale del Head: 100.77.179.14

INSTALACIÓN
-----------

PASO 1: Instalar Python 3.9.6 (si no lo tienes)
   - Descarga e instala desde el link arriba

PASO 2: Instalar y conectar Tailscale
   - Descarga e instala Tailscale
   - Inicia sesión en Tailscale
   - Verifica que estés conectado: tailscale status

PASO 3: Configurar autenticación SSH sin contraseña

   En esta máquina Worker, ejecuta:

   a) Generar clave SSH (si no tienes):
      ssh-keygen -t ed25519 -C "bittrader-worker"
      (Presiona Enter en todas las preguntas)

   b) Copiar clave al Head:
      ssh-copy-id enderj@100.77.179.14
      (Te pedirá la contraseña del Head una sola vez)

   c) Verificar conexión:
      ssh enderj@100.77.179.14 "echo OK"
      (Debe mostrar "OK" sin pedir contraseña)

PASO 4: Ejecutar instalador
   ./install.sh

PASO 5: Instalar daemons
   ./install_daemons.sh

¡LISTO! El Worker se conectará automáticamente al Head.

VERIFICACIÓN
------------
Para verificar que todo funciona:

1. Ver log del SSH tunnel:
   tail -f ~/.bittrader_worker/logs/ssh_tunnel.log

   Debe mostrar: "✅ SSH tunnel activo"

2. Ver log del Worker:
   tail -f ~/.bittrader_worker/logs/worker.log

   Debe mostrar: "✅ Worker conectado exitosamente"

3. En el Head (MacBook Pro), verificar cluster:
   ray status

   Debe mostrar 2 nodes con total de CPUs sumados

CONTROL DE DAEMONS
------------------

Detener Worker:
   launchctl unload ~/Library/LaunchAgents/com.bittrader.worker.plist
   launchctl unload ~/Library/LaunchAgents/com.bittrader.ssh_tunnel.plist

Reiniciar Worker:
   launchctl load ~/Library/LaunchAgents/com.bittrader.ssh_tunnel.plist
   launchctl load ~/Library/LaunchAgents/com.bittrader.worker.plist

Ver estado de daemons:
   launchctl list | grep bittrader

AJUSTAR CPUs
------------
Para cambiar el número de CPUs del Worker:

1. Editar archivo:
   echo "8" > ~/.bittrader_worker/current_cpus
   (Cambia 8 por el número de CPUs que quieras)

2. Reiniciar Worker:
   launchctl unload ~/Library/LaunchAgents/com.bittrader.worker.plist
   launchctl load ~/Library/LaunchAgents/com.bittrader.worker.plist

DESINSTALACIÓN
--------------
Para desinstalar completamente:

1. Detener daemons:
   launchctl unload ~/Library/LaunchAgents/com.bittrader.worker.plist
   launchctl unload ~/Library/LaunchAgents/com.bittrader.ssh_tunnel.plist

2. Eliminar archivos:
   rm ~/Library/LaunchAgents/com.bittrader.worker.plist
   rm ~/Library/LaunchAgents/com.bittrader.ssh_tunnel.plist
   rm -rf ~/.bittrader_worker

TROUBLESHOOTING
---------------

Problema: "SSH tunnel desconectado constantemente"
Solución:
   - Verifica que Tailscale esté conectado: tailscale status
   - Verifica que el Head esté accesible: ping 100.77.179.14
   - Verifica autenticación SSH: ssh enderj@100.77.179.14

Problema: "Worker no se conecta"
Solución:
   - Verifica que el SSH tunnel esté activo:
     tail -f ~/.bittrader_worker/logs/ssh_tunnel.log
   - Verifica que el puerto esté forwardeado:
     netstat -an | grep 6379

Problema: "Head no muestra el Worker"
Solución:
   - En el Head, verificar Ray: ray status
   - Ver logs del Head: tail -f ~/.bittrader_head/head.log
   - Reiniciar Head: launchctl unload/load com.bittrader.head.plist

ARQUITECTURA
------------
Head Node (MacBook Pro - en casa):
   - Ray 2.10.0 en localhost:6379
   - 12 CPUs
   - Siempre accesible via Tailscale: 100.77.179.14

Worker Node (esta máquina):
   - Ray 2.10.0
   - SSH tunnel: 100.77.179.14:6379 → localhost:6379
   - Se conecta a 127.0.0.1:6379 (a través del tunnel)
   - Funciona desde CUALQUIER ubicación con internet

SOPORTE
-------
Para reportar problemas o sugerencias:
Email: enderjnets@gmail.com

Versión: 3.0
Fecha: 27 de Enero 2026
