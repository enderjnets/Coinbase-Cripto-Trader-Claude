#!/bin/bash
#
# Bittrader Worker Daemon v2.6 - Linux Edition
# Persistent Ray Worker daemon with automatic reconnection
#

INSTALL_DIR="$HOME/.bittrader_worker"
LOG_FILE="$INSTALL_DIR/logs/worker.log"
LOCK_FILE="$INSTALL_DIR/worker_daemon.lock"

# Create logs directory
mkdir -p "$INSTALL_DIR/logs"

# Check if already running
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Worker daemon already running (PID: $PID)"
        exit 1
    fi
fi

# Create lock file
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

# Load configuration
if [ ! -f "$INSTALL_DIR/config.env" ]; then
    echo "ERROR: config.env not found"
    exit 1
fi

source "$INSTALL_DIR/config.env"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "================================================================"
log "    Worker Daemon v2.6 Starting (Linux)"
log "================================================================"
log ""
log "Configuration:"
log "  Head IP: $HEAD_IP"
log "  CPUs: $NUM_CPUS"
log "  Python: $PYTHON_PATH"
log "  Ray: $RAY_PATH"
log ""

# Enable cluster mode
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
export RAY_ENABLE_IPV6=0

# Activate virtual environment
if [ -f "$INSTALL_DIR/venv/bin/activate" ]; then
    source "$INSTALL_DIR/venv/bin/activate"
    log "✅ Virtual environment activated"
fi

RETRY_COUNT=0
MAX_RETRIES=999999

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Check connectivity to HEAD
    if ! ping -c 1 -W 2 "$HEAD_IP" &> /dev/null; then
        log "⚠️  Cannot reach Head Node ($HEAD_IP)"
        log "   Retrying in 30 seconds..."
        sleep 30
        continue
    fi

    # Check if Ray is already running
    if pgrep -x "raylet" > /dev/null; then
        # Ray is running, check if healthy
        if "$PYTHON_PATH" -c "import ray; ray.init(address='auto', ignore_reinit_error=True); print(ray.cluster_resources())" &> /dev/null; then
            # All good, wait and check again
            sleep 60
            continue
        else
            log "⚠️  Ray running but not connected. Restarting..."
            "$RAY_PATH" stop 2>/dev/null || true
            sleep 2
        fi
    fi

    # Connect to cluster
    log "🔗 Connecting to $HEAD_IP:6379..."

    if "$RAY_PATH" start --address="$HEAD_IP:6379" --num-cpus="$NUM_CPUS" 2>&1 | tee -a "$LOG_FILE"; then
        log "✅ Connected to cluster with $NUM_CPUS CPUs"
    else
        log "❌ Connection failed"
        log "   Retrying in 30 seconds..."
        sleep 30
        RETRY_COUNT=$((RETRY_COUNT + 1))
        continue
    fi

    # Monitor connection
    sleep 60
done

log "❌ Maximum retry attempts reached. Exiting."
