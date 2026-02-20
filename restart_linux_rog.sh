#!/bin/bash
#
# 🔄 Script de Reinicio para Linux ROG
# Ejecutar en: ender@192.168.1.XX (o IP del ROG)
#

echo "========================================"
echo "  🔄 REINICIANDO LINUX ROG"
echo "  $(date)"
echo "========================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠️  $1${NC}"; }

log "1. Deteniendo workers existentes..."
pkill -f "crypto_worker.py" 2>/dev/null
pkill -f "worker_daemon.sh" 2>/dev/null
sleep 2

log "2. Verificando que se detuvieron..."
if ps aux | grep -q "[c]rypto_worker"; then
    warn "Workers aún activos, forzando..."
    pkill -9 -f "crypto_worker.py" 2>/dev/null
    sleep 1
fi

log "3. Limpiando caché de Ray..."
ray stop 2>/dev/null
sleep 1

log "4. Iniciando worker daemon..."
cd ~/.bittrader_worker
nohup bash worker_daemon.sh > /tmp/worker.log 2>&1 &
WORKER_PID=$!

log "5. Verificando inicio..."
sleep 3

if ps -p $WORKER_PID > /dev/null 2>&1; then
    log "✅ Worker daemon iniciado (PID: $WORKER_PID)"
else
    error "❌ Error al iniciar worker daemon"
    exit 1
fi

log "6. Verificando workers activos..."
sleep 5
ps aux | grep crypto_worker | grep -v grep | wc -l

log "7. Últimas líneas del log..."
tail -5 /tmp/worker.log

echo ""
log "========================================"
echo "  ✅ LINUX ROG REINICIADO"
echo "========================================"
echo ""
echo "📊 Verificar en dashboard: http://localhost:5006"
echo ""
