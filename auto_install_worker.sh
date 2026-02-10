#!/bin/bash
################################################################################
# 🧬 AUTO-INSTALLER WORKER - SISTEMA DE TRADING DISTRIBUIDO
# Instalador autónomo para Mac, Linux y Windows (WSL)
#
# Este script configura TODO automáticamente:
# - Detecta el sistema operativo
# - Instala dependencias
# - Clona/actualiza el proyecto
# - Configura workers según CPUs disponibles
# - Configura auto-arranque al reiniciar
# - Conecta automáticamente al coordinator
#
# Uso: curl -sSL https://raw.githubusercontent.com/.../auto_install_worker.sh | bash
# O: wget -qO- https://.../auto_install_worker.sh | bash
################################################################################

set -e

# ════════════════════════════════════════════════════════════════════════════════════
# COLORS
# ════════════════════════════════════════════════════════════════════════════════════
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════════════
REPO_URL="https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git"
COORDINATOR_URL="${COORDINATOR_URL:-http://100.77.179.14:5001}"
PROJECT_DIR="$HOME/Coinbase-Cripto-Trader-Claude"
WORKER_DIR="$HOME/.crypto_worker"
LOG_FILE="$WORKER_DIR/install.log"

# ════════════════════════════════════════════════════════════════════════════════════
# FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════════

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$msg"
    echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
}

log_color() {
    echo -e "${2}$1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE" 2>/dev/null || true
}

detect_os() {
    log "🔍 Detectando sistema operativo..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="macos"
        OS_NAME="macOS"
    elif [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "linux"* ]]; then
        # Check if WSL
        if grep -q Microsoft /proc/version 2>/dev/null || grep -q microsoft /proc/version 2>/dev/null; then
            OS_TYPE="wsl"
            OS_NAME="WSL (Windows Subsystem for Linux)"
        else
            OS_TYPE="linux"
            OS_NAME="Linux"
        fi
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS_TYPE="windows"
        OS_NAME="Windows"
    else
        OS_TYPE="unknown"
        OS_NAME="Desconocido"
    fi
    
    log_color "✅ Sistema: $OS_NAME ($OS_TYPE)" "$GREEN"
}

detect_cpu_cores() {
    log "🔍 Detectando CPUs..."
    
    if [[ "$OS_TYPE" == "macos" ]]; then
        CPU_CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
    else
        CPU_CORES=$(nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo 4)
    fi
    
    # Reserve 1-2 cores for system, use rest for workers
    WORKERS_COUNT=$((CPU_CORES - 2))
    [[ $WORKERS_COUNT -lt 1 ]] && WORKERS_COUNT=1
    
    log_color "✅ CPU cores: $CPU_CORES - Workers a iniciar: $WORKERS_COUNT" "$GREEN"
}

setup_directories() {
    log "📁 Creando directorios..."
    mkdir -p "$WORKER_DIR"
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    log "✅ Directorios creados"
}

install_dependencies() {
    log "📦 Instalando dependencias..."
    
    if [[ "$OS_TYPE" == "macos" ]]; then
        # Check if Homebrew is installed
        if ! command -v brew &> /dev/null; then
            log_color "⚠️  Homebrew no encontrado. Instalando..." "$YELLOW"
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        # Install Python if not available
        if ! command -v python3 &> /dev/null; then
            log_color "📦 Instalando Python via Homebrew..." "$YELLOW"
            brew install python3 git curl
        fi
    
    elif [[ "$OS_TYPE" == "linux" ]] || [[ "$OS_TYPE" == "wsl" ]]; then
        # Update package list
        sudo apt-get update -qq 2>/dev/null || apt-get update -qq 2>/dev/null || true
        
        # Install Python and git
        sudo apt-get install -y python3 python3-pip git curl 2>/dev/null || \
        apt-get install -y python3 python3-pip git curl 2>/dev/null || true
    
    elif [[ "$OS_TYPE" == "windows" ]]; then
        log_color "ℹ️  Para Windows, usa el instalador .exe o el script batch" "$CYAN"
        return 0
    fi
    
    log_color "✅ Dependencias instaladas" "$GREEN"
}

