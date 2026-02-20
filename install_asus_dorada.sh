#!/bin/bash
#
# 🔧 Script de Instalación para Asus Dorada
# Este worker NUNCA funcionó, requiere instalación completa
#

echo "========================================"
echo "  🔧 INSTALANDO WORKER EN ASUS DORADA"
echo "  $(date)"
echo "========================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠️  $1${NC}"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ❌ $1${NC}"; }

# Verificar que es Linux
if [ "$(uname)" != "Linux" ]; then
    error "Este script debe ejecutarse en Linux (Asus Dorada)"
    exit 1
fi

log "1. Verificando sistema..."
echo "   OS: $(uname -a)"
echo "   CPU: $(nproc) cores"
echo "   Memory: $(free -h | grep Mem | awk '{print $2}')"

log "2. Instalando dependencias..."
# Ubuntu/Debian
if command -v apt &> /dev/null; then
    sudo apt update -qq
    sudo apt install -y python3 python3-pip git curl
elif command -v yum &> /dev/null; then
    sudo yum install -y python3 python3-pip git curl
fi

log "3. Verificando Python..."
python3 --version
pip3 --version

log "4. Clonando repositorio..."
if [ -d "$HOME/Coinbase-Cripto-Trader-Claude" ]; then
    warn "Directorio existente, actualizando..."
    cd "$HOME/Coinbase-Cripto-Trader-Claude"
    git pull origin main
else
    cd $HOME
    git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git
    cd Coinbase-Cripto-Trader-Claude
fi

log "5. Instalando dependencias Python..."
pip3 install --user -r requirements.txt 2>/dev/null || pip3 install --user ray redis psutil

log "6. Creando directorio del worker..."
mkdir -p ~/.bittrader_worker

log "7. Configurando variables de entorno..."
cat > ~/.bittrader_worker/config.env << 'EOF'
HEAD_IP=100.118.215.73
TAILSCALE_IP=N/A (LAN)
INSTALL_DATE=$(date)
THROTTLE_ENABLED=true
EOF

log "8. Copiando archivos del worker..."
cp worker_daemon.sh ~/.bittrader_worker/
cp -r venv ~/.bittrader_worker/ 2>/dev/null || true

log "9. Iniciando worker daemon..."
cd ~/.bittrader_worker
chmod +x worker_daemon.sh
nohup bash worker_daemon.sh > /tmp/asus_worker.log 2>&1 &
WORKER_PID=$!

log "10. Verificando..."
sleep 5

if ps -p $WORKER_PID > /dev/null 2>&1; then
    log "✅ Worker daemon iniciado (PID: $WORKER_PID)"
else
    error "❌ Error al iniciar worker daemon"
    tail -20 /tmp/asus_worker.log
    exit 1
fi

log "11. Verificando workers activos..."
ps aux | grep crypto_worker | grep -v grep | wc -l

log "12. Últimas líneas del log..."
tail -15 /tmp/asus_worker.log

echo ""
echo "========================================"
log "  ✅ INSTALACIÓN COMPLETADA EN ASUS DORADA"
echo "========================================"
echo ""
echo "📊 Verificar en dashboard: http://localhost:5006"
echo ""
echo "🔧 Si hay errores, revisar:"
echo "   - Log: tail -f /tmp/asus_worker.log"
echo "   - Dependencias Python: pip3 list | grep -E 'ray|psutil|redis'"
echo "   - Conexión Tailscale: tailscale status"
echo ""
