#!/bin/bash
# Bittrader SSH Tunnel Daemon
# Mantiene el SSH tunnel activo hacia el Head Node

set -e

WORKER_DIR="$HOME/.bittrader_worker"
CONFIG_FILE="$WORKER_DIR/config.env"
LOG_FILE="$WORKER_DIR/logs/ssh_tunnel.log"

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
log "SSH Tunnel Daemon iniciando"
log "Head: $HEAD_IP:$HEAD_PORT"
log "=========================================="

# Loop infinito con reconexión automática
while true; do
    log "🔐 Intentando establecer SSH tunnel..."

    # Verificar conectividad antes de intentar SSH
    if ping -c 1 -W 2 "$HEAD_IP" &> /dev/null; then
        log "✅ Head accesible via ping"

        # Iniciar SSH tunnel
        # -N: No ejecutar comando remoto
        # -L: Port forwarding (local 6379 -> remote localhost:6379)
        # -o ServerAliveInterval=60: Mantener conexión viva
        # -o ServerAliveCountMax=3: Reintentar 3 veces
        # -o ExitOnForwardFailure=yes: Salir si el forwarding falla
        # -o StrictHostKeyChecking=no: No preguntar por host key
        ssh -N \
            -L 6379:localhost:6379 \
            -o ServerAliveInterval=60 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            "enderj@$HEAD_IP" &> "$WORKER_DIR/logs/ssh_tunnel_verbose.log"

        EXIT_CODE=$?
        log "⚠️  SSH tunnel desconectado (exit code: $EXIT_CODE)"
    else
        log "❌ No se puede alcanzar el Head ($HEAD_IP)"
    fi

    # Esperar antes de reintentar
    log "⏳ Reintentando en 10 segundos..."
    sleep 10
done
