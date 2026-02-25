================================================================
              BITTRADER WORKER v5.0 - Windows
================================================================

REQUISITOS:
- Windows 10/11
- Python 3.9+ (se instala automaticamente)
- 4GB RAM minimo
- Conexion a internet

INSTALACION:

1. Abre PowerShell como Administrador
2. Navega a esta carpeta
3. Ejecuta:
   Set-ExecutionPolicy Bypass -File install.ps1

4. O con CMD:
   INSTALL.bat

5. Para personalizar:
   .\install.ps1 -CoordinatorUrl http://TU-IP:5001 -NumWorkers 4

INICIAR WORKERS:
   cd %USERPROFILE%\crypto_worker
   .\start_workers.ps1

DETENER WORKERS:
   .\stop_workers.ps1

VER ESTADO:
   tasklist /FI "IMAGENAME eq python.exe"

VER LOGS:
   type worker_1.log

NOTAS:
- Compatible con Windows 10/11
- Numba JIT requiere Visual C++ Build Tools
- Cada worker usa ~500MB RAM
- Ajusta -NumWorkers segun tus CPUs

COORDINADOR:
- IP: 100.77.179.14:5001 (Tailscale)
- IP Local: 10.0.0.232:5001

================================================================
