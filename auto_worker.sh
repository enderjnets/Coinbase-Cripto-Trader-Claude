#!/bin/bash
# Auto-restart worker script
# Reinicia el crypto_worker automáticamente cuando falla

PROJECT_DIR="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
VENV_PATH="$HOME/coinbase_trader_venv"
LOG_FILE="/tmp/worker_output.log"
COORDINATOR_URL="http://localhost:5001"

echo "========================================"
echo "🔄 AUTO-WORKER MONITOR"
echo "========================================"
echo "Proyecto: $PROJECT_DIR"
echo "Coordinator: $COORDINATOR_URL"
echo ""

restart_count=0

while true; do
    # Limpiar procesos Ray residuales
    pkill -f raylet 2>/dev/null
    pkill -f "ray::" 2>/dev/null
    pkill -f gcs_server 2>/dev/null
    sleep 2

    restart_count=$((restart_count + 1))
    echo ""
    echo "========================================"
    echo "🚀 Iniciando worker (intento #$restart_count)"
    echo "   $(date)"
    echo "========================================"

    # Activar venv y ejecutar worker
    source "$VENV_PATH/bin/activate"
    cd "$PROJECT_DIR"

    COORDINATOR_URL="$COORDINATOR_URL" PYTHONUNBUFFERED=1 python -u crypto_worker.py 2>&1 | tee -a "$LOG_FILE"

    exit_code=$?
    echo ""
    echo "⚠️  Worker terminó con código: $exit_code"
    echo "⏳ Reiniciando en 5 segundos..."
    sleep 5
done
