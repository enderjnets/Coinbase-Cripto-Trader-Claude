#!/bin/bash
#
# 🔄 Script de Reinicio para MacBook Air
# Ejecutar en el MacBook Air (localmente o por SSH)
#

echo "========================================"
echo "  🔄 REINICIANDO MACBOOK AIR"
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
WORKERS_RUNNING=$(ps aux | grep crypto_worker | grep -v grep | wc -l)
if [ "$WORKERS_RUNNING" -gt 0 ]; then
    warn "Workers aún activos: $WORKERS_RUNNING"
    warn "Forzando detención..."
    pkill -9 -f "crypto_worker.py" 2>/dev/null
    sleep 1
fi

log "3. Verificando configuración Tailscale..."
if command -v tailscale &> /dev/null; then
    TS_STATUS=$(tailscale status 2>/dev/null)
    log "Tailscale: $TS_STATUS"
else
    warn "Tailscale no encontrado"
fi

log "4. Iniciando worker daemon..."
cd ~/.bittrader_worker
nohup bash worker_daemon.sh > /tmp/worker_air.log 2>&1 &
WORKER_PID=$!

log "5. Verificando inicio..."
sleep 3

if ps -p $WORKER_PID > /dev/null 2>&1; then
    log "✅ Worker daemon iniciado (PID: $WORKER_PID)"
else
    error "❌ Error al iniciar worker daemon"
    exit 1
fi

log "6. Workers activos..."
sleep 5
ps aux | grep crypto_worker | grep -v grep | wc -l

log "7. Últimas líneas del log..."
tail -10 /tmp/worker_air.log

echo ""
log "========================================"
echo "  ✅ MACBOOK AIR REINICIADO"
echo "========================================"
echo ""
echo "📊 Verificar en dashboard: http://localhost:5006"
echo ""
