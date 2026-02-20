#!/bin/bash
# Worker Air Daemon - Auto-restart on crash
# Mantiene el worker corriendo reiniciándolo si se cae

PROJECT_DIR="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
COORDINATOR_URL="http://100.118.215.73:5001"
LOG_FILE="$PROJECT_DIR/worker_air.log"
PID_FILE="$PROJECT_DIR/worker_air_daemon.pid"

echo "🔄 Worker Air Daemon iniciado"
echo "📁 Directorio: $PROJECT_DIR"
echo "📡 Coordinator: $COORDINATOR_URL"
echo "📋 Log: $LOG_FILE"
echo ""

# Guardar PID del daemon
echo $$ > "$PID_FILE"

# Limpiar Ray al inicio
pkill -9 -f "ray::" 2>/dev/null
rm -rf /tmp/ray* 2>/dev/null
find "$PROJECT_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

cd "$PROJECT_DIR"

RESTART_COUNT=0

while true; do
    RESTART_COUNT=$((RESTART_COUNT + 1))
    echo "=========================================="
    echo "🚀 Iniciando worker (intento #$RESTART_COUNT)"
    echo "⏰ $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="

    # Limpiar Ray antes de cada intento
    pkill -9 -f "ray::" 2>/dev/null
    sleep 2
    rm -rf /tmp/ray* 2>/dev/null

    # Iniciar worker
    COORDINATOR_URL="$COORDINATOR_URL" python3 -u crypto_worker.py "$COORDINATOR_URL" >> "$LOG_FILE" 2>&1

    EXIT_CODE=$?
    echo "⚠️  Worker terminó con código: $EXIT_CODE"
    echo "⏰ $(date '+%Y-%m-%d %H:%M:%S')"

    # Esperar 5 segundos antes de reiniciar
    echo "⏳ Esperando 5s antes de reiniciar..."
    sleep 5
done
