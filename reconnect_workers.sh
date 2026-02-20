#!/bin/bash
################################################################################
# SCRIPT DE RECONEXIÓN DE WORKERS
# Intenta reconectar workers offline automáticamente
#
# Uso: ./reconnect_workers.sh [--daemon] [--once]
################################################################################

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuración
COORDINATOR_URL="http://localhost:5001"
LOG_FILE="worker_reconnect.log"
INTERVAL=60  # segundos entre reintentos

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$msg"
    echo "$msg" >> "$LOG_FILE"
}

log_color() {
    echo -e "${2}$1${NC}"
}

# Verificar si coordinator está disponible
check_coordinator() {
    curl -s --max-time 5 "$COORDINATOR_URL/api/status" > /dev/null 2>&1
}

# Intentar conectar via SSH
ssh_connect() {
    local name=$1
    local ip=$2
    local user="enderj"

    # Intentar conexión SSH básica
    if timeout 10 ssh -o ConnectTimeout=5 \
                     -o StrictHostKeyChecking=no \
                     -o BatchMode=yes \
                     -o UserKnownHostsFile=/dev/null \
                     "$user@$ip" "echo 'SSH_OK'" 2>/dev/null; then
        log_color "✅ $name ($ip) accesible via SSH" "$GREEN"
        return 0
    else
        return 1
    fi
}

# Iniciar worker remotamente
start_remote_worker() {
    local ip=$1
    local user="enderj"

    log "Iniciando worker en $ip..."

    # Comandos para iniciar worker
    ssh -o StrictHostKeyChecking=no "$user@$ip" "
        cd ~/Coinbase*Trader* 2>/dev/null || cd ~/Bittrader* 2>/dev/null || exit 1

        # Detener workers antiguos
        pkill -f 'crypto_worker' 2>/dev/null || true
        sleep 2

        # Iniciar nuevo worker en background
        nohup python3 crypto_worker.py $COORDINATOR_URL > ~/worker_remote.log 2>&1 &
        sleep 2

        # Verificar que está corriendo
        if pgrep -f 'crypto_worker' > /dev/null; then
            echo 'WORKER_STARTED'
        else
            echo 'WORKER_FAILED'
        fi
    " 2>/dev/null
}

# Verificar estado de workers en coordinator
check_workers_status() {
    log "📊 Verificando estado de workers..."
    curl -s "$COORDINATOR_URL/api/workers" 2>/dev/null | python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)
    now = __import__('time').time()

    print('='*60)
    print('{:<40} {:<10} {:<8} {:<10}'.format('WORKER', 'STATUS', 'WUs', 'MINUTOS_AGO'))
    print('='*60)

    for w in data['workers']:
        name = w['id'][:38]
        status = w['status']
        wus = w['work_units_completed']
        mins = w.get('last_seen_minutes_ago', 999)

        if status == 'active':
            color = '\033[0;32m'  # verde
        elif mins < 60:
            color = '\033[1;33m'  # amarillo
        else:
            color = '\033[0;31m'  # rojo

        print('{}{:<40} {:<10} {:<8} {:<10.1f}\033[0m'.format(color, name, status, wus, mins))

    print('='*60)
except Exception as e:
    print('Error obteniendo estado: ' + str(e))
" 2>/dev/null
}

# Modo daemon: intentar reconectar periódicamente
run_daemon() {
    log_color "🔄 Modo DAEMON iniciado - intentando reconectar cada ${INTERVAL}s" "$BLUE"
    log "Presiona Ctrl+C para detener"

    while true; do
        echo ""
        check_workers_status
        echo ""

        # Lista de workers a verificar (nombre, IP)
        workers_list="MacBook-Air 10.0.0.47 Linux-ROG 10.0.0.30"

        while read -r name ip; do
            if [ -z "$name" ] || [ -z "$ip" ]; then
                continue
            fi

            # Verificar si worker está activo
            is_active=$(curl -s "$COORDINATOR_URL/api/workers" 2>/dev/null | \
                       python3 -c "import sys,json; w=[x for x in json.load(sys.stdin)['workers'] if '$name'.lower() in x['id'].lower()]; print('active' if w and w[0]['status']=='active' else 'inactive')" 2>/dev/null)

            if [ "$is_active" != "active" ]; then
                log "⚠️  $name parece offline, intentando despertar..."

                # Intentar SSH
                if ssh_connect "$name" "$ip"; then
                    start_remote_worker "$ip"
                fi
            else
                log_color "✅ $name ya está activo" "$GREEN"
            fi
        done <<< "$workers_list"

        sleep $INTERVAL
    done
}

# Modo único: intentar una vez
run_once() {
    log "🔍 Escaneo único de workers..."

    check_workers_status
    echo ""

    # Lista de workers
    workers_list="MacBook-Air 10.0.0.47 Linux-ROG 10.0.0.30"

    while read -r name ip; do
        if [ -z "$name" ] || [ -z "$ip" ]; then
            continue
        fi

        log "Verificando $name ($ip)..."

        if ssh_connect "$name" "$ip"; then
            start_remote_worker "$ip"
        else
            log_color "❌ $name no accesible - probablemente apagado" "$RED"
        fi
    done <<< "$workers_list"
}

# Mostrar ayuda
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --daemon   Modo daemon: reconnecta periódicamente"
    echo "  --once     Escanear una sola vez (default)"
    echo "  --status   Solo mostrar estado actual"
    echo "  --help     Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 --once           # Escanear una vez"
    echo "  $0 --daemon         # Mantener ejecutándose y reconectar"
}

################################################################################
# MAIN
################################################################################

case "${1:-}" in
    --daemon)
        run_daemon
        ;;
    --status)
        check_workers_status
        ;;
    --help|-h)
        show_help
        ;;
    *)
        run_once
        ;;
esac
