================================================================
              BITTRADER WORKER v5.0 - Linux
================================================================

REQUISITOS:
- Python 3.9+
- 4GB RAM minimo
- Conexion a internet

INSTALACION:

1. Descomprime este archivo
2. Abre terminal en la carpeta
3. Ejecuta:
   chmod +x install.sh
   ./install.sh

4. Para personalizar:
   COORDINATOR_URL=http://TU-IP:5001 NUM_WORKERS=5 ./install.sh

INICIAR WORKERS:
   cd ~/crypto_worker && ./start_workers.sh

DETENER WORKERS:
   cd ~/crypto_worker && ./stop_workers.sh

VER ESTADO:
   cd ~/crypto_worker && ./status.sh

VER LOGS:
   tail -f /tmp/worker_1.log

NOTAS:
- Numba JIT acelera backtests ~4000x
- Cada worker usa ~500MB RAM
- Ajusta NUM_WORKERS segun tus CPUs

COORDINADOR:
- IP: 100.77.179.14:5001 (Tailscale)
- IP Local: 10.0.0.232:5001

================================================================
