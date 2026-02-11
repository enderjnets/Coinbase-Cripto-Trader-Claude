#!/bin/bash
#
# 🚀 ULTIMATE TRADING SYSTEM - INSTALADOR COMPLETO
# Instala y configura todo el sistema de trading automatizado
#
# Uso: bash install_system.sh
#

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ${BLUE}🚀 ULTIMATE TRADING SYSTEM - INSTALADOR COMPLETO${NC}  ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Detectar SO
OS="$(uname -s)"
case "$OS" in
    Darwin*)
        echo -e "${BLUE}🍎 Detectado: macOS${NC}"
        ;;
    Linux*)
        echo -e "${BLUE}🐧 Detectado: Linux${NC}"
        ;;
    *)
        echo -e "${RED}❌ SO no soportado${NC}"
        exit 1
        ;;
esac

# Directorio del proyecto
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo -e "${GREEN}📁 Directorio del proyecto:${NC} $PROJECT_DIR"
echo ""

# ==================== VERIFICACIONES ====================
echo -e "${YELLOW}🔍 Verificando dependencias...${NC}"
echo ""

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "   ${GREEN}✅${NC} Python: $PYTHON_VERSION"
else
    echo -e "   ${RED}❌${NC} Python no instalado"
    echo "   Instala Python 3.9+ desde python.org"
    exit 1
fi

# Pip
if command -v pip3 &> /dev/null; then
    echo -e "   ${GREEN}✅${NC} pip3 disponible"
else
    echo -e "   ${YELLOW}⚠️${NC} pip3 no disponible"
fi

# Git
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version 2>&1)
    echo -e "   ${GREEN}✅${NC} Git: $GIT_VERSION"
else
    echo -e "   ${RED}❌${NC} Git no instalado"
    exit 1
fi

# ==================== CREAR DIRECTORIOS ====================
echo ""
echo -e "${YELLOW}📁 Creando estructura de directorios...${NC}"
echo ""

mkdir -p "$PROJECT_DIR/backups"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/models"
mkdir -p "$PROJECT_DIR/.venv"

echo -e "   ${GREEN}✅${NC} Directorios creados"

# ==================== INSTALAR DEPENDENCIAS ====================
echo ""
echo -e "${YELLOW}📦 Instalando dependencias de Python...${NC}"
echo ""

# Crear virtual environment
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    python3 -m venv .venv
    echo -e "   ${GREEN}✅${NC} Virtual environment creado"
fi

# Activar e instalar
source .venv/bin/activate

# Instalar dependencias básicas
pip install --quiet --upgrade pip 2>/dev/null || true

# Instalar dependencias del requirements.txt si existe
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    pip install --quiet -r requirements.txt
    echo -e "   ${GREEN}✅${NC} Dependencies de requirements.txt instaladas"
fi

# Instalar dependencias adicionales para trading
echo -e "   ${BLUE}📊 Instalando librerías de trading...${NC}"

pip install --quiet \
    requests \
    pandas \
    numpy \
    plotly \
    flask \
    streamlit \
    scikit-learn \
    gymnasium \
    stable-baselines3 \
    tensorboard \
    ccxt \
    python-dotenv \
    sqlalchemy \
    redis \
    celery \
    APScheduler \
    schedule \
    python-dateutil \
    aiohttp \
    websockets \
    loguru \
    pyyaml \
    tqdm \
    tabulate \
    colorlog \
    emoji \
    pycoingecko \
    python-binance \
    ccxt \
    2>/dev/null || true

echo -e "   ${GREEN}✅${NC} Librerías instaladas"

# ==================== PERMISOS ====================
echo ""
echo -e "${YELLOW}🔐 Configurando permisos...${NC}"
echo ""

chmod +x *.sh 2>/dev/null || true
chmod +x *.py 2>/dev/null || true

echo -e "   ${GREEN}✅${NC} Permisos configurados"

# ==================== CONFIGURACIÓN ====================
echo ""
echo -e "${YELLOW}⚙️ Configuración inicial...${NC}"
echo ""

# Crear archivo .env si no existe
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cat > "$PROJECT_DIR/.env" << 'EOF'
# ============================================
# CONFIGURACIÓN DEL SISTEMA DE TRADING
# ============================================

# Configuración General
PROJECT_NAME="Ultimate Trading System"
ENVIRONMENT="development"  # development | production

# API Keys (para live trading)
COINBASE_API_KEY=""
COINBASE_API_SECRET=""
COINBASE_API_PASSPHRASE=""

# Configuración de Trading
INITIAL_CAPITAL=500
RISK_PER_TRADE=0.02  # 2%
MAX_DAILY_LOSS=0.05  # 5%
TARGET_DAILY_RETURN=0.05  # 5%

