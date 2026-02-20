#!/bin/bash
# 🧠 Bittrader Head Node Installer v4.0 - MacBook Pro Edition
# Configures MacBook Pro as stable Head Node with remote worker connectivity

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="$HOME/.bittrader_head"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🧠 BITTRADER HEAD NODE INSTALLER v4.0 - MACBOOK PRO     ║${NC}"
echo -e "${BLUE}║      Configuración optimizada para Head Node estable       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 1. PYTHON 3.9.6 CHECK (CRITICAL for Ray cluster compatibility)
echo -e "${YELLOW}[1/7]${NC} Verificando Python 3.9.6..."
echo -e "   (Python 3.9.6 es necesario para compatibilidad Ray con Workers)"

PYTHON_CMD=""
PYTHON_VERSION=""

# Check standard paths for Python 3.9.6 EXACTLY
for candidate in "/usr/local/bin/python3.9" "/Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9" "/opt/homebrew/bin/python3.9" "/usr/bin/python3.9"; do
    if [ -f "$candidate" ]; then
        VERSION=$("$candidate" --version 2>&1 | cut -d' ' -f2)
        if [ "$VERSION" == "3.9.6" ]; then
            PYTHON_CMD="$candidate"
            PYTHON_VERSION="$VERSION"
            echo -e "   ✅ Encontrado Python 3.9.6 en: $candidate"
            break
        fi
    fi
done

# If Python 3.9.6 not found, install it automatically
if [ -z "$PYTHON_CMD" ]; then
    echo -e "   Python 3.9.6 no encontrado. Descargando e instalando automáticamente..."
    echo -e "   (Esto puede tardar 2-3 minutos)"

    # Download Python 3.9.6 installer
    PYTHON_PKG="/tmp/python-3.9.6-macos11.pkg"
    echo -e "   Descargando Python 3.9.6 desde python.org..."

    if curl -L -o "$PYTHON_PKG" "https://www.python.org/ftp/python/3.9.6/python-3.9.6-macos11.pkg" 2>&1; then
        echo -e "   ✅ Descarga completada"

        # Install silently with sudo
        echo -e "   Instalando Python 3.9.6 (requiere permisos de administrador)..."
        echo -e "   Se te pedirá tu contraseña:"

        if sudo installer -pkg "$PYTHON_PKG" -target / 2>&1; then
            echo -e "   ✅ Python 3.9.6 instalado correctamente"
            rm -f "$PYTHON_PKG"

            # Find newly installed Python
            if [ -f "/usr/local/bin/python3.9" ]; then
                PYTHON_CMD="/usr/local/bin/python3.9"
            elif [ -f "/Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9" ]; then
                PYTHON_CMD="/Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9"
            fi

            PYTHON_VERSION=$("$PYTHON_CMD" --version 2>&1 | cut -d' ' -f2)
        else
            echo -e "${RED}   ❌ Error al instalar Python 3.9.6${NC}"
            rm -f "$PYTHON_PKG"
            exit 1
        fi
    else
        echo -e "${RED}   ❌ Error al descargar Python 3.9.6${NC}"
        echo -e "   Descarga manualmente desde:"
        echo -e "   https://www.python.org/ftp/python/3.9.6/python-3.9.6-macos11.pkg"
        exit 1
    fi
fi

# Final validation
if [ ! -x "$PYTHON_CMD" ]; then
    echo -e "${RED}   ❌ Error: No se pudo configurar Python 3.9.6${NC}"
    exit 1
fi

echo -e "   ✅ Usando Python: $PYTHON_CMD (v$PYTHON_VERSION)"

# Verify exact version match
if [ "$PYTHON_VERSION" != "3.9.6" ]; then
    echo -e "${RED}   ❌ ERROR: Se requiere Python 3.9.6 exacto${NC}"
    echo -e "   Encontrado: $PYTHON_VERSION"
    exit 1
fi

echo -e "   ✅ Versión verificada: Python 3.9.6 (compatible con Workers)"

# 2. TAILSCALE SETUP (MUST COME BEFORE VENV for config generation)
echo -e "${YELLOW}[2/7]${NC} Configurando Red (Tailscale)..."

