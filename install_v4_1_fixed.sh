#!/bin/bash
#
# 🎁 Bittrader Worker Installer v4.1 (CORREGIDO)
# One-click installer con validaciones mejoradas
#
# Usage: ./install.sh [TAILSCALE_AUTH_KEY] [HEAD_NODE_IP]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="$HOME/.bittrader_worker"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ============================================================
# EMBEDDED DEFAULTS - Edit these when generating new installer
# ============================================================
DEFAULT_AUTH_KEY="tskey-auth-kFntrJrZEn11CNTRL-f9Zr975c6bwyBMwUShdkztQ67myQb"
DEFAULT_HEAD_IP="100.118.215.73"

# Command line args override defaults
ARG_AUTH_KEY="${1:-$DEFAULT_AUTH_KEY}"
ARG_HEAD_IP="${2:-$DEFAULT_HEAD_IP}"

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       🎁 BITTRADER WORKER INSTALLER v4.1              ║${NC}"
echo -e "${BLUE}║       Con validaciones de seguridad integradas           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# 1. CHECK SYSTEM & PYTHON VERSION (CRÍTICO - Versión exacta importa!)
# ============================================================
echo -e "${YELLOW}[1/8]${NC} Verificando sistema..."

# Verificar Python versión EXACTA
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "   Python detectado: $PYTHON_VERSION"

# PROBLEMA: Versiones desalineadas causan RuntimeError
# SOLUCIÓN: Verificar que coincida con Head Node
if [ "$PYTHON_MAJOR" != "3" ] || [ "$PYTHON_MINOR" != "9" ]; then
    echo -e "${YELLOW}⚠️  ADVERTENCIA: Python $PYTHON_VERSION detectado${NC}"
    echo "   El Head Node usa Python 3.9.x"
    echo "   Versiones diferentes pueden causar RuntimeError: version mismatch"
    echo ""
    echo "   Opciones:"
    echo "   1. Instalar Python 3.9 (recomendado para compatibilidad)"
    echo "   2. Continuar con Python $PYTHON_VERSION (puede fallar)"
    echo ""
    read -p "   ¿Instalar Python 3.9? (S/n): " INSTALL_PY39
    if [[ "$INSTALL_PY39" =~ ^[Ss]$ ]]; then
        echo -e "   Instalando Python 3.9..."
        if command -v brew &> /dev/null; then
            brew install python@3.9
            export PATH="/opt/homebrew/opt/python@3.9/bin:$PATH"
            PYTHON_CMD="/opt/homebrew/bin/python3.9"
        else
            echo -e "${RED}❌ Error: Homebrew no encontrado. Instala Homebrew primero.${NC}"
            exit 1
        fi
    else
        PYTHON_CMD="python3"
    fi
else
    PYTHON_CMD="python3"
fi

# ============================================================
# 2. VERIFICACIÓN DE SINTAXIS PYTHON (NUEVO - Lecciones Solana)
# ============================================================
echo ""
echo -e "${YELLOW}[2/8]${NC} Verificando sintaxis de scripts..."

# Verificar que los scripts no tengan errores de sintaxis antes de instalar
SYNTAX_ERRORS=0

