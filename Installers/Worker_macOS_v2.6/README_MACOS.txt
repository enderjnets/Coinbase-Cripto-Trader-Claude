╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║         BITTRADER WORKER INSTALLER v2.6 - MACOS EDITION                  ║
║                                                                          ║
║         Professional Ray Worker for macOS                                ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ENGLISH GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OVERVIEW
--------
This installer configures your Mac as a Ray Worker node in the Bittrader
distributed computing cluster. Workers connect to the Head Node and contribute
computing power for high-performance backtesting and optimization.

SYSTEM REQUIREMENTS
-------------------
  • macOS 12 (Monterey) or higher
  • 4GB RAM minimum (8GB+ recommended)
  • 2+ CPU cores (4+ recommended)
  • Network connection to Head Node
  • Python 3.9.6 (auto-installed)

QUICK START
-----------
1. Make scripts executable:
   chmod +x install.sh verify_worker.sh uninstall.sh

2. Run installer:
   ./install.sh

3. Enter Head Node IP when prompted
   (Provided by cluster administrator)

4. Verify installation:
   ./verify_worker.sh

FEATURES
--------
  ✓ Automatic Python 3.9.6 installation
  ✓ Ray 2.51.2 with optimized configuration
  ✓ Smart CPU throttling (2 CPUs when in use, full when idle)
  ✓ Automatic reconnection on network changes
  ✓ Google Drive code synchronization support
  ✓ Tailscale VPN support for remote connection
  ✓ Auto-start on login
  ✓ Battery-aware processing (optional)

NETWORK MODES
-------------
  LAN MODE:
    • Connect directly to Head Node on same network
    • Use local IP (e.g., 192.168.1.x)
    • No VPN required

  TAILSCALE MODE:
    • Connect to Head Node remotely via VPN
    • Use Tailscale IP (e.g., 100.x.x.x)
    • Works from anywhere
    • Auth key included in installer (90-day validity)

SMART THROTTLING
----------------
The worker automatically adjusts CPU usage:
  • Active use: 2 CPUs (minimal impact)
  • Idle 5+ min: All CPUs (maximum performance)
  • Plugged in: Full performance
  • Battery: Reduced performance (optional)

INSTALLED COMPONENTS
--------------------
  ~/.bittrader_worker/          Installation directory
  ├── config.env                Configuration
  ├── venv/                     Python virtual environment
  ├── worker_daemon.sh          Worker daemon
  ├── smart_throttle.sh         CPU throttling monitor
  ├── status_indicator.sh       Status notifications
  ├── current_cpus              Current CPU allocation
  └── logs/
      ├── worker.log            Main log
      ├── throttle.log          Throttle monitor log
      └── status.log            Status notifications log

  ~/Library/LaunchAgents/
  ├── com.bittrader.worker.plist    Worker auto-start
  ├── com.bittrader.throttle.plist  Throttle monitor
  └── com.bittrader.status.plist    Status notifications

VERIFICATION
------------
Run verification script:
  ./verify_worker.sh

Checks:
  ✓ Python and Ray installation
  ✓ Configuration
  ✓ Network connectivity to Head Node
  ✓ Google Drive code synchronization
  ✓ Worker status and connection

TROUBLESHOOTING
---------------
Problem: Cannot connect to Head Node
Solution:
  • Verify Head Node is running
  • Check network: ping HEAD_IP
  • If using Tailscale: tailscale status
  • Check logs: tail -f ~/.bittrader_worker/worker.log

Problem: Python version mismatch
Solution:
  • Installer should install Python 3.9.6 automatically
  • If failed, download from python.org/downloads/release/python-396
  • Run installer again after manual Python installation

Problem: High CPU usage
Solution:
  • Normal during optimization tasks
  • Throttling should reduce CPU when Mac is in use
  • Check throttle status: cat ~/.bittrader_worker/current_cpus
  • Disable throttle if needed (see config.env)

Problem: Worker stops unexpectedly
Solution:
  • Check error log: ~/.bittrader_worker/worker.log
  • Restart: launchctl start com.bittrader.worker
  • Verify auto-start: launchctl list | grep bittrader

UNINSTALLATION
--------------
To remove the worker:
  ./uninstall.sh

This removes:
  • Installation directory
  • Auto-start services
  • Desktop shortcuts

Python and system packages are NOT removed.

LOGS
----
  Main log:     ~/.bittrader_worker/worker.log
  Throttle log: ~/.bittrader_worker/throttle.log
  Status log:   ~/.bittrader_worker/status.log

  Monitor live: tail -f ~/.bittrader_worker/worker.log

SUPPORT
-------
  • Troubleshooting Guide: TROUBLESHOOTING.txt
  • Complete Guide: Documentation/COMPLETE_CLUSTER_GUIDE.md
  • Contact cluster administrator for support

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GUÍA EN ESPAÑOL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESUMEN
-------
Este instalador configura tu Mac como Worker (trabajador) en el cluster
distribuido de Bittrader. Los Workers se conectan al Head Node y contribuyen
poder de procesamiento para backtesting y optimización de alto rendimiento.