if ! command -v tailscale &> /dev/null; then
    echo -e "   ⚠️ Tailscale no encontrado. Instalando..."
    if command -v brew &> /dev/null; then
        brew install --cask tailscale || echo "   (Si falla, instala manualmente desde https://tailscale.com)"
    else
        echo -e "   ⚠️ Homebrew no encontrado. No puedo instalar Tailscale automáticamente."
        echo -e "   👉 Por favor instala Tailscale manualmente: https://tailscale.com/download/mac"
    fi
fi

TAILSCALE_IP=""
if command -v tailscale &> /dev/null; then
    TS_IP=$(tailscale ip -4 2>/dev/null || echo "")
    if [ -n "$TS_IP" ]; then
        TAILSCALE_IP="$TS_IP"
        echo -e "   ✅ Tailscale activo: $TAILSCALE_IP"
    else
        echo -e "   ⚠️ Tailscale instalado pero NO conectado."
        echo -e "   🚀 Iniciando autenticación..."
        sudo tailscale up --accept-routes || echo "   (Error iniciando Tailscale. Configúralo manualmente)"

        # Try again after connecting
        TS_IP=$(tailscale ip -4 2>/dev/null || echo "")
        if [ -n "$TS_IP" ]; then
            TAILSCALE_IP="$TS_IP"
            echo -e "   ✅ Tailscale conectado: $TAILSCALE_IP"
        fi
    fi
else
    echo -e "   ❌ Tailscale no disponible. El acceso remoto no funcionará."
fi

# Verify Tailscale IP was obtained
if [ -z "$TAILSCALE_IP" ]; then
    echo -e "${RED}   ❌ ERROR: No se pudo obtener IP de Tailscale${NC}"
    echo -e "   El Head Node requiere Tailscale para acceso remoto del Worker."
    echo -e "   Por favor configura Tailscale manualmente y vuelve a ejecutar este script."
    exit 1
fi

# 3. DETECT CPU COUNT
echo -e "${YELLOW}[3/7]${NC} Detectando CPUs disponibles..."
TOTAL_CPUS=$(sysctl -n hw.ncpu)
echo -e "   ✅ Detectados $TOTAL_CPUS CPUs"

# 4. VENV CREATION
echo -e "${YELLOW}[4/7]${NC} Creando entorno seguro..."
mkdir -p "$INSTALL_DIR"
VENV_DIR="$INSTALL_DIR/venv"
rm -rf "$VENV_DIR"
"$PYTHON_CMD" -m venv "$VENV_DIR"
echo -e "   ✅ Venv creado en $INSTALL_DIR/venv"

# 5. DEPENDENCIES
echo -e "${YELLOW}[5/7]${NC} Instalando dependencias (esto puede tardar)..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install "ray[default]==2.51.2" "streamlit" "pandas" "ccxt" "plotly" "python-dotenv" "watchdog" "coinbase-advanced-py" "optuna" "urllib3==1.26.15" --quiet

# Verify Imports
if "$VENV_DIR/bin/python" -c "import ray; import optuna; import coinbase; print('Health Check Passed')" &> /dev/null; then
    echo -e "   ✅ Ray y dependencias instaladas y verificadas"
else
    echo -e "${RED}   ❌ Error: Falló la verificación de dependencias.${NC}"
    exit 1
fi

# 6. PROJECT FILES
echo -e "${YELLOW}[6/7]${NC} Configurando archivos del proyecto..."
PROJECT_DIR="$INSTALL_DIR/project"
mkdir -p "$PROJECT_DIR"

# Copy Launcher Scripts
rm -f "$PROJECT_DIR/start_cluster_head.py" "$PROJECT_DIR/start_head.sh"
cp -f "$SCRIPT_DIR/start_cluster_head.py" "$PROJECT_DIR/" 2>/dev/null || true
cp -f "$SCRIPT_DIR/start_head.sh" "$PROJECT_DIR/" 2>/dev/null || true

# Copy APPLICATION SOURCE CODE
# ----------------------------------------------------
# Check for internal 'src' folder (Standalone ZIP) vs Parent folder (Dev Environment)
if [ -d "$SCRIPT_DIR/src" ] && [ -f "$SCRIPT_DIR/src/interface.py" ]; then
    SOURCE_ROOT="$SCRIPT_DIR/src"
    echo -e "   📦 Instalando desde paquete incluído (Standalone)..."
else
    SOURCE_ROOT="$(dirname "$SCRIPT_DIR")"
    echo -e "   📂 Buscando en carpeta padre (Dev Mode)..."
fi

echo -e "   Copiando código fuente desde $SOURCE_ROOT..."

