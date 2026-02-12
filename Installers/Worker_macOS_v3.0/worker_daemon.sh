#!/bin/bash
#
# Bittrader Worker Daemon v3.0 - macOS
# Manages multiple crypto_worker.py instances with auto-restart
#
# Usage: ./worker_daemon.sh [NUM_WORKERS]
#

INSTALL_DIR="$HOME/crypto_worker"
NUM_WORKERS="${1:-3}"
LOG_DIR="/tmp"

# Load config
if [ -f "$INSTALL_DIR/config.env" ]; then
    source "$INSTALL_DIR/config.env"
fi

COORDINATOR_URL="${COORDINATOR_URL:-http://10.0.0.232:5001}"

echo "========================================"
echo " Bittrader Worker Daemon v3.0"
echo "========================================"
echo " Workers: $NUM_WORKERS"
echo " Coordinator: $COORDINATOR_URL"
echo " Logs: $LOG_DIR/worker_*.log"
echo "========================================"
echo ""

# Activate virtual environment
if [ -f "$INSTALL_DIR/venv/bin/activate" ]; then
    source "$INSTALL_DIR/venv/bin/activate"
    echo "Virtual environment activated"
else
    echo "ERROR: Virtual environment not found"
    exit 1
fi

cd "$INSTALL_DIR"

# Function to start a worker
start_worker() {
    local instance=$1
    echo "Starting worker $instance..."

    COORDINATOR_URL="$COORDINATOR_URL" \
    WORKER_INSTANCE="$instance" \
    NUM_WORKERS="$NUM_WORKERS" \
    USE_RAY="false" \
    PYTHONUNBUFFERED=1 \
    nohup python -u crypto_worker.py > "$LOG_DIR/worker_$instance.log" 2>&1 &

    echo "Worker $instance started (PID: $!)"
}

# Start all workers
for i in $(seq 1 $NUM_WORKERS); do
    start_worker $i
    sleep 2
done

echo ""
echo "All $NUM_WORKERS workers started!"
echo ""
echo "Monitor logs:"
echo "  tail -f $LOG_DIR/worker_1.log"
echo ""
echo "Stop all workers:"
echo "  pkill -f crypto_worker"
echo ""
