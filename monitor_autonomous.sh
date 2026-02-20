#!/bin/bash
# Monitor Autónomo del Sistema Distribuido
# Vigila ambos workers y corrige problemas automáticamente

PROJECT_DIR="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
COORDINATOR_URL="http://localhost:5001"
LOG_FILE="$PROJECT_DIR/monitor_autonomous.log"

cd "$PROJECT_DIR"

echo "╔══════════════════════════════════════════════════════════════════╗" | tee -a "$LOG_FILE"
echo "║       🤖 MONITOR AUTÓNOMO - Sistema Distribuido                 ║" | tee -a "$LOG_FILE"
echo "╚══════════════════════════════════════════════════════════════════╝" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "⏰ Inicio: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Verificar que el daemon del Worker Air esté corriendo
check_worker_air_daemon() {
    if ! pgrep -f "worker_air_daemon.sh" > /dev/null; then
        echo "⚠️  Worker Air daemon no está corriendo - Reiniciando..." | tee -a "$LOG_FILE"
        nohup ./worker_air_daemon.sh > worker_air_daemon.log 2>&1 &
        echo $! > worker_air_daemon.pid
        sleep 3
        echo "✅ Worker Air daemon reiniciado" | tee -a "$LOG_FILE"
    fi
}

# Verificar estado de ambos workers
check_workers_status() {
    WORKER_COUNT=$(curl -s "$COORDINATOR_URL/api/workers" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['workers']))" 2>/dev/null)

    if [ "$WORKER_COUNT" != "2" ]; then
        echo "⚠️  Solo $WORKER_COUNT worker(s) conectado(s) - Se esperaban 2" | tee -a "$LOG_FILE"
        check_worker_air_daemon
        return 1
    fi
    return 0
}

# Obtener uso de CPU del Worker Air local
get_worker_air_cpu() {
    ps aux | grep "crypto_worker.py" | grep -v grep | awk '{print $3}' | head -1
}

# Monitoreo continuo
ITERATION=0
LAST_GEN_AIR=""
LAST_GEN_PRO=""

while true; do
    ITERATION=$((ITERATION + 1))
    TIMESTAMP=$(date '+%H:%M:%S')

    echo "" | tee -a "$LOG_FILE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
    echo "📊 ITERACIÓN #$ITERATION - $TIMESTAMP" | tee -a "$LOG_FILE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

    # Verificar workers
    check_workers_status

    # CPU Worker Air
    CPU_AIR=$(get_worker_air_cpu)
    if [ -n "$CPU_AIR" ]; then
        CPU_CORES_AIR=$(echo "scale=1; $CPU_AIR / 100" | bc 2>/dev/null)
        echo "🖥️  Worker Air: ${CPU_AIR}% CPU (~${CPU_CORES_AIR} cores)" | tee -a "$LOG_FILE"

        # Alert si no está usando suficientes cores
        if (( $(echo "$CPU_AIR < 300" | bc -l) )); then
            echo "   ⚠️  WARNING: Uso bajo de CPU (esperado >700% con población 90)" | tee -a "$LOG_FILE"
        fi
    else
        echo "⚠️  Worker Air: No detectado localmente" | tee -a "$LOG_FILE"
    fi

    # Estado del sistema
    STATUS=$(curl -s "$COORDINATOR_URL/api/status" 2>/dev/null)
    if [ -n "$STATUS" ]; then
        echo "$STATUS" | python3 << 'PYEOF' | tee -a "$LOG_FILE"
import sys, json
data = json.load(sys.stdin)
wu = data['work_units']
workers = data['workers']
print(f"\n📋 Work Units:")
print(f"   Total: {wu['total']}")
print(f"   ✅ Completados: {wu['completed']}")
print(f"   🔄 En progreso: {wu['in_progress']}")
print(f"   ⏳ Pendientes: {wu['pending']}")
print(f"\n👥 Workers activos: {workers['active']}")
PYEOF
    fi

    # Últimas líneas del log Worker Air
    echo "" | tee -a "$LOG_FILE"
    echo "📜 Worker Air (últimas 5 líneas):" | tee -a "$LOG_FILE"
    tail -5 worker_air.log 2>/dev/null | sed 's/^/   /' | tee -a "$LOG_FILE"

    # Extraer generación actual
    CURRENT_GEN=$(tail -20 worker_air.log 2>/dev/null | grep "Gen [0-9]" | tail -1 | grep -oE "Gen [0-9]+")
    if [ -n "$CURRENT_GEN" ] && [ "$CURRENT_GEN" != "$LAST_GEN_AIR" ]; then
        echo "   🔄 Progreso: $CURRENT_GEN" | tee -a "$LOG_FILE"
        LAST_GEN_AIR="$CURRENT_GEN"
    fi

    # Esperar 30 segundos antes de la siguiente iteración
    echo "" | tee -a "$LOG_FILE"
    echo "⏳ Próxima verificación en 30s..." | tee -a "$LOG_FILE"
    sleep 30
done
