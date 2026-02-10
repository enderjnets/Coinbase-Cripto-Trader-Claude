#!/bin/bash
#
# 🎁 Bittrader Worker Installer v2.3 (Sync Edition)
# One-click installer with auth key support and visual indicator
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
# Auth key expires: April 24, 2026 (90 days from Jan 24, 2026)
DEFAULT_AUTH_KEY="tskey-auth-kFntrJrZEn11CNTRL-f9Zr975c6idbbwyBMwUShdkztQ67myQb"
DEFAULT_HEAD_IP="100.118.215.73"  # MacBook Air (Head Node) Tailscale IP

# Command line args override defaults
ARG_AUTH_KEY="${1:-$DEFAULT_AUTH_KEY}"
ARG_HEAD_IP="${2:-$DEFAULT_HEAD_IP}"

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       🎁 BITTRADER WORKER INSTALLER v2.0                   ║${NC}"
echo -e "${BLUE}║       Únete al cluster de procesamiento distribuido        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# 1. CHECK MACOS VERSION
# ============================================================
echo -e "${YELLOW}[1/7]${NC} Verificando sistema operativo..."

OS_VERSION=$(sw_vers -productVersion)
MAJOR_VERSION=$(echo $OS_VERSION | cut -d. -f1)

if [ "$MAJOR_VERSION" -lt 12 ]; then
    echo -e "${RED}❌ Error: Se requiere macOS 12 (Monterey) o superior.${NC}"
    echo "   Tu versión: $OS_VERSION"
    exit 1
fi
echo -e "   ✅ macOS $OS_VERSION compatible"

# ============================================================
# 2. GET HEAD NODE IP (First, to determine if Tailscale needed)
# ============================================================
echo ""
echo -e "${YELLOW}[2/7]${NC} Configuración del cluster..."

# Check command line arg first
if [ -n "$ARG_HEAD_IP" ]; then
    HEAD_IP="$ARG_HEAD_IP"
    echo -e "   Head Node IP (from arg): $HEAD_IP"
# Then check existing config
elif [ -f "$INSTALL_DIR/config.env" ]; then
    source "$INSTALL_DIR/config.env"
    echo -e "   Configuración existente encontrada."
    echo -e "   Head Node IP: $HEAD_IP"
    read -p "   ¿Mantener esta configuración? (S/n): " KEEP_CONFIG
    if [[ "$KEEP_CONFIG" =~ ^[Nn]$ ]]; then
        HEAD_IP=""
    fi
fi

if [ -z "$HEAD_IP" ]; then
    echo ""
    echo -e "   Ingresa la IP del Head Node (la Mac principal del cluster)."
    echo -e "   • Para red local: usa la IP local (ej: 192.168.1.x)"
    echo -e "   • Para conexión remota: usa la IP de Tailscale (ej: 100.x.x.x)"
    echo ""
    read -p "   Head Node IP: " HEAD_IP
    
    if [ -z "$HEAD_IP" ]; then
        echo -e "${RED}   ❌ Error: Debes proporcionar la IP del Head Node.${NC}"
        exit 1
    fi
fi

# ============================================================
# 3. DETECT CONNECTION MODE (LAN vs WAN)
# ============================================================
echo ""
echo -e "${YELLOW}[3/7]${NC} Detectando modo de conexión..."

CONNECTION_MODE="unknown"

# Test if Head Node is reachable directly
echo -e "   Probando conexión directa a $HEAD_IP..."
if ping -c 1 -W 2 "$HEAD_IP" &> /dev/null; then
    echo -e "   ✅ Head Node alcanzable directamente"
    CONNECTION_MODE="lan"
else
    echo -e "   ⚠️ Head Node no alcanzable directamente"
    CONNECTION_MODE="wan"
fi