clone_or_update_project() {
    log "📥 Configurando proyecto..."
    
    if [ -d "$PROJECT_DIR/.git" ]; then
        log "📥 Proyecto ya existe, actualizando..."
        cd "$PROJECT_DIR"
        git pull origin main --quiet 2>/dev/null || git pull origin main 2>/dev/null || true
    else
        log "📥 Clonando proyecto..."
        git clone "$REPO_URL" "$PROJECT_DIR"
        cd "$PROJECT_DIR"
    fi
    
    log_color "✅ Proyecto en: $PROJECT_DIR" "$GREEN"
}

install_python_deps() {
    log "🐍 Instalando dependencias Python..."
    
    cd "$PROJECT_DIR"
    
    # Upgrade pip first
    python3 -m pip install --upgrade pip --quiet 2>/dev/null || true
    
    # Install required packages
    python3 -m pip install requests pandas numpy --quiet 2>/dev/null || \
    python3 -m pip install requests pandas numpy 2>/dev/null || \
    pip3 install requests pandas numpy --quiet 2>/dev/null || true
    
    log_color "✅ Dependencias Python listas" "$GREEN"
}

configure_worker_env() {
    log "⚙️  Configurando entorno worker..."
    
    # Create environment file
    cat > "$WORKER_DIR/worker.env" << EOF
COORDINATOR_URL=$COORDINATOR_URL
PROJECT_DIR=$PROJECT_DIR
WORKER_DIR=$WORKER_DIR
OS_TYPE=$OS_TYPE
CPU_CORES=$CPU_CORES
WORKERS_COUNT=$WORKERS_COUNT
EOF
    
    log_color "✅ Entorno configurado" "$GREEN"
}

create_startup_script() {
    log "🚀 Creando script de inicio..."
    
    cat > "$WORKER_DIR/start_workers.sh" << 'SCRIPT'
#!/bin/bash
################################################################################
# SCRIPT DE INICIO DE WORKERS
# Auto-generado por auto_install_worker.sh
################################################################################

set -e

# Load environment
source "$HOME/.crypto_worker/worker.env"

# Navigate to project
cd "$PROJECT_DIR"

# Kill existing workers
pkill -f "crypto_worker.py" 2>/dev/null || true
sleep 2

# Start workers
COORD_URL="$COORDINATOR_URL"

for i in $(seq 1 $WORKERS_COUNT); do
    WORKER_INSTANCE=$i nohup python3 "$PROJECT_DIR/crypto_worker.py" $COORD_URL > "$WORKER_DIR/worker_$i.log" 2>&1 &
    echo "Worker $i iniciado"
done

echo ""
echo "Workers iniciados: $WORKERS_COUNT"
SCRIPT
    
    chmod +x "$WORKER_DIR/start_workers.sh"
    log_color "✅ Script de inicio creado" "$GREEN"
}

setup_auto_start() {
    log "⏰ Configurando auto-arranque..."
    
    if [[ "$OS_TYPE" == "macos" ]]; then
        # Create LaunchAgent
        mkdir -p "$HOME/Library/LaunchAgents"
        
        cat > "$HOME/Library/LaunchAgents/com.crypto.worker.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.crypto.worker</string>
    <key>ProgramArguments</key>
    <array>
        <string>$WORKER_DIR/start_workers.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$WORKER_DIR/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>$WORKER_DIR/launchd_error.log</string>
</dict>
</plist>
EOF
        
        # Load the LaunchAgent
        launchctl load "$HOME/Library/LaunchAgents/com.crypto.worker.plist" 2>/dev/null || true
        
        log_color "✅ Auto-arranque configurado (macOS LaunchAgent)" "$GREEN"
    
    elif [[ "$OS_TYPE" == "linux" ]] || [[ "$OS_TYPE" == "wsl" ]]; then
        # Create systemd user service
        mkdir -p "$HOME/.config/systemd/user"
        
        cat > "$HOME/.config/systemd/user/crypto-worker.service" << EOF
[Unit]
Description=Crypto Trading Worker
After=network.target

[Service]
Type=simple
ExecStart=%h/.crypto_worker/start_workers.sh
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
        
        # Enable and start
        systemctl --user daemon-reload 2>/dev/null || true
        systemctl --user enable crypto-worker 2>/dev/null || true
        systemctl --user start crypto-worker 2>/dev/null || true
        
        log_color "✅ Auto-arranque configurado (systemd)" "$GREEN"
    
    elif [[ "$OS_TYPE" == "windows" ]]; then
        log_color "ℹ️  Para Windows, usa el script batch con tareas programadas" "$CYAN"
    fi
}