REQUISITOS DEL SISTEMA
-----------------------
  • macOS 12 (Monterey) o superior
  • 4GB RAM mínimo (8GB+ recomendado)
  • 2+ núcleos CPU (4+ recomendado)
  • Conexión de red al Head Node
  • Python 3.9.6 (instalación automática)

INICIO RÁPIDO
-------------
1. Hacer scripts ejecutables:
   chmod +x install.sh verify_worker.sh uninstall.sh

2. Ejecutar instalador:
   ./install.sh

3. Ingresar IP del Head Node cuando se solicite
   (Proporcionada por el administrador del cluster)

4. Verificar instalación:
   ./verify_worker.sh

CARACTERÍSTICAS
---------------
  ✓ Instalación automática de Python 3.9.6
  ✓ Ray 2.51.2 con configuración optimizada
  ✓ Throttling inteligente de CPU (2 CPUs en uso, completo en idle)
  ✓ Reconexión automática al cambiar de red
  ✓ Soporte para sincronización de código vía Google Drive
  ✓ Soporte Tailscale VPN para conexión remota
  ✓ Inicio automático al iniciar sesión
  ✓ Procesamiento consciente de batería (opcional)

MODOS DE RED
------------
  MODO LAN:
    • Conectar directamente al Head Node en misma red
    • Usar IP local (ej: 192.168.1.x)
    • No requiere VPN

  MODO TAILSCALE:
    • Conectar al Head Node remotamente vía VPN
    • Usar IP Tailscale (ej: 100.x.x.x)
    • Funciona desde cualquier lugar
    • Auth key incluida en instalador (validez 90 días)

THROTTLING INTELIGENTE
----------------------
El worker ajusta automáticamente el uso de CPU:
  • Uso activo: 2 CPUs (impacto mínimo)
  • Idle 5+ min: Todas las CPUs (máximo rendimiento)
  • Conectado: Rendimiento completo
  • Batería: Rendimiento reducido (opcional)

COMPONENTES INSTALADOS
-----------------------
  ~/.bittrader_worker/          Directorio de instalación
  ├── config.env                Configuración
  ├── venv/                     Entorno virtual Python
  ├── worker_daemon.sh          Daemon del worker
  ├── smart_throttle.sh         Monitor de throttling
  ├── status_indicator.sh       Notificaciones de estado
  ├── current_cpus              Asignación actual de CPU
  └── logs/
      ├── worker.log            Log principal
      ├── throttle.log          Log de throttle
      └── status.log            Log de notificaciones

  ~/Library/LaunchAgents/
  ├── com.bittrader.worker.plist    Auto-inicio worker
  ├── com.bittrader.throttle.plist  Monitor throttle
  └── com.bittrader.status.plist    Notificaciones

VERIFICACIÓN
------------
Ejecutar script de verificación:
  ./verify_worker.sh

Verifica:
  ✓ Instalación de Python y Ray
  ✓ Configuración
  ✓ Conectividad de red al Head Node
  ✓ Sincronización de código Google Drive
  ✓ Estado y conexión del worker

SOLUCIÓN DE PROBLEMAS
----------------------
Problema: No puede conectar al Head Node
Solución:
  • Verificar que Head Node esté corriendo
  • Verificar red: ping HEAD_IP
  • Si usa Tailscale: tailscale status
  • Verificar logs: tail -f ~/.bittrader_worker/worker.log

Problema: Versión de Python no coincide
Solución:
  • El instalador debe instalar Python 3.9.6 automáticamente
  • Si falla, descargar de python.org/downloads/release/python-396
  • Ejecutar instalador nuevamente después de instalación manual

Problema: Alto uso de CPU
Solución:
  • Normal durante tareas de optimización
  • Throttling debe reducir CPU cuando Mac está en uso
  • Verificar estado throttle: cat ~/.bittrader_worker/current_cpus
  • Deshabilitar throttle si es necesario (ver config.env)

Problema: Worker se detiene inesperadamente
Solución:
  • Verificar log de errores: ~/.bittrader_worker/worker.log
  • Reiniciar: launchctl start com.bittrader.worker
  • Verificar auto-inicio: launchctl list | grep bittrader

DESINSTALACIÓN
--------------
Para eliminar el worker:
  ./uninstall.sh

Esto elimina:
  • Directorio de instalación
  • Servicios de auto-inicio
  • Accesos directos del escritorio

Python y paquetes del sistema NO se eliminan.

LOGS
----
  Log principal: ~/.bittrader_worker/worker.log
  Log throttle:  ~/.bittrader_worker/throttle.log
  Log status:    ~/.bittrader_worker/status.log

  Monitorear en vivo: tail -f ~/.bittrader_worker/worker.log

SOPORTE
-------
  • Guía de Solución de Problemas: TROUBLESHOOTING.txt
  • Guía Completa: Documentation/GUIA_COMPLETA_CLUSTER_DISTRIBUIDO.md
  • Contactar administrador del cluster para soporte

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Version: 2.6
Release Date: January 2026
Tested with: Ray 2.51.2, Python 3.9.6, macOS Sequoia 15.2.1

Thank you for contributing to the Bittrader cluster!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