# If WAN mode, ensure Tailscale is set up
TAILSCALE_IP=""
if [ "$CONNECTION_MODE" == "wan" ]; then
    echo ""
    echo -e "   ${BLUE}Modo WAN detectado - Configurando Tailscale...${NC}"
    
    # Check if Tailscale is installed
    if ! command -v tailscale &> /dev/null; then
        echo -e "   Tailscale no encontrado. Instalando..."
        
        if command -v brew &> /dev/null; then
            brew install --cask tailscale
        else
            echo -e "${YELLOW}   ⚠️  Homebrew no encontrado.${NC}"
            echo ""
            echo "   Para conexiones remotas necesitas Tailscale."
            echo "   1. Instala desde: https://tailscale.com/download/mac"
            echo "   2. Ejecuta este script de nuevo"
            exit 1
        fi
    fi
    
    # Check if connected to Tailscale
    if ! tailscale status &> /dev/null; then
        # Need to connect with auth key
        AUTH_KEY="$ARG_AUTH_KEY"
        
        # Try embedded key first
        if [ -n "$AUTH_KEY" ]; then
            echo -e "   Conectando a Tailscale con key integrada..."
            if sudo tailscale up --authkey="$AUTH_KEY" --accept-routes 2>&1; then
                sleep 3
            else
                echo -e "${YELLOW}   ⚠️ La key integrada falló (posiblemente expirada).${NC}"
                AUTH_KEY=""
            fi
        fi
        
        # If no key or key failed, prompt for manual entry
        if [ -z "$AUTH_KEY" ] || ! tailscale status &> /dev/null; then
            echo ""
            echo -e "   ${YELLOW}La key integrada expiró o no funciona.${NC}"
            echo -e "   Ingresa una nueva Auth Key del administrador:"
            echo -e "   (Genera una nueva en: https://login.tailscale.com/admin/settings/keys)"
            echo ""
            read -p "   Nueva Auth Key: " NEW_AUTH_KEY
            
            if [ -z "$NEW_AUTH_KEY" ]; then
                echo -e "${RED}   ❌ Error: Se requiere Auth Key para conexión remota.${NC}"
                exit 1
            fi
            
            echo -e "   Conectando con nueva key..."
            sudo tailscale up --authkey="$NEW_AUTH_KEY" --accept-routes
            sleep 3
        fi
    fi
    
    if tailscale status &> /dev/null; then
        TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
        echo -e "   ✅ Conectado a Tailscale (IP: $TAILSCALE_IP)"
        
        # Re-test connection via Tailscale
        if ping -c 1 -W 2 "$HEAD_IP" &> /dev/null; then
            echo -e "   ✅ Head Node ahora alcanzable via Tailscale"
        else
            echo -e "${YELLOW}   ⚠️ Advertencia: Head Node aún no alcanzable. Verifica la IP.${NC}"
        fi
    else
        echo -e "${RED}   ❌ Error conectando a Tailscale.${NC}"
        exit 1
    fi
else
    echo -e "   ${GREEN}Modo LAN - Conexión directa (sin VPN necesario)${NC}"
    TAILSCALE_IP="N/A (LAN)"
fi

# ============================================================
# 5. CHECK/INSTALL PYTHON & RAY
# ============================================================
echo ""
echo -e "${YELLOW}[5/7]${NC} Verificando Python y Ray..."

# Check/Install Python 3.9 via Homebrew
# We use 3.9 specifically to MATCH the Head Node (MacBook Air)
echo -e "   Buscando Python 3.9..."

PYTHON_CMD=""
# Check standard Homebrew paths
if [ -f "/opt/homebrew/bin/python3.9" ]; then
    PYTHON_CMD="/opt/homebrew/bin/python3.9"
elif [ -f "/usr/local/bin/python3.9" ]; then
    PYTHON_CMD="/usr/local/bin/python3.9"
fi

# If not found, install it
if [ -z "$PYTHON_CMD" ]; then
    echo -e "   Python 3.9 no encontrado. Instalando via Homebrew (puede tardar)..."
    if ! command -v brew &> /dev/null; then
         # Install Homebrew if missing
         /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    brew install python@3.9
    
    # Re-detect
    if [ -f "/opt/homebrew/bin/python3.9" ]; then
        PYTHON_CMD="/opt/homebrew/bin/python3.9"
    elif [ -f "/usr/local/bin/python3.9" ]; then
        PYTHON_CMD="/usr/local/bin/python3.9"
    else
        # Fallback to whatever brew linked
        PYTHON_CMD=$(brew --prefix python@3.9)/bin/python3.9
    fi
fi

if [ ! -x "$PYTHON_CMD" ]; then
    echo -e "${RED}   ❌ Error: No se pudo instalar Python 3.9.${NC}"
    exit 1
fi

echo -e "   ✅ Usando Python: $PYTHON_CMD"

# Create Virtual Environment
VENV_DIR="$INSTALL_DIR/venv"
echo -e "   Creando entorno virtual en $VENV_DIR..."
rm -rf "$VENV_DIR" # Clean start
"$PYTHON_CMD" -m venv "$VENV_DIR"

# Install Ray in Venv
echo -e "   Instalando Ray y dependencias (esto puede tardar)..."
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel --quiet
"$VENV_DIR/bin/pip" install "grpcio==1.59.0" --quiet
"$VENV_DIR/bin/pip" install "ray[default]" "streamlit" "pandas" "ccxt" "plotly" "python-dotenv" "watchdog" "coinbase-advanced-py" "optuna" --quiet

