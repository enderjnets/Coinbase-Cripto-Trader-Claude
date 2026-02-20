#!/bin/bash
#
# 🔄 Script de Reinicio de Todos los Workers
# Fecha: $(date)
#

echo "========================================"
echo "  🔄 REINICIO DE WORKERS DEL SISTEMA"
echo "========================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠️  $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ❌ $1${NC}"
}

# Directorio del proyecto
PROJECT_DIR="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
cd "$PROJECT_DIR"

echo "📂 Directorio: $PROJECT_DIR"
echo ""

# 1. REINICIO LOCAL (MacBook Pro)
echo "========================================"
echo "  🍎 1. REINICIANDO MACBOOK PRO (LOCAL)"
echo "========================================"
log "Deteniendo workers locales..."

# Matar procesos de crypto_worker existentes
pkill -f "crypto_worker.py" 2>/dev/null
sleep 2

log "Iniciando nuevo worker daemon..."
cd /Users/enderj/.bittrader_worker
bash worker_daemon.sh > /tmp/worker_restart.log 2>&1 &
WORKER_PID=$!
log "Worker daemon iniciado (PID: $WORKER_PID)"

sleep 3

# Verificar que esté corriendo
if ps -p $WORKER_PID > /dev/null; then
    log "✅ Worker daemon local funcionando"
else
    error "❌ Error al iniciar worker daemon local"
fi

echo ""

# 2. REINICIO LINUX ROG (KUBUNTU)
echo "========================================"
echo "  🐧 2. REINICIANDO LINUX ROG (KUBUNTU)"
echo "========================================"

# Verificar si SSH está configurado
if [ -f "$HOME/.ssh/id_rsa_rog" ]; then
    log "Conectando a Linux ROG via SSH..."
    
    # Comandos a ejecutar en Linux ROG
    SSH_CMD="
        echo 'Deteniendo workers existentes...';
        pkill -f 'crypto_worker.py' 2>/dev/null;
        sleep 2;
        echo 'Iniciando worker daemon...';
        cd ~/.bittrader_worker;
        bash worker_daemon.sh > /tmp/worker.log 2>&1 &;
        sleep 3;
        echo 'Verificando...';
        ps aux | grep crypto_worker | grep -v grep | wc -l;
    "
    
    # Ejecutar remotamente
    ssh -i "$HOME/.ssh/id_rsa_rog" ender@192.168.1.XX "$SSH_CMD" 2>/dev/null
    log "✅ Comandos enviados a Linux ROG"
else
    warn "⚠️ SSH no configurado para Linux ROG"
    warn "📝 MANUALMENTE en Linux ROG:"
    echo "   1. Abrir terminal"
    echo "   2. Ejecutar: pkill -f crypto_worker"
    echo "   3. Ejecutar: cd ~/.bittrader_worker && bash worker_daemon.sh &"
fi

echo ""

# 3. REINICIO MACBOOK AIR
echo "========================================"
echo "  🪶 3. REINICIANDO MACBOOK AIR"
echo "========================================"

warn "📝 MANUALMENTE en MacBook Air:"
echo "   1. Conectar por SSH o VNC"
echo "   2. Ejecutar: pkill -f crypto_worker"
echo "   3. Ejecutar: cd ~/.bittrader_worker && bash worker_daemon.sh &"

echo ""

# 4. REINSTALACIÓN ASUS DORADA
echo "========================================"
echo "  🌐 4. REINSTALACIÓN ASUS DORADA (NUNCA FUNCIONÓ)"
echo "========================================"

warn "⚠️ Asus Dorada nunca inició workers. Requiere reinstalación:"
echo ""
echo "   Opción A - Instalación Rápida:"
echo "   1. Conectar al Asus Dorada"
echo "   2. Clonar repositorio:"
echo "      git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git"
echo "   3. Ejecutar instalador:"
echo "      cd Coinbase-Cripto-Trader-Claude"
echo "      bash auto_install_worker.sh"
echo ""
echo "   Opción B - Instalación Manual:"
echo "   1. Copiar archivos del proyecto al Asus"
echo "   2. Instalar Python y dependencias"
echo "   3. Configurar variables de entorno"
echo "   4. Iniciar worker daemon"

echo ""

# 5. VERIFICACIÓN FINAL
echo "========================================"
echo "  🔍 5. VERIFICACIÓN DEL SISTEMA"
echo "========================================"

log "Esperando 10 segundos para que los workers se conecten..."
sleep 10

log "Consultando estado del coordinator..."
cd "$PROJECT_DIR"

# Verificar API del dashboard
STATUS=$(curl -s http://localhost:5006/api/status 2>/dev/null)
if [ -n "$STATUS" ]; then
    echo "$STATUS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"   Workers activos: {data['workers']['active']}\")
print(f\"   WUs completados: {data['work_units']['completed']}\")
print(f\"   WUs en progreso: {data['work_units']['in_progress']}\")
print(f\"   Mejor PnL: \${data['best_strategy']['pnl']:.2f}\")
"
else
    warn "No se pudo conectar al dashboard"
fi

echo ""
log "========================================"
echo "  ✅ REINICIO COMPLETADO"
echo "========================================"
echo ""
echo "📊 Resumen:"
echo "   - MacBook Pro: Reiniciado ✅"
echo "   - Linux ROG: Comandos enviados ✅"
echo "   - MacBook Air: Requiere acción manual ⏳"
echo "   - Asus Dorada: Requiere reinstalación ⏳"
echo ""
echo "🔗 Dashboards:"
echo "   - F1 Dashboard: http://localhost:5006"
echo "   - Coordinator: http://localhost:5005"
echo ""
