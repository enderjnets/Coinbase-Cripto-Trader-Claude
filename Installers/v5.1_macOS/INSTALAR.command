#!/bin/bash
# ============================================================================
#  BITTRADER WORKER - Instalador Automatico v5.1 - macOS
#  Haz doble clic en este archivo desde Finder para instalar.
#  Compatible con Apple Silicon (M1/M2/M3) e Intel.
# ============================================================================

# Colores
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

clear
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        BITTRADER WORKER INSTALLER v5.1 - macOS          ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

WORK_DIR="$HOME/crypto_worker"
GITHUB_RAW="https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main"
LAN_URL="http://10.0.0.232:5001"
WAN_URL="http://100.77.179.14:5001"

# ── 1. Auto-detectar red (LAN vs WAN/Tailscale) ────────────────────────────
echo -e "${BLUE}[1/7] Detectando red...${NC}"
if curl -s --max-time 2 "$LAN_URL/api/status" > /dev/null 2>&1; then
    COORDINATOR_URL="$LAN_URL"
    echo -e "  ${GREEN}✓ Red local detectada → $COORDINATOR_URL${NC}"
else
    COORDINATOR_URL="$WAN_URL"
    echo -e "  ${YELLOW}→ Red externa (Tailscale) → $COORDINATOR_URL${NC}"
fi

# ── 2. Auto-detectar CPUs óptimos ──────────────────────────────────────────
TOTAL_CPUS=$(sysctl -n hw.logicalcpu 2>/dev/null || echo 4)
if [ "$TOTAL_CPUS" -le 2 ]; then
    NUM_WORKERS=1
elif [ "$TOTAL_CPUS" -le 4 ]; then
    NUM_WORKERS=$((TOTAL_CPUS - 1))
else
    NUM_WORKERS=$((TOTAL_CPUS - 2))
fi
echo -e "${BLUE}[2/7] CPUs detectados: ${TOTAL_CPUS} → Lanzando ${NUM_WORKERS} workers${NC}"

# ── 3. Crear directorio de trabajo ─────────────────────────────────────────
echo -e "${BLUE}[3/7] Preparando directorio $WORK_DIR ...${NC}"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# ── 4. Descargar archivos desde GitHub ─────────────────────────────────────
echo -e "${BLUE}[4/7] Descargando archivos desde GitHub...${NC}"
FILES=(crypto_worker.py numba_backtester.py backtester.py dynamic_strategy.py strategy_miner.py)
for f in "${FILES[@]}"; do
    printf "  Descargando %-30s " "$f..."
    if curl -fsSL "$GITHUB_RAW/$f" -o "$f" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Error al descargar $f${NC}"
        echo "  Verifica tu conexión a internet."
        read -p "Presiona Enter para salir..."
        exit 1
    fi
done

# ── 5. Instalar Python y dependencias ──────────────────────────────────────
echo -e "${BLUE}[5/7] Instalando dependencias...${NC}"

# Instalar Homebrew si no existe
if ! command -v brew &>/dev/null; then
    echo "  Instalando Homebrew (requiere contraseña)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Agregar brew al PATH para Apple Silicon
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
    fi
fi

# Instalar Python 3.11 si no hay Python 3
if ! command -v python3 &>/dev/null; then
    echo "  Instalando Python 3.11..."
    brew install python@3.11
fi

# Crear entorno virtual
if [ ! -d "venv" ]; then
    echo "  Creando entorno virtual..."
    python3 -m venv venv
fi
source venv/bin/activate

echo "  Instalando paquetes Python..."
pip install --upgrade pip -q
pip install requests numpy numba pandas -q

# Verificar Numba
python3 -c "import numba; print(f'  ✓ Numba {numba.__version__} instalado')"

# ── 6. Crear scripts auxiliares ────────────────────────────────────────────
echo -e "${BLUE}[6/7] Creando scripts...${NC}"

# Guardar config
cat > config.env << EOF
COORDINATOR_URL=$COORDINATOR_URL
NUM_WORKERS=$NUM_WORKERS
USE_RAY=false
PYTHONUNBUFFERED=1
INSTALLER_VERSION=5.1
EOF

# Script de inicio
cat > start_workers.sh << 'STARTEOF'
#!/bin/bash
cd "$HOME/crypto_worker"
source venv/bin/activate
source config.env

