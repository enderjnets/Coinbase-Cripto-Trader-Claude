#!/bin/bash
# Multi-Worker Launcher con Auto-Restart
# Lanza múltiples instancias de worker y las reinicia si mueren

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PATH="$HOME/coinbase_trader_venv"
NUM_WORKERS=${1:-3}
COORDINATOR_URL=${COORDINATOR_URL:-"http://localhost:5001"}
CHECK_INTERVAL=60  # Verificar cada 60 segundos

echo "========================================"
echo "🚀 MULTI-WORKER LAUNCHER (Auto-Restart)"
echo "========================================"
echo "📁 Directorio: $SCRIPT_DIR"
echo "🔢 Workers: $NUM_WORKERS"
echo "📡 Coordinator: $COORDINATOR_URL"
echo "🔄 Auto-restart: cada ${CHECK_INTERVAL}s"
echo ""

# Activar venv
source "$VENV_PATH/bin/activate"

# Matar workers existentes
pkill -f "python.*crypto_worker" 2>/dev/null
sleep 2

# Función para lanzar un worker
launch_worker() {
    local i=$1
    local LOG_FILE="/tmp/worker_${i}.log"
    echo "[$(date '+%H:%M:%S')] 🔄 Iniciando Worker $i → $LOG_FILE"

    cd "$SCRIPT_DIR"
    COORDINATOR_URL="$COORDINATOR_URL" \
    NUM_WORKERS="$NUM_WORKERS" \
    WORKER_INSTANCE="$i" \
    USE_RAY="false" \
    PYTHONUNBUFFERED=1 nohup python -u crypto_worker.py > "$LOG_FILE" 2>&1 &
}

# Lanzar todos los workers
for i in $(seq 1 $NUM_WORKERS); do
    launch_worker $i
    sleep 2
done

echo ""
echo "✅ $NUM_WORKERS workers iniciados"
echo "🛡️  Monitor de auto-restart activo..."
echo "🛑 Detener: pkill -f multi_worker"
echo ""

# Loop de monitoreo - reiniciar workers que mueran
while true; do
    sleep $CHECK_INTERVAL

    for i in $(seq 1 $NUM_WORKERS); do
        # Verificar si el worker sigue vivo buscando su PID
        if ! pgrep -f "WORKER_INSTANCE=$i.*crypto_worker" > /dev/null 2>&1; then
            echo "[$(date '+%H:%M:%S')] ⚠️  Worker $i muerto - reiniciando..."
            launch_worker $i
            sleep 2
        fi
    done
done
