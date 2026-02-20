#!/bin/bash
# ==============================================================================
# AUTONOMOUS SYSTEM MAINTAINER
# Se ejecuta cada hora vía cron
# ==============================================================================

LOG_FILE="/tmp/autonomous_maintainer.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S'] $1" | tee -a "$LOG_FILE"
}

log "=== AUTONOMOUS MAINTAINER STARTED ==="

# Verificar coordinator
check_coordinator() {
    log "Checking coordinator..."
    if curl -s http://localhost:5001/api/status > /dev/null 2>&1; then
        log "✅ Coordinator OK"
    else
        log "❌ Coordinator down - restarting..."
        cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
        source ~/coinbase_trader_venv/bin/activate
        python coordinator_port5001.py &
        sleep 5
    fi
}

# Verificar dashboards
check_dashboards() {
    log "Checking dashboards..."
    for port in 5005 5006 8501; do
        if curl -s http://localhost:$port/api/status > /dev/null 2>&1; then
            log "✅ Dashboard $port OK"
        else
            log "❌ Dashboard $port down - restarting..."
            if [ $port -eq 5005 ]; then
                cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude
                source ~/coinbase_trader_venv/bin/activate
                python coordinator_simple.py &
            elif [ $port -eq 5006 ]; then
                cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/f1_dashboard.py &
            fi
            sleep 3
        fi
    done
}

# Verificar workers locales
check_workers() {
    local_count=$(ps aux | grep crypto_worker | grep -v grep | wc -l)
    log "Local workers: $local_count"
    if [ $local_count -lt 3 ]; then
        log "⚠️ Few local workers - restarting..."
        cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
        source ~/coinbase_trader_venv/bin/activate
        for i in 1 2 3; do
            COORDINATOR_URL="http://localhost:5001" WORKER_INSTANCE="$i" nohup python crypto_worker.py > /tmp/worker_$i.log 2>&1 &
        done
        log "✅ Workers restarted"
    fi
}

# Verificar workers remotos
check_remote_workers() {
    log "Checking Linux ROG workers..."
    if ssh -o ConnectTimeout=5 enderj@10.0.0.240 "hostname" 2>/dev/null; then
        remote_count=$(ssh enderj@10.0.0.240 "ps aux | grep crypto_worker | grep -v grep | wc -l" 2>/dev/null)
        log "Linux ROG workers: $remote_count"
        if [ "$remote_count" -lt 5 ]; then
            log "⚠️ Linux workers low - restarting..."
            ssh enderj@10.0.0.240 'cd ~/Coinbase-Cripto-Trader-Claude && for i in 1 2 3 4 5; do COORDINATOR_URL="http://10.0.0.232:5001" NUM_WORKERS="5" WORKER_INSTANCE="$i" nohup python crypto_worker.py > /tmp/worker_$i.log 2>&1 & done'
        fi
    else
        log "❌ SSH fail"
    fi
}

# Backup DB
backup_db() {
    log "Backing up DB..."
    cp coordinator.db "optimization_history/backup_$(date +%Y%m%d_%H%M%S).db.bak
}

# Git sync
git_sync() {
    log "Git sync..."
    cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
    git add -A
    git commit -m "Auto-commit $(date '+%Y-%m-%d %H:%M" 2>/dev/null
    git push origin main 2>/dev/null
}

# Run optimization persistence
run_persistence() {
    log "Running persistence..."
    source ~/coinbase_trader_venv/bin/activate
    python optimization_persistence.py 2>/dev/null
}

# Main
check_coordinator
check_dashboards
check_workers
check_remote_workers
backup_db
run_persistence
git_sync

log "=== AUTONOMOUS MAINTAINER DONE ==="
