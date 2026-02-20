#!/bin/bash
#
# 🔄 Bittrader Worker Daemon
# Automatically connects and reconnects to the Ray cluster
#

INSTALL_DIR="$HOME/.bittrader_worker"
LOG_FILE="$INSTALL_DIR/worker.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Load config
if [ ! -f "$INSTALL_DIR/config.env" ]; then
    log "❌ Error: config.env no encontrado."
    exit 1
fi
source "$INSTALL_DIR/config.env"

log "🚀 Worker Daemon iniciado"
log "   Head Node: $HEAD_IP"

# Enable cluster mode
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1

# Activate Virtual Environment
if [ -f "$INSTALL_DIR/venv/bin/activate" ]; then
    source "$INSTALL_DIR/venv/bin/activate"
    log "✅ Entorno virtual activado"
else
    log "⚠️ Entorno virtual no encontrado. Usando sistema..."
fi

# Helper to find Tailscale
find_tailscale() {
    if command -v tailscale &> /dev/null; then
        echo "tailscale"
    elif [ -f "/Applications/Tailscale.app/Contents/MacOS/Tailscale" ]; then
        echo "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
    elif [ -f "/opt/homebrew/bin/tailscale" ]; then
        echo "/opt/homebrew/bin/tailscale"
    else
        echo ""
    fi
}

# Connection loop
while true; do
    # 1. Check connectivity to HEAD
    CONNECTED_TO_HEAD=false
    if ping -c 1 -W 2 "$HEAD_IP" &> /dev/null; then
        CONNECTED_TO_HEAD=true
    fi

    # 2. If not connected, diagnose Tailscale
    if [ "$CONNECTED_TO_HEAD" = false ]; then
        log "⚠️ No puedo contactar al Head ($HEAD_IP)."
        
        TS_CMD=$(find_tailscale)
        if [ -n "$TS_CMD" ]; then
            # Verify status and log output if failed
            TS_STATUS=$("$TS_CMD" status 2>&1)
            if [ $? -eq 0 ]; then
                log "ℹ️ Tailscale conectado ($TS_STATUS), pero ping falló."
            else
                log "⚠️ Tailscale error: $TS_STATUS"
                log "   Intentando levantar..."
                "$TS_CMD" up --accept-routes 2>&1 >/dev/null &
            fi
        else
            log "⚠️ Tailscale no encontrado en rutas estándar."
        fi
        
        sleep 30
        continue
    fi
     
    # Check if Ray is already running and connected
    if pgrep -x "raylet" > /dev/null; then
        # Ray is running, check if it's healthy
        if python3 -c "import ray; ray.init(address='auto', ignore_reinit_error=True); print(ray.cluster_resources())" &> /dev/null; then
            # All good, just wait
            sleep 60
            continue
        else
            log "⚠️ Ray corriendo pero sin conexión. Reiniciando..."
            ray stop 2>/dev/null || true
            sleep 2
        fi
    fi
    
    # 4. Try to connect
    log "🔗 Conectando a $HEAD_IP:6379..."
    
    # [FIX] Smart Directory Management
    # If Google Drive is synced, we use it to avoid downloading the code via Ray.
    # Otherwise, we use Universal Mode (Ray manages the environment).
    
    PROJECT_DIR=$(find "$HOME/Library/CloudStorage" -type d -name "Coinbase Cripto Trader Antigravity" -print -quit 2>/dev/null)
    
    if [ -n "$PROJECT_DIR" ]; then
        log "📂 Modo Drive Detectado: $PROJECT_DIR"
        cd "$PROJECT_DIR" || log "⚠️ No pude entrar al directorio."
        export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
    else
        log "🌍 Modo Universal (Sin Drive). Código sincronizado por Ray."
        cd "$HOME"
    fi
    
    # Get CPU count from throttle config if exists

    if [ -f "$INSTALL_DIR/current_cpus" ]; then
        CPUS=$(cat "$INSTALL_DIR/current_cpus")
    else
        CPUS=$(sysctl -n hw.ncpu)
    fi
    
    # Start Ray worker
    if "$INSTALL_DIR/venv/bin/ray" start --address="$HEAD_IP:6379" --num-cpus="$CPUS" 2>&1 | tee -a "$LOG_FILE"; then
        log "✅ Conectado al cluster con $CPUS CPUs"
    else
        log "❌ Error conectando. Reintentando en 60s..."
    fi
    
    sleep 60
done