# Verify Imports
if "$VENV_DIR/bin/python" -c "import ray; import optuna; import coinbase; print('Health Check Passed')" &> /dev/null; then
    echo -e "   ✅ Ray y dependencias instaladas y verificadas"
else
    echo -e "${RED}   ❌ Error: Falló la verificación de dependencias.${NC}"
    exit 1
fi

# ============================================================
# 6. INSTALL WORKER SCRIPTS
# ============================================================
echo ""
echo -e "${YELLOW}[6/7]${NC} Instalando scripts del worker..."

# Create install directory
mkdir -p "$INSTALL_DIR"

# Copy scripts
cp "$SCRIPT_DIR/worker_daemon.sh" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/smart_throttle.sh" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/status_indicator.sh" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/worker_daemon.sh"
chmod +x "$INSTALL_DIR/smart_throttle.sh"
chmod +x "$INSTALL_DIR/status_indicator.sh"

# Initialize with reduced CPUs (throttle enabled by default)
echo "2" > "$INSTALL_DIR/current_cpus"

# Save config
cat > "$INSTALL_DIR/config.env" << EOF
HEAD_IP=$HEAD_IP
TAILSCALE_IP=$TAILSCALE_IP
INSTALL_DATE=$(date)
THROTTLE_ENABLED=true
EOF

echo -e "   ✅ Scripts instalados en $INSTALL_DIR"

# ============================================================
# 7. REGISTER LAUNCHD AGENTS
# ============================================================
echo ""
echo -e "${YELLOW}[7/7]${NC} Configurando inicio automático..."

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENTS_DIR"

# Worker Daemon plist
cat > "$LAUNCH_AGENTS_DIR/com.bittrader.worker.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bittrader.worker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/worker_daemon.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/worker.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/worker_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER</key>
        <string>1</string>
    </dict>
</dict>
</plist>
EOF

# Throttle Monitor plist
cat > "$LAUNCH_AGENTS_DIR/com.bittrader.throttle.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bittrader.throttle</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/smart_throttle.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/throttle.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/throttle_error.log</string>
</dict>
</plist>
EOF

# Status Indicator plist
cat > "$LAUNCH_AGENTS_DIR/com.bittrader.status.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bittrader.status</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/status_indicator.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/status.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/status_error.log</string>
</dict>
</plist>
EOF

# Unload existing agents (if any)
launchctl unload "$LAUNCH_AGENTS_DIR/com.bittrader.worker.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.bittrader.throttle.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.bittrader.status.plist" 2>/dev/null || true

# Load new agents
launchctl load "$LAUNCH_AGENTS_DIR/com.bittrader.worker.plist"
launchctl load "$LAUNCH_AGENTS_DIR/com.bittrader.throttle.plist"
launchctl load "$LAUNCH_AGENTS_DIR/com.bittrader.status.plist"

echo -e "   ✅ Servicios registrados para inicio automático"

# ============================================================
# DONE!
# ============================================================
echo ""
# 8. DESKTOP SHORTCUT
echo ""
echo -e "${YELLOW}[8/8]${NC} Creando acceso directo..."
SHORTCUT="$HOME/Desktop/Bittrader Worker Status.command"
cat > "$SHORTCUT" << EOF
#!/bin/bash
echo "📊 Estado del Worker Bittrader"
echo "------------------------------"
echo "Para cerrar esta ventana, presiona Ctrl+C"
echo ""
tail -f "$INSTALL_DIR/worker.log"
EOF
chmod +x "$SHORTCUT"
echo -e "   ✅ Acceso directo creado: $SHORTCUT"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       ✅ INSTALACIÓN COMPLETADA                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "   Tu Mac ahora es parte del cluster de Bittrader."
echo ""
echo -e "   📡 Head Node: $HEAD_IP"
echo -e "   🔗 Tu IP: $TAILSCALE_IP"
echo ""
echo -e "   ${BLUE}Características activas:${NC}"
echo -e "   • ✅ Auto-conexión al iniciar sesión"
echo -e "   • ✅ Reconexión automática si se pierde"
echo -e "   • ✅ Throttling inteligente (menos CPU cuando usas la Mac)"
echo -e "   • ✅ Notificaciones de estado (recibirás alertas)"
echo ""
echo -e "   He puesto un monitor de estado en tu Escritorio:"
echo -e "   📊 Bittrader Worker Status"
echo ""
echo -e "   Para desinstalar: ./uninstall.sh"
echo ""

# Show initial notification
osascript -e 'display notification "Worker instalado y conectado correctamente" with title "Bittrader Worker" sound name "Glass"' 2>/dev/null || true
