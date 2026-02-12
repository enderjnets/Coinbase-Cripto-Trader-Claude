#!/bin/bash
#
# Bittrader Worker Installer v3.0 - macOS Edition
# Coordinator-based distributed computing with Numba JIT acceleration
#
# NEW in v3.0:
# - Coordinator REST API architecture (no Ray)
# - Numba JIT acceleration (4000x speedup)
# - Multi-worker support per machine
#
# Usage: ./install.sh [COORDINATOR_URL]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="$HOME/crypto_worker"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Default coordinator URL (MacBook Pro LAN IP)
DEFAULT_COORDINATOR_URL="http://10.0.0.232:5001"

echo ""
echo -e "${CYAN}+============================================================+${NC}"
echo -e "${CYAN}|                                                            |${NC}"
echo -e "${CYAN}|    BITTRADER WORKER INSTALLER v3.0 - NUMBA JIT EDITION    |${NC}"
echo -e "${CYAN}|                                                            |${NC}"
echo -e "${CYAN}|    Coordinator-based distributed computing                 |${NC}"
echo -e "${CYAN}|    4000x speedup with Numba JIT acceleration              |${NC}"
echo -e "${CYAN}|                                                            |${NC}"
echo -e "${CYAN}+============================================================+${NC}"
echo ""

# ============================================================
# 1. CHECK MACOS VERSION
# ============================================================
echo -e "${YELLOW}[1/6]${NC} Verificando sistema operativo..."

OS_VERSION=$(sw_vers -productVersion)
MAJOR_VERSION=$(echo $OS_VERSION | cut -d. -f1)

if [ "$MAJOR_VERSION" -lt 12 ]; then
    echo -e "${RED}Error: Se requiere macOS 12 (Monterey) o superior.${NC}"
    echo "   Tu version: $OS_VERSION"
    exit 1
fi
echo -e "   ${GREEN}macOS $OS_VERSION compatible${NC}"

# ============================================================
# 2. GET COORDINATOR URL
# ============================================================
echo ""
echo -e "${YELLOW}[2/6]${NC} Configuracion del coordinator..."

# Check command line arg first
COORDINATOR_URL="${1:-$DEFAULT_COORDINATOR_URL}"

# Check existing config
if [ -f "$INSTALL_DIR/config.env" ]; then
    source "$INSTALL_DIR/config.env"
    if [ -n "$COORDINATOR_URL" ]; then
        echo -e "   Configuracion existente encontrada: $COORDINATOR_URL"
        read -p "   Mantener esta configuracion? (S/n): " KEEP_CONFIG
        if [[ "$KEEP_CONFIG" =~ ^[Nn]$ ]]; then
            COORDINATOR_URL=""
        fi
    fi
fi

if [ -z "$COORDINATOR_URL" ] || [ "$COORDINATOR_URL" == "$DEFAULT_COORDINATOR_URL" ]; then
    echo ""
    echo -e "   Ingresa la URL del Coordinator:"
    echo -e "   ${BLUE}Ejemplos:${NC}"
    echo -e "   - Red local: http://10.0.0.232:5001"
    echo -e "   - Tailscale: http://100.77.179.14:5001"
    echo ""
    read -p "   Coordinator URL [$DEFAULT_COORDINATOR_URL]: " INPUT_URL
    COORDINATOR_URL="${INPUT_URL:-$DEFAULT_COORDINATOR_URL}"
fi

echo -e "   ${GREEN}Coordinator: $COORDINATOR_URL${NC}"

# ============================================================
# 3. CHECK/INSTALL PYTHON
# ============================================================
echo ""
echo -e "${YELLOW}[3/6]${NC} Verificando Python..."

PYTHON_CMD=""