echo "Iniciando $NUM_WORKERS workers → $COORDINATOR_URL"
for i in $(seq 1 $NUM_WORKERS); do
    COORDINATOR_URL="$COORDINATOR_URL" WORKER_INSTANCE="$i" USE_RAY="false" \
    PYTHONUNBUFFERED=1 nohup python3 -u crypto_worker.py >> logs/worker_$i.log 2>&1 &
    echo "  Worker $i (PID $!)"
    sleep 1
done
echo ""
echo "✅ $NUM_WORKERS workers iniciados. Logs: ~/crypto_worker/logs/"
STARTEOF

# Script de parada
cat > stop_workers.sh << 'STOPEOF'
#!/bin/bash
COUNT=$(pgrep -f crypto_worker.py | wc -l | tr -d ' ')
pkill -f crypto_worker.py 2>/dev/null
echo "✅ $COUNT workers detenidos"
STOPEOF

# Script de estado
cat > status.sh << 'STATEOF'
#!/bin/bash
source "$HOME/crypto_worker/config.env"
COUNT=$(pgrep -f crypto_worker.py | wc -l | tr -d ' ')
echo "══════════════════════════════"
echo "  BITTRADER WORKER STATUS"
echo "══════════════════════════════"
echo "  Workers activos : $COUNT / $NUM_WORKERS"
echo "  Coordinator     : $COORDINATOR_URL"
echo ""
echo "  Últimos resultados:"
for i in $(seq 1 $NUM_WORKERS); do
    LOG="$HOME/crypto_worker/logs/worker_$i.log"
    if [ -f "$LOG" ]; then
        LAST=$(tail -1 "$LOG" 2>/dev/null)
        echo "  W$i: $LAST"
    fi
done
STATEOF

# Script de actualización
cat > update.sh << 'UPDATEEOF'
#!/bin/bash
cd "$HOME/crypto_worker"
echo "Actualizando archivos desde GitHub..."
GITHUB_RAW="https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main"
for f in crypto_worker.py numba_backtester.py backtester.py dynamic_strategy.py strategy_miner.py; do
    curl -fsSL "$GITHUB_RAW/$f" -o "$f" && echo "  ✓ $f" || echo "  ✗ Error: $f"
done
echo "✅ Actualización completada. Reinicia los workers."
UPDATEEOF

mkdir -p logs
chmod +x start_workers.sh stop_workers.sh status.sh update.sh

# ── 7. Configurar auto-inicio (LaunchAgent) ────────────────────────────────
echo -e "${BLUE}[7/7] Configurando inicio automático...${NC}"

PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/com.bittrader.workers.plist"
mkdir -p "$PLIST_DIR"

VENV_PYTHON="$WORK_DIR/venv/bin/python3"

cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bittrader.workers</string>
    <key>ProgramArguments</key>
    <array>
        <string>$WORK_DIR/start_workers.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>$WORK_DIR/logs/launchagent.log</string>
    <key>StandardErrorPath</key>
    <string>$WORK_DIR/logs/launchagent_err.log</string>
    <key>WorkingDirectory</key>
    <string>$WORK_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>COORDINATOR_URL</key>
        <string>$COORDINATOR_URL</string>
        <key>NUM_WORKERS</key>
        <string>$NUM_WORKERS</string>
        <key>USE_RAY</key>
        <string>false</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
</dict>
</plist>
EOF

# Cargar LaunchAgent
launchctl unload "$PLIST_FILE" 2>/dev/null
launchctl load "$PLIST_FILE"
echo -e "  ${GREEN}✓ Auto-inicio configurado (se iniciará al encender Mac)${NC}"

# ── Iniciar workers ahora ──────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ INSTALACIÓN COMPLETADA                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Coordinator : ${BOLD}$COORDINATOR_URL${NC}"
echo -e "  Workers     : ${BOLD}$NUM_WORKERS workers${NC}"
echo -e "  Directorio  : ${BOLD}$WORK_DIR${NC}"
echo ""
echo "  Iniciando workers..."
bash start_workers.sh
echo ""
echo "  Comandos útiles:"
echo "    Ver estado  : cd ~/crypto_worker && ./status.sh"
echo "    Detener     : cd ~/crypto_worker && ./stop_workers.sh"
echo "    Actualizar  : cd ~/crypto_worker && ./update.sh"
echo ""
echo -e "  ${YELLOW}Los workers se iniciarán automáticamente al encender el Mac.${NC}"
echo ""
read -p "Presiona Enter para cerrar..."