# Workers
MIN_WORKERS=5
MAX_WORKERS=50

# Database
DATABASE_PATH="./coordinator.db"

# Logging
LOG_LEVEL="INFO"
LOG_DIR="./logs"

# Auto-Improvement
AUTO_IMPROVEMENT_ENABLED=true
AUTO_IMPROVEMENT_DAY="sunday"
AUTO_IMPROVEMENT_HOUR=0

# Alertas
ALERTS_ENABLED=true
TELEGRAM_TOKEN=""
TELEGRAM_CHAT_ID=""
DISCORD_WEBHOOK=""

# ============================================
EOF
    echo -e "   ${GREEN}✅${NC} .env creado (configura tus API keys)"
else
    echo -e "   ${YELLOW}⚠️${NC} .env ya existe"
fi

# ==================== VERIFICAR ARCHIVOS ====================
echo ""
echo -e "${YELLOW}📄 Verificando archivos del sistema...${NC}"
echo ""

REQUIRED_FILES=(
    "coordinator.py"
    "crypto_worker.py"
    "strategy_miner.py"
    "interface.py"
    "f1_dashboard.py"
)

OPTIONAL_FILES=(
    "auto_improvement_system.py"
    "interactive_dashboard.py"
    "analyze_perf_simple.py"
    "knowledge_base_strategies.py"
    "master_control_panel.py"
    "cron_setup.sh"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "   ${GREEN}✅${NC} $file"
    else
        echo -e "   ${RED}❌${NC} $file (FALTANTE)"
    fi
done

echo ""
for file in "${OPTIONAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "   ${GREEN}✅${NC} $file (opcional)"
    else
        echo -e "   ${YELLOW}⚠️${NC} $file (no encontrado)"
    fi
done

# ==================== CREAR ACCESOS DIRECTOS ====================
echo ""
echo -e "${YELLOW}🔗 Creando accesos directos...${NC}"
echo ""

# Crear script de inicio rápido
cat > "$PROJECT_DIR/start_system.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Iniciando Ultimate Trading System..."
source .venv/bin/activate
python3 coordinator.py &
sleep 2
echo "✅ Sistema iniciado"
echo ""
echo "📊 Dashboards:"
echo "   • http://localhost:5001 (Coordinator)"
echo "   • http://localhost:5006 (F1 Dashboard)"
echo "   • http://localhost:5007 (Auto-Improvement)"
echo "   • http://localhost:8501 (Streamlit)"
echo ""
echo "Presiona Enter para salir..."
read
pkill -f coordinator.py
echo "🛑 Sistema detenido"
EOF

chmod +x "$PROJECT_DIR/start_system.command"
echo -e "   ${GREEN}✅${NC} start_system.command creado"

# Crear script de estado
cat > "$PROJECT_DIR/status_system.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
python3 -c "
import sqlite3
conn = sqlite3.connect('coordinator.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM workers WHERE (julianday(\"now\") - last_seen) < (10.0/1440.0)')
active = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM work_units')
wus = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM results')
results = c.fetchone()[0]
c.execute('SELECT MAX(pnl) FROM results')
best_pnl = c.fetchone()[0] or 0
print(f'''
╔════════════════════════════╗
║  📊 ESTADO DEL SISTEMA      ║
╠════════════════════════════╣
║  👥 Workers: {active} activos          ║
║  📦 WUs: {wus}                   ║
║  📈 Results: {results:,}              ║
║  💰 Best PnL: \${best_pnl:.2f}          ║
╚════════════════════════════╝
''')
"
EOF

chmod +x "$PROJECT_DIR/status_system.command"
echo -e "   ${GREEN}✅${NC} status_system.command creado"

# ==================== RESUMEN ====================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ${BLUE}✅ INSTALACIÓN COMPLETADA${NC}                                ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📊 Archivos del sistema:${NC}"
echo "   • start_system.command - Iniciar sistema"
echo "   • status_system.command - Ver estado"
echo "   • .env - Configuración (editar para API keys)"
echo ""
echo -e "${YELLOW}🌐 Dashboards:${NC}"
echo "   • http://localhost:5001 (Coordinator)"
echo "   • http://localhost:5006 (F1 Dashboard)"
echo "   • http://localhost:5007 (Auto-Improvement Dashboard)"
echo "   • http://localhost:8501 (Streamlit)"
echo ""
echo -e "${YELLOW}🚀 Próximos pasos:${NC}"
echo "   1. Edita .env con tus API keys (si vas a hacer live trading)"
echo "   2. Ejecuta: bash start_system.command"
echo "   3. Abre los dashboards en tu navegador"
echo ""
echo -e "${GREEN}🎉 ¡Sistema listo para usar!${NC}"
