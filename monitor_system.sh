#!/bin/bash
# Monitor Script - Bittrader Autonomous Mode

LOG_FILE="/tmp/monitor_bittrader.log"
COORD_URL="http://localhost:5001/api/status"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_system() {
    # Get status
    STATUS=$(curl -s "$COORD_URL" 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        log "🚨 COORDINATOR CAÍDO!"
        return 1
    fi
    
    # Extract metrics
    COMPLETED=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['work_units']['completed'])" 2>/dev/null)
    TOTAL=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['work_units']['total'])" 2>/dev/null)
    ACTIVE=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['workers']['active'])" 2>/dev/null)
    PENDING=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['work_units']['pending'])" 2>/dev/null)
    
    # Calculate percentage
    PCT=$(echo "scale=1; $COMPLETED * 100 / $TOTAL" | bc 2>/dev/null)
    
    log "✅ WUs: $COMPLETED/$TOTAL ($PCT%) | Pend: $PENDING | Workers: $ACTIVE"
    
    # Check if work is progressing
    if [ "$PENDING" -eq 0 ] && [ "$ACTIVE" -eq 0 ]; then
        log "⚠️ No hay trabajo! Creando nuevos work units..."
        python3 /Users/enderj/Coinbase-Cripto-Trader-Claude/generate_advanced_wus.py 2>/dev/null
    fi
    
    return 0
}

# Main loop
log "🚀 INICIANDO MONITOREO AUTÓNOMO"
log "================================="

while true; do
    check_system
    
    # Check for errors in last 5 minutes
    RECENT_ERRORS=$(grep -i "error\|exception" /tmp/coordinator.log 2>/dev/null | tail -5 | wc -l)
    if [ "$RECENT_ERRORS" -gt 0 ]; then
        log "⚠️ $RECENT_ERRORS errores recientes detectados"
    fi
    
    # Check workers
    WORKER_COUNT=$(pgrep -f "crypto_worker" | wc -l)
    if [ "$WORKER_COUNT" -lt 3 ]; then
        log "⚠️ Solo $WORKER_COUNT workers corriendo!"
    fi
    
    sleep 60
done
