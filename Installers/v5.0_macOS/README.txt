================================================================
              BITTRADER WORKER v5.0 - macOS
================================================================

REQUISITOS:
- macOS 11+ (Big Sur o superior)
- Python 3.9+ (se instala automaticamente)
- Xcode Command Line Tools
- 4GB RAM minimo

INSTALACION:

1. Abre Terminal
2. Navega a esta carpeta:
   cd "/path/to/esta/carpeta"

3. Ejecuta:
   chmod +x install.sh
   ./install.sh

4. Para personalizar:
   COORDINATOR_URL=http://TU-IP:5001 NUM_WORKERS=4 ./install.sh

INICIAR WORKERS:
   cd ~/crypto_worker && ./start_workers.sh

DETENER WORKERS:
   cd ~/crypto_worker && ./stop_workers.sh

VER ESTADO:
   cd ~/crypto_worker && ./status.sh

VER LOGS:
   tail -f /tmp/worker_1.log

NOTAS:
- Compatible con Apple Silicon (M1/M2/M3) e Intel
- Numba JIT acelera backtests ~4000x
- Cada worker usa ~400MB RAM en M-series
- Ajusta NUM_WORKERS segun tus CPUs (tipico: 4)

COORDINADOR:
- IP: 100.77.179.14:5001 (Tailscale)
- IP Local: 10.0.0.232:5001

================================================================