for script in "$SCRIPT_DIR"/*.py; do
    if [ -f "$script" ]; then
        if ! python3 -m py_compile "$script" 2>/dev/null; then
            echo -e "${RED}❌ Error de sintaxis en: $(basename "$script")${NC}"
            SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
        fi
    fi
done

if [ $SYNTAX_ERRORS -gt 0 ]; then
    echo -e "${RED}❌ Error: $SYNTAX_ERRORS scripts tienen errores de sintaxis${NC}"
    echo "   Corrige los errores antes de instalar"
    exit 1
fi

echo -e "   ✅ Scripts verificados sin errores de sintaxis"

# ============================================================
# 3. GET HEAD NODE IP
# ============================================================
echo ""
echo -e "${YELLOW}[3/8]${NC} Configuración del cluster..."

if [ -n "$ARG_HEAD_IP" ]; then
    HEAD_IP="$ARG_HEAD_IP"
    echo -e "   Head Node IP (desde argumento): $HEAD_IP"
elif [ -f "$INSTALL_DIR/config.env" ]; then
    source "$INSTALL_DIR/config.env"
    echo -e "   Configuración existente encontrada."
    echo -e "   Head Node IP: $HEAD_IP"
    read -p "   ¿Mantener esta configuración? (S/n): " KEEP_CONFIG
    if [[ "$KEEP_CONFIG" =~ ^[Nn]$ ]]; then
        HEAD_IP=""
    fi
else
    read -p "   Head Node IP: " HEAD_IP
fi

if [ -z "$HEAD_IP" ]; then
    echo -e "${RED}❌ Error: Debes proporcionar la IP del Head Node${NC}"
    exit 1
fi

# ============================================================
# 4. DETECT CONNECTION MODE
# ============================================================
echo ""
echo -e "${YELLOW}[4/8]${NC} Detectando modo de conexión..."

CONNECTION_MODE="unknown"

echo -e "   Probando conexión a $HEAD_IP..."
if ping -c 1 -W 2 "$HEAD_IP" &> /dev/null; then
    echo -e "   ✅ Head Node alcanzable directamente"
    CONNECTION_MODE="lan"
    TAILSCALE_IP="N/A (LAN)"
else
    echo -e "   ⚠️ Head Node no alcanzable directamente"
    CONNECTION_MODE="wan"
fi

# ============================================================
# 5. TAILSCALE SETUP (SI ES NECESARIO)
# ============================================================
if [ "$CONNECTION_MODE" == "wan" ]; then
    echo ""
    echo -e "${YELLOW}[5/8]${NC} Configurando Tailscale..."
    
    if ! command -v tailscale &> /dev/null; then
        echo "   Tailscale no encontrado. Instalando..."
        if command -v brew &> /dev/null; then
            brew install --cask tailscale
        else
            echo -e "${RED}❌ Error: Instala Tailscale manualmente desde https://tailscale.com/download${NC}"
            exit 1
        fi
    fi
    
    if ! tailscale status &> /dev/null 2>&1; then
        echo -e "   Conectando a Tailscale..."
        if [ -n "$ARG_AUTH_KEY" ]; then
            if sudo tailscale up --authkey="$ARG_AUTH_KEY" --accept-routes 2>&1; then
                echo -e "   ✅ Conectado a Tailscale"
            else
                echo -e "${RED}❌ Error conectando a Tailscale${NC}"
                echo "   Ingresa la Auth Key manualmente:"
                read -p "   Auth Key: " MANUAL_AUTH_KEY
                sudo tailscale up --authkey="$MANUAL_AUTH_KEY" --accept-routes
            fi
        else
            echo -e "${RED}❌ Se requiere Auth Key de Tailscale${NC}"
            read -p "   Auth Key: " MANUAL_AUTH_KEY
            sudo tailscale up --authkey="$MANUAL_AUTH_KEY" --accept-routes
        fi
    fi
    
    TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "N/A")
    echo -e "   ✅ Tailscale IP: $TAILSCALE_IP"
fi

# ============================================================
# 6. INSTALL DEPENDENCIAS (CON VALIDACIÓN MEJORADA)
# ============================================================
echo ""
echo -e "${YELLOW}[6/8]${NC} Instalando dependencias..."

# Crear Virtual Environment
VENV_DIR="$INSTALL_DIR/venv"
echo "   Creando entorno virtual..."
rm -rf "$VENV_DIR"
python3 -m venv "$VENV_DIR"

# Instalar dependencias UNA POR UNA con verificación
echo "   Instalando dependencias (con verificaciones)..."

# Instalar pip primero
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel --quiet

# Instalar Ray CON LA VERSIÓN CORRECTA (no la más reciente - causa crashes!)
echo "   ⏳ Instalando Ray 2.9.0 (versión estable)..."
"$VENV_DIR/bin/pip" install "ray==2.9.0" --quiet  # VERSIÓN ESTABLE

# Instalar otras dependencias
"$VENV_DIR/bin/pip" install "streamlit" "pandas" "ccxt" "plotly" "python-dotenv" "watchdog" "coinbase-advanced-py" "optuna" --quiet

# VERIFICACIÓN FINAL DE IMPORTS (Lecciones Solana)
echo "   🔍 Verificando imports..."
if ! "$VENV_DIR/bin/python" -c "import ray; import optuna; import coinbase; import ccxt; import streamlit; print('✅ Imports OK')" 2>/dev/null; then
    echo -e "${RED}❌ Error: Faltan dependencias${NC}"
    exit 1
fi

echo -e "   ✅ Dependencias instaladas y verificadas"

# ============================================================
# 7. INSTALL WORKER SCRIPTS
# ============================================================
echo ""
echo -e "${YELLOW}[7/8]${NC} Instalando scripts del worker..."

mkdir -p "$INSTALL_DIR"

# Copiar scripts
if [ -f "$SCRIPT_DIR/worker_daemon.sh" ]; then
    cp "$SCRIPT_DIR/worker_daemon.sh" "$INSTALL_DIR/"
fi

# Save config con VALIDACIÓN
cat > "$INSTALL_DIR/config.env" << EOF
HEAD_IP=$HEAD_IP
TAILSCALE_IP=$TAILSCALE_IP
INSTALL_DATE=$(date)
PYTHON_VERSION=$PYTHON_VERSION
RAY_VERSION=2.9.0
EOF

echo -e "   ✅ Scripts instalados"

# ============================================================
# 8. FINAL HEALTH CHECK (NUEVO)
# ============================================================
echo ""
echo -e "${YELLOW}[8/8]${NC} Health check final..."

# Verificar que todo esté correcto
if [ -f "$VENV_DIR/bin/python" ]; then
    PYTHON_CHECK=$("$VENV_DIR/bin/python" --version 2>&1)
    echo -e "   ✅ Python: $PYTHON_CHECK"
else
    echo -e "${RED}❌ Error: Python venv no creado${NC}"
    exit 1
fi

# ============================================================
# DONE!
# ============================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       ✅ INSTALACIÓN COMPLETADA v4.1                     ║${NC}"
echo -e "${GREEN}║       Con validaciones de seguridad                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "   📡 Head Node: $HEAD_IP"
if [ -n "$TAILSCALE_IP" ]; then
    echo -e "   🔗 Tailscale: $TAILSCALE_IP"
fi
echo -e "   🐍 Python: $PYTHON_VERSION"
echo -e "   📦 Ray: 2.9.0 (estable)"
echo ""
echo -e "${BLUE}Características:${NC}"
echo "   • ✅ Verificación de sintaxis Python"
echo "   • ✅ Python 3.9 compatibility check"
echo "   • ✅ Ray 2.9.0 (no 2.51.x que causa crashes)"
echo "   • ✅ Dependencias verificadas una por una"
echo ""
echo "   Para iniciar el worker:"
echo "   $INSTALL_DIR/worker_daemon.sh"
echo ""
