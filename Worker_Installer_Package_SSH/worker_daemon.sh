#!/bin/bash
# Bittrader Worker Daemon
# Conecta el Worker Ray al Head via SSH tunnel (localhost:6379)

set -e

WORKER_DIR="$HOME/.bittrader_worker"
CONFIG_FILE="$WORKER_DIR/config.env"
VENV_PATH="$WORKER_DIR/venv"
LOG_FILE="$WORKER_DIR/logs/worker.log"

# Cargar configuración
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "Error: No se encontró $CONFIG_FILE"
    exit 1
fi

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "Worker Daemon iniciando"
log "Modo: SSH Tunnel"
log "=========================================="

# Activar entorno virtual
source "$VENV_PATH/bin/activate"

# Loop infinito con reconexión automática
while true; do
    # Esperar a que el SSH tunnel esté activo
    log "🔍 Esperando SSH tunnel..."
    while ! nc -z localhost 6379 2>/dev/null; do
        sleep 5
    done
    log "✅ SSH tunnel activo"

    # Leer número de CPUs dinámicamente
    if [ -f "$WORKER_DIR/current_cpus" ]; then
        NUM_CPUS=$(cat "$WORKER_DIR/current_cpus")
    else
        NUM_CPUS=$(sysctl -n hw.ncpu)
    fi

    log "🚀 Conectando Worker Ray con $NUM_CPUS CPUs..."

    # Conectar Worker a través del SSH tunnel (localhost:6379)
    ray start \
        --address=127.0.0.1:6379 \
        --num-cpus="$NUM_CPUS" \
        &>> "$LOG_FILE"

    if [ $? -eq 0 ]; then
        log "✅ Worker conectado exitosamente"

        # Monitorear conexión
        while ray status --address=127.0.0.1:6379 &>/dev/null; do
            sleep 30
        done

        log "⚠️  Conexión perdida con el Head"
        ray stop &>/dev/null || true
    else
        log "❌ Error al conectar Worker"
    fi

    # Esperar antes de reintentar
    log "⏳ Reintentando en 15 segundos..."
    sleep 15
done
