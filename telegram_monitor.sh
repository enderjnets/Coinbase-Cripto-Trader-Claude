#!/bin/bash
# ============================================================================
# TELEGRAM MONITOR - Strategy Miner Progress Notifications
# ============================================================================

# Configuración Telegram
BOT_TOKEN="TELEGRAM_BOT_TOKEN_REDACTED"
CHAT_ID="771213858"

# Configuración del sistema
COORDINATOR_URL="http://localhost:5001"
LINUX_HOST="enderj@10.0.0.240"
CHECK_INTERVAL=300  # 5 minutos

# Variables de estado
LAST_COMPLETED=0
LAST_BEST_PNL=0

# Función para enviar mensaje a Telegram
send_telegram() {
    local message="$1"
    curl -s -G "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${CHAT_ID}" \
        --data-urlencode "text=${message}" \
        --data-urlencode "parse_mode=HTML" > /dev/null 2>&1
}

# Función para obtener estado del coordinador
get_status() {
    curl -s "${COORDINATOR_URL}/api/status" 2>/dev/null
}

# Función para obtener progreso del worker Linux
get_linux_progress() {
    ssh -o ConnectTimeout=5 ${LINUX_HOST} "grep -E 'Gen [0-9]+.*PnL' /tmp/auto_worker.log 2>/dev/null | tail -1" 2>/dev/null
}

echo "========================================"
echo "TELEGRAM MONITOR - Strategy Miner"
echo "========================================"
echo "Bot: Eko_MacPro_bot"
echo "Intervalo: ${CHECK_INTERVAL}s"
echo ""

# Mensaje inicial
send_telegram "🚀 <b>Monitor Iniciado</b>

Sistema de monitoreo activo.
Intervalo: cada 5 minutos

Comandos disponibles (proximamente):
/status - Estado actual
/workers - Workers activos
/stop - Detener monitoreo"

echo "Mensaje inicial enviado. Monitoreando..."

while true; do
    # Obtener estado
    STATUS=$(get_status)

    if [ -n "$STATUS" ]; then
        COMPLETED=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['work_units']['completed'])" 2>/dev/null)
        IN_PROGRESS=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['work_units']['in_progress'])" 2>/dev/null)
        PENDING=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['work_units']['pending'])" 2>/dev/null)
        TOTAL=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['work_units']['total'])" 2>/dev/null)
        WORKERS=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['workers']['active'])" 2>/dev/null)

        # Obtener progreso Linux
        LINUX_PROGRESS=$(get_linux_progress)

        # Verificar si hay nuevo work unit completado
        if [ -n "$COMPLETED" ] && [ "$COMPLETED" -gt "$LAST_COMPLETED" ]; then
            send_telegram "✅ <b>Work Unit Completado!</b>

Completados: ${COMPLETED}/${TOTAL}
Pendientes: ${PENDING}
Workers activos: ${WORKERS}"
            LAST_COMPLETED=$COMPLETED
        fi

        # Log local
        echo "[$(date '+%H:%M:%S')] WU: ${COMPLETED}/${TOTAL} | Workers: ${WORKERS} | Linux: ${LINUX_PROGRESS}"
    else
        echo "[$(date '+%H:%M:%S')] Error: No se pudo conectar al coordinador"
    fi

    sleep $CHECK_INTERVAL
done