if [ -f "$SOURCE_ROOT/interface.py" ]; then
    # Copy Python files
    cp "$SOURCE_ROOT"/*.py "$PROJECT_DIR/" 2>/dev/null || true
    # Copy Requirements
    cp "$SOURCE_ROOT/requirements.txt" "$PROJECT_DIR/" 2>/dev/null || true
    # Copy Data folder
    # Data folder is special - prioritize what's in the Drive if we are in Dev Mode
    DATA_SRC=""
    if [ -d "$SCRIPT_DIR/src/data" ]; then
        DATA_SRC="$SCRIPT_DIR/src/data"
    elif [ -d "$(dirname "$SCRIPT_DIR")/data" ]; then
        DATA_SRC="$(dirname "$SCRIPT_DIR")/data"
    elif [ -d "$SOURCE_ROOT/data" ]; then
        DATA_SRC="$SOURCE_ROOT/data"
    fi

    if [ -n "$DATA_SRC" ]; then
        echo -e "   📦 Migrando carpeta de datos desde $DATA_SRC..."
        cp -r "$DATA_SRC" "$PROJECT_DIR/"
        echo -e "   ✅ Datos migrados correctamente."
    else
        echo -e "   ⚠️ No se encontró la carpeta 'data'. Si tienes datos previos, asegúrate de que existan en el Drive."
    fi
else
    echo -e "   ⚠️ No se encontró el código fuente en $SOURCE_ROOT."
    echo -e "   Asegúrate de ejecutar esto desde la carpeta de Google Drive."
fi

# Copy source files from installer package
cp "$SCRIPT_DIR/start_cluster_head.py" "$PROJECT_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/start_head.sh" "$PROJECT_DIR/" 2>/dev/null || true

# Make launcher executable
chmod +x "$PROJECT_DIR/start_head.sh" 2>/dev/null || true

echo -e "   ✅ Archivos copiados a $PROJECT_DIR"

# 7. SAVE CONFIGURATION
echo -e "${YELLOW}[7/7]${NC} Guardando configuración..."
CONFIG_FILE="$INSTALL_DIR/config.env"
cat > "$CONFIG_FILE" << EOF
# Bittrader Head Node Configuration
# Generated: $(date)

HEAD_IP=$TAILSCALE_IP
NUM_CPUS=$TOTAL_CPUS
PYTHON_VERSION=$PYTHON_VERSION
RAY_VERSION=2.51.2
INSTALL_DIR=$INSTALL_DIR
PROJECT_DIR=$PROJECT_DIR
VENV_DIR=$VENV_DIR
EOF

echo -e "   ✅ Configuración guardada en: $CONFIG_FILE"

# DONE
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            ✅ INSTALACIÓN COMPLETADA EXITOSAMENTE          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📊 CONFIGURACIÓN DEL HEAD NODE:${NC}"
echo -e "   • IP (Tailscale): ${GREEN}$TAILSCALE_IP${NC}"
echo -e "   • CPUs: ${GREEN}$TOTAL_CPUS${NC}"
echo -e "   • Python: ${GREEN}$PYTHON_VERSION${NC}"
echo -e "   • Ray: ${GREEN}2.51.2${NC}"
echo ""
echo -e "${BLUE}🚀 PARA INICIAR EL HEAD NODE:${NC}"
echo -e "   cd \"$INSTALL_DIR/project\""
echo -e "   $VENV_DIR/bin/ray start --head \\"
echo -e "     --port=6379 \\"
echo -e "     --node-ip-address=$TAILSCALE_IP \\"
echo -e "     --include-dashboard=false \\"
echo -e "     --num-cpus=$TOTAL_CPUS"
echo ""
echo -e "${BLUE}📡 INSTRUCCIONES PARA CONECTAR WORKER (MacBook Air):${NC}"
echo -e "   1. En MacBook Air, ejecuta el instalador del Worker"
echo -e "   2. Cuando te pida la IP del Head, ingresa: ${GREEN}$TAILSCALE_IP${NC}"
echo -e "   3. El Worker se conectará automáticamente"
echo ""
echo -e "${YELLOW}💡 TIP: Guarda esta IP para configurar el Worker: ${GREEN}$TAILSCALE_IP${NC}"
echo ""
echo -e "Configuración guardada en: ${GREEN}$CONFIG_FILE${NC}"
echo ""
