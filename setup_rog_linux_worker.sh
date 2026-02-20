#!/bin/bash
################################################################################
# SCRIPT DE CONFIGURACIÓN AUTOMÁTICA DEL WORKER EN LINUX ROG
# Ejecutar ESTE SCRIPT en el Linux ROG después de reinstalar
################################################################################

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🔧 CONFIGURACIÓN AUTOMÁTICA - LINUX ROG WORKER           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ==============================================================================
# CONFIGURACIÓN - EDITAR ESTOS VALORES
# ==============================================================================
COORDINATOR_IP="100.77.179.14"  # IP de Tailscale del MacBook Pro
COORDINATOR_PORT="5001"
COORDINATOR_URL="http://$COORDINATOR_IP:$COORDINATOR_PORT"
NUM_WORKERS=4

echo -e "${YELLOW}📡 Coordinator: $COORDINATOR_URL${NC}"
echo -e "${YELLOW}👥 Workers a iniciar: $NUM_WORKERS${NC}"
echo ""

# ==============================================================================
# 1. ACTUALIZAR SISTEMA
# ==============================================================================
echo -e "${BLUE}🔄 Actualizando sistema...${NC}"
sudo apt update -y
sudo apt upgrade -y
echo -e "${GREEN}✅ Sistema actualizado${NC}"
echo ""

# ==============================================================================
# 2. INSTALAR DEPENDENCIAS
# ==============================================================================
echo -e "${BLUE}📦 Instalando dependencias...${NC}"
sudo apt install -y python3 python3-pip python3-venv git curl wget htop

# Verificar Python
PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "${GREEN}🐍 Python: $PYTHON_VERSION${NC}"
echo ""

# ==============================================================================
# 3. CLONAR/RESFRESCAR PROYECTO
# ==============================================================================
echo -e "${BLUE}📁 Configurando proyecto...${NC}"

# Opción A: Desde GitHub
if [ -d "$HOME/Coinbase-Cripto-Trader-Claude" ]; then
    echo "Actualizando desde GitHub..."
    cd $HOME/Coinbase-Cripto-Trader-Claude
    git pull origin main
else
    echo "Clonando desde GitHub..."
    cd $HOME
    git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git
    cd Coinbase-Cripto-Trader-Claude
fi

PROJECT_DIR=$(pwd)
echo -e "${GREEN}✅ Proyecto en: $PROJECT_DIR${NC}"
echo ""

# ==============================================================================
# 4. CREAR VIRTUAL ENVIRONMENT
# ==============================================================================
echo -e "${BLUE}🐍 Creando virtual environment...${NC}"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install requests pandas numpy
echo -e "${GREEN}✅ Virtual environment listo${NC}"
echo ""

# ==============================================================================
# 5. INSTALAR WORKERS COMO SERVICIO
# ==============================================================================
echo -e "${BLUE}⚙️  Configurando workers como servicio systemd...${NC}"

# Crear script de inicio del worker
cat > $HOME/start_worker.sh << 'SCRIPT'
#!/bin/bash
COORDINATOR_URL="${1:-http://100.77.179.14:5001}"
WORKER_INSTANCE="${2:-1}"

source $(dirname $0)/.venv/bin/activate
cd $(dirname $0)
exec python3 crypto_worker.py $COORDINATOR_URL
SCRIPT

chmod +x $HOME/start_worker.sh

# Crear archivo de servicio systemd para cada worker
for i in $(seq 1 $NUM_WORKERS); do
    SERVICE_NAME="crypto-worker@$i"
    
    cat > /tmp/$SERVICE_NAME.service << EOF
[Unit]
Description=Crypto Worker $i
After=network.target

[Service]
Type=simple
User=enderj
WorkingDirectory=$PROJECT_DIR
Environment=COORDINATOR_URL=$COORDINATOR_URL
Environment=WORKER_INSTANCE=$i
ExecStart=$HOME/start_worker.sh $COORDINATOR_URL $i
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo cp /tmp/$SERVICE_NAME.service /etc/systemd/system/
    sudo systemctl enable $SERVICE_NAME
    echo -e "${GREEN}✅ Servicio $SERVICE_NAME configurado${NC}"
done

echo ""

# ==============================================================================
# 6. INICIAR WORKERS
# ==============================================================================
echo -e "${BLUE}🚀 Iniciando workers...${NC}"
sudo systemctl daemon-reload

for i in $(seq 1 $NUM_WORKERS); do
    SERVICE_NAME="crypto-worker@$i"
    sudo systemctl start $SERVICE_NAME
    sleep 2
    STATUS=$(sudo systemctl is-active $SERVICE_NAME 2>&1)
    echo -e "  Worker $i: $STATUS"
done

echo ""

# ==============================================================================
# 7. VERIFICACIÓN FINAL
# ==============================================================================
echo -e "${BLUE}🔍 Verificando conexión con coordinator...${NC}"
sleep 3

curl -s $COORDINATOR_URL/api/status 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('='*50)
    print('📊 ESTADO DEL COORDINATOR')
    print('='*50)
    print(f\"  Workers activos: {data['workers']['active']}\")
    print(f\"  WUs completados: {data['work_units']['completed']}/{data['work_units']['total']}\")
    print(f\"  Best PnL: \${data['best_strategy']['pnl']:.2f}\")
    print('='*50)
except Exception as e:
    print(f'⚠️  No se pudo verificar: {e}')
" 2>/dev/null || echo "  ⚠️  Coordinator no accesible todavía"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ CONFIGURACIÓN COMPLETADA                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "📝 Comandos útiles:"
echo "   Ver workers:     sudo systemctl status 'crypto-worker@*'"
echo "   Ver logs:       sudo journalctl -u crypto-worker@1 -f"
echo "   Detener todos:  sudo systemctl stop 'crypto-worker@*'"
echo "   Reiniciar:      sudo systemctl restart crypto-worker@1"
echo ""