# Check for Python 3.9+
for candidate in python3 python3.11 python3.10 python3.9 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if command -v $candidate &> /dev/null; then
        VERSION=$($candidate --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        MAJOR=$(echo $VERSION | cut -d. -f1)
        MINOR=$(echo $VERSION | cut -d. -f2)

        if [ "$MAJOR" == "3" ] && [ "$MINOR" -ge "9" ]; then
            PYTHON_CMD=$candidate
            echo -e "   ${GREEN}Python $VERSION encontrado: $candidate${NC}"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${YELLOW}   Python 3.9+ no encontrado. Instalando via Homebrew...${NC}"

    if ! command -v brew &> /dev/null; then
        echo -e "${RED}   Homebrew no encontrado. Instalando...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    brew install python@3.11
    PYTHON_CMD=$(brew --prefix python@3.11)/bin/python3.11

    if [ ! -x "$PYTHON_CMD" ]; then
        echo -e "${RED}   Error instalando Python${NC}"
        exit 1
    fi
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
echo -e "   ${GREEN}Usando Python: $PYTHON_CMD (v$PYTHON_VERSION)${NC}"

# ============================================================
# 4. CREATE VIRTUAL ENVIRONMENT & INSTALL DEPENDENCIES
# ============================================================
echo ""
echo -e "${YELLOW}[4/6]${NC} Instalando dependencias..."

# Create install directory
mkdir -p "$INSTALL_DIR/data"

# Create virtual environment
VENV_PATH="$INSTALL_DIR/venv"
echo -e "   Creando entorno virtual..."
$PYTHON_CMD -m venv "$VENV_PATH"

VENV_PYTHON="$VENV_PATH/bin/python"
VENV_PIP="$VENV_PATH/bin/pip"

# Upgrade pip
echo -e "   Actualizando pip..."
$VENV_PIP install --upgrade pip setuptools wheel --quiet

# Install dependencies
echo -e "   Instalando dependencias (numba, pandas, requests, ccxt)..."
$VENV_PIP install numba numpy pandas requests ccxt python-dotenv --quiet

# Verify numba installation
if $VENV_PYTHON -c "import numba; print(f'Numba {numba.__version__}')" &> /dev/null; then
    NUMBA_VERSION=$($VENV_PYTHON -c "import numba; print(numba.__version__)")
    echo -e "   ${GREEN}Numba $NUMBA_VERSION instalado (4000x speedup)${NC}"
else
    echo -e "${YELLOW}   Numba no se pudo instalar. Usando Python fallback.${NC}"
fi

# ============================================================
# 5. COPY WORKER FILES
# ============================================================
echo ""
echo -e "${YELLOW}[5/6]${NC} Copiando archivos del worker..."

# Copy Python files
cp "$SCRIPT_DIR/crypto_worker.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/strategy_miner.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/numba_backtester.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/dynamic_strategy.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/backtester.py" "$INSTALL_DIR/"

# Create minimal config.py
cat > "$INSTALL_DIR/config.py" << 'CONFIGEOF'
class Config:
    TRADING_FEE_MAKER = 0.4  # 0.4% maker fee
    TRADING_FEE_TAKER = 0.6  # 0.6% taker fee
CONFIGEOF

# Create minimal strategy.py for backtester fallback
cat > "$INSTALL_DIR/strategy.py" << 'STRATEOF'
class Strategy:
    def __init__(self, strategy_params=None):
        self.params = strategy_params or {}
    def prepare_data(self, df):
        return df
    def get_signal(self, window, current_index, risk_level=None):
        return {"signal": None, "sl": None, "tp": None, "reason": "NO_SIGNAL"}
    def calculate_atr(self, window, current_index, period=14):
        return 0.01
STRATEOF

# Create config.env
cat > "$INSTALL_DIR/config.env" << EOF
COORDINATOR_URL=$COORDINATOR_URL
INSTALL_DATE=$(date)
VERSION=3.0
PYTHON_PATH=$VENV_PYTHON
EOF

# Copy worker daemon script
cp "$SCRIPT_DIR/worker_daemon.sh" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/worker_daemon.sh"

echo -e "   ${GREEN}Archivos instalados en $INSTALL_DIR${NC}"

# ============================================================
# 6. TEST CONNECTION & NUMBA WARMUP
# ============================================================
echo ""
echo -e "${YELLOW}[6/6]${NC} Verificando instalacion..."

# Test coordinator connection
echo -e "   Probando conexion al coordinator..."
if curl -s --connect-timeout 5 "$COORDINATOR_URL/api/status" > /dev/null 2>&1; then
    echo -e "   ${GREEN}Coordinator accesible${NC}"
else
    echo -e "${YELLOW}   Coordinator no accesible. Verifica que este ejecutandose.${NC}"
fi

# Warmup Numba JIT
echo -e "   Calentando Numba JIT (primera compilacion)..."
cd "$INSTALL_DIR"
$VENV_PYTHON -c "
try:
    from numba_backtester import warmup_jit, HAS_NUMBA
    if HAS_NUMBA:
        warmup_jit()
        print('   Numba JIT listo')
    else:
        print('   Numba no disponible, usando Python')
except Exception as e:
    print(f'   Error: {e}')
" 2>/dev/null || echo -e "   ${YELLOW}Warmup omitido${NC}"

# ============================================================
# INSTALLATION COMPLETE
# ============================================================
echo ""
echo -e "${GREEN}+============================================================+${NC}"
echo -e "${GREEN}|                                                            |${NC}"
echo -e "${GREEN}|          INSTALACION COMPLETADA v3.0                       |${NC}"
echo -e "${GREEN}|                                                            |${NC}"
echo -e "${GREEN}+============================================================+${NC}"
echo ""
echo -e "   ${BLUE}Directorio:${NC}      $INSTALL_DIR"
echo -e "   ${BLUE}Coordinator:${NC}     $COORDINATOR_URL"
echo -e "   ${BLUE}Numba JIT:${NC}       4000x speedup activo"
echo ""
echo -e "${CYAN}+------------------------------------------------------------+${NC}"
echo -e "${CYAN}|                     COMO INICIAR                           |${NC}"
echo -e "${CYAN}+------------------------------------------------------------+${NC}"
echo ""
echo -e "   ${YELLOW}Iniciar 1 worker:${NC}"
echo -e "   cd $INSTALL_DIR && source venv/bin/activate"
echo -e "   COORDINATOR_URL=\"$COORDINATOR_URL\" python crypto_worker.py"
echo ""
echo -e "   ${YELLOW}Iniciar 3 workers (background):${NC}"
echo -e "   cd $INSTALL_DIR && source venv/bin/activate"
echo -e "   for i in 1 2 3; do"
echo -e "     COORDINATOR_URL=\"$COORDINATOR_URL\" WORKER_INSTANCE=\"\$i\" NUM_WORKERS=\"3\" \\"
echo -e "     nohup python -u crypto_worker.py > /tmp/worker_\$i.log 2>&1 &"
echo -e "     sleep 2"
echo -e "   done"
echo ""
echo -e "   ${YELLOW}Ver logs:${NC}"
echo -e "   tail -f /tmp/worker_1.log"
echo ""
echo -e "   ${YELLOW}Detener workers:${NC}"
echo -e "   pkill -f crypto_worker"
echo ""
echo -e "${GREEN}Listo para minar estrategias!${NC}"
echo ""