start_workers() {
    log "🚀 Iniciando workers..."
    
    cd "$PROJECT_DIR"
    
    # Kill existing workers
    pkill -f "crypto_worker.py" 2>/dev/null || true
    sleep 2
    
    # Start new workers
    COORD_URL="$COORDINATOR_URL"
    
    for i in $(seq 1 $WORKERS_COUNT); do
        WORKER_INSTANCE=$i nohup python3 "$PROJECT_DIR/crypto_worker.py" $COORD_URL > "$WORKER_DIR/worker_$i.log" 2>&1 &
        echo -ne "Worker $i iniciado...\r"
        sleep 0.5
    done
    
    sleep 3
    
    # Verify workers
    WORKERS_RUNNING=$(ps aux | grep "crypto_worker.py" | grep -v grep | wc -l)
    log_color "✅ Workers iniciados: $WORKERS_RUNNING / $WORKERS_COUNT" "$GREEN"
}

verify_installation() {
    log "🔍 Verificando instalación..."
    
    sleep 3
    
    # Check coordinator connection
    if curl -s --max-time 10 "$COORDINATOR_URL/api/status" > /dev/null 2>&1; then
        STATUS=$(curl -s "$COORDINATOR_URL/api/status")
        WORKERS_ACTIVE=$(echo $STATUS | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('workers',{}).get('active','0'))" 2>/dev/null || echo "0")
        log_color "✅ Coordinator accesible - Workers activos: $WORKERS_ACTIVE" "$GREEN"
    else
        log_color "⚠️  Coordinator no accesible (puede que aún no esté listo)" "$YELLOW"
    fi
    
    # Check local workers
    WORKERS_RUNNING=$(ps aux | grep "crypto_worker.py" | grep -v grep | wc -l)
    log_color "✅ Workers locales ejecutándose: $WORKERS_RUNNING" "$GREEN"
}

print_summary() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              ✅ INSTALACIÓN COMPLETADA                          ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "📊 ${CYAN}RESUMEN:${NC}"
    echo ""
    echo -e "   💻 Sistema: $OS_NAME"
    echo -e "   🔧 CPUs disponibles: $CPU_CORES"
    echo -e "   👥 Workers iniciados: $WORKERS_COUNT"
    echo -e "   📡 Coordinator: $COORDINATOR_URL"
    echo -e "   📁 Proyecto: $PROJECT_DIR"
    echo -e "   📁 Logs: $WORKER_DIR/worker_*.log"
    echo ""
    echo -e "🔗 ${CYAN}COMANDOS ÚTILES:${NC}"
    echo ""
    echo -e "   Ver workers:   ps aux | grep crypto_worker"
    echo -e "   Ver logs:      tail -f $WORKER_DIR/worker_1.log"
    echo -e "   Reiniciar:     $WORKER_DIR/start_workers.sh"
    echo -e "   Ver status:    curl $COORDINATOR_URL/api/status"
    echo ""
    echo -e "📂 ${CYAN}ARCHIVOS:${NC}"
    echo ""
    echo -e "   $WORKER_DIR/worker.env      - Configuración"
    echo -e "   $WORKER_DIR/start_workers.sh - Script de inicio"
    echo -e "   $WORKER_DIR/install.log    - Log de instalación"
    echo ""
    
    # Get hostname for SSH access
    HOSTNAME=$(hostname 2>/dev/null || echo "tu-maquina")
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "IP-LOCAL")
    
    echo -e "🌐 ${CYAN}ACCESO REMOTO:${NC}"
    echo ""
    echo -e "   Para acceder remotamente:"
    echo -e "   ssh enderj@$LOCAL_IP"
    echo ""
}

# ════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════════════

main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     🧬 AUTO-INSTALLER WORKER - SISTEMA DE TRADING               ║${NC}"
    echo -e "${BLUE}║                                                                   ║${NC}"
    echo -e "${BLUE}║     Instalador autónomo para Mac, Linux y Windows                 ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Initialize log
    mkdir -p "$WORKER_DIR"
    echo "# Install log - $(date)" > "$LOG_FILE"
    
    # Run installation steps
    detect_os
    detect_cpu_cores
    setup_directories
    install_dependencies
    clone_or_update_project
    install_python_deps
    configure_worker_env
    create_startup_script
    setup_auto_start
    start_workers
    verify_installation
    print_summary
}

# ════════════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════════

# Allow overriding coordinator URL
COORDINATOR_URL="${1:-$COORDINATOR_URL}"

# Run main
main "$@"
