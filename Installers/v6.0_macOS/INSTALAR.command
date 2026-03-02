#!/bin/bash
# ============================================================================
#  BITTRADER WORKER - Instalador Automatico v6.0 - macOS
#  Haz doble clic en este archivo desde Finder para instalar.
#  Compatible con Apple Silicon (M1/M2/M3) e Intel.
#
#  CAMBIOS v6.0:
#  - Soporte completo de Futures: SHORT, leverage (1-10x), liquidacion,
#    funding rates cada 8 horas.
#  - Nuevo archivo config.py con SPOT_FEE_MAKER, FUTURES_FEE_TAKER,
#    FUTURES_FUNDING_RATE.
#  - GENOME_SIZE ampliado a 22 (direction + leverage).
#  - Re-detecta URL del coordinator en cada inicio (LAN vs Tailscale).
# ============================================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

clear
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        BITTRADER WORKER INSTALLER v6.0 - macOS          ║${NC}"
echo -e "${BOLD}║        + Futures: SHORT / Leverage / Funding            ║${NC}"
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
elif curl -s --max-time 5 "$WAN_URL/api/status" > /dev/null 2>&1; then
    COORDINATOR_URL="$WAN_URL"
    echo -e "  ${GREEN}✓ Tailscale detectado → $COORDINATOR_URL${NC}"
else
    echo -e ""
    echo -e "${RED}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║              ❌ ERROR: SIN CONEXIÓN                      ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════╝${NC}"
    echo -e ""
    echo -e "${YELLOW}No se pudo conectar al coordinator desde esta red.${NC}"
    echo -e "${YELLOW}Los workers necesitan Tailscale para conectarse remotamente.${NC}"
    echo -e ""
    echo -e "${BOLD}SOLUCIÓN:${NC}"
    echo -e "  1. Instala Tailscale: ${BLUE}https://tailscale.com/download${NC}"
    echo -e "  2. Inicia sesión con la cuenta que Ender te invite"
    echo -e "  3. Una vez conectado a la red de Ender, vuelve a ejecutar este instalador"
    echo -e ""
    echo -e "  (Si estás en casa de Ender, verifica que estés en su WiFi)"
    echo -e ""
    read -p "Presiona Enter para salir..."
    exit 1
fi

# ── 2. Auto-detectar CPUs óptimos ──────────────────────────────────────────
TOTAL_CPUS=$(sysctl -n hw.logicalcpu 2>/dev/null || echo 4)
if   [ "$TOTAL_CPUS" -le 2 ]; then NUM_WORKERS=1
elif [ "$TOTAL_CPUS" -le 4 ]; then NUM_WORKERS=$((TOTAL_CPUS - 1))
else                                NUM_WORKERS=$((TOTAL_CPUS - 2))
fi
echo -e "${BLUE}[2/7] CPUs detectados: ${TOTAL_CPUS} → Lanzando ${NUM_WORKERS} workers${NC}"

# ── 3. Crear directorio de trabajo ─────────────────────────────────────────
echo -e "${BLUE}[3/7] Preparando directorio $WORK_DIR ...${NC}"
mkdir -p "$WORK_DIR/logs" "$WORK_DIR/data"
cd "$WORK_DIR"

# ── 4. Descargar archivos desde GitHub ─────────────────────────────────────
echo -e "${BLUE}[4/7] Descargando archivos desde GitHub...${NC}"
FILES=(crypto_worker.py numba_backtester.py backtester.py dynamic_strategy.py strategy_miner.py config.py)
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

if ! command -v brew &>/dev/null; then
    echo "  Instalando Homebrew (requiere contraseña)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
    fi
fi

if ! command -v python3 &>/dev/null; then
    echo "  Instalando Python 3.11..."
    brew install python@3.11
fi

if [ ! -d "venv" ]; then
    echo "  Creando entorno virtual..."
    python3 -m venv venv
fi
source venv/bin/activate

echo "  Instalando paquetes Python..."
pip install --upgrade pip -q
pip install requests numpy numba pandas -q
python3 -c "import numba; print(f'  ✓ Numba {numba.__version__} instalado')"

# ── 6. Crear scripts auxiliares ────────────────────────────────────────────
echo -e "${BLUE}[6/7] Creando scripts...${NC}"

# Guardar config base (sin URL hardcodeada — se detecta en cada inicio)
cat > config.env << EOF
NUM_WORKERS=$NUM_WORKERS
USE_RAY=false
PYTHONUNBUFFERED=1
INSTALLER_VERSION=6.0
LAN_URL=$LAN_URL
WAN_URL=$WAN_URL
EOF

# ── start_workers.sh: RE-DETECTA URL en cada inicio ──
cat > start_workers.sh << 'STARTEOF'
#!/bin/bash
cd "$HOME/crypto_worker"
source venv/bin/activate
source config.env

# Re-detectar coordinator URL en cada inicio (LAN vs Tailscale)
if curl -s --max-time 3 "$LAN_URL/api/status" > /dev/null 2>&1; then
    COORDINATOR_URL="$LAN_URL"
    echo "  Red local → $COORDINATOR_URL"
else
    COORDINATOR_URL="$WAN_URL"
    echo "  Tailscale → $COORDINATOR_URL"
fi
export COORDINATOR_URL

echo "Iniciando $NUM_WORKERS workers → $COORDINATOR_URL"
for i in $(seq 1 $NUM_WORKERS); do
    COORDINATOR_URL="$COORDINATOR_URL" WORKER_INSTANCE="$i" USE_RAY="false" \
    PYTHONUNBUFFERED=1 nohup python3 -u crypto_worker.py >> logs/worker_$i.log 2>&1 &
    echo "  Worker $i (PID $!)"
    sleep 1
done
echo "✅ $NUM_WORKERS workers iniciados. Logs: ~/crypto_worker/logs/"
STARTEOF

cat > stop_workers.sh << 'STOPEOF'
#!/bin/bash
COUNT=$(pgrep -f crypto_worker.py | wc -l | tr -d ' ')
pkill -f crypto_worker.py 2>/dev/null
echo "✅ $COUNT workers detenidos"
STOPEOF

cat > status.sh << 'STATEOF'
#!/bin/bash
source "$HOME/crypto_worker/config.env"
COUNT=$(pgrep -f crypto_worker.py | wc -l | tr -d ' ')
if curl -s --max-time 2 "$LAN_URL/api/status" > /dev/null 2>&1; then COORD_URL="$LAN_URL"; else COORD_URL="$WAN_URL"; fi
echo "══════════════════════════════"
echo "  BITTRADER WORKER STATUS v6.0"
echo "══════════════════════════════"
echo "  Workers activos : $COUNT / $NUM_WORKERS"
echo "  Coordinator     : $COORD_URL"
echo ""
for i in $(seq 1 $NUM_WORKERS); do
    LOG="$HOME/crypto_worker/logs/worker_$i.log"
    [ -f "$LOG" ] && echo "  W$i: $(tail -1 $LOG 2>/dev/null)"
done
STATEOF

cat > update.sh << 'UPDATEEOF'
#!/bin/bash
cd "$HOME/crypto_worker"
echo "Actualizando archivos desde GitHub..."
GITHUB_RAW="https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main"
for f in crypto_worker.py numba_backtester.py backtester.py dynamic_strategy.py strategy_miner.py config.py; do
    curl -fsSL "$GITHUB_RAW/$f" -o "$f" && echo "  ✓ $f" || echo "  ✗ Error: $f"
done
echo "✅ Actualización completada. Reinicia workers: ./stop_workers.sh && ./start_workers.sh"
UPDATEEOF

chmod +x start_workers.sh stop_workers.sh status.sh update.sh

# ── 7. Configurar auto-inicio (LaunchAgent) ────────────────────────────────
echo -e "${BLUE}[7/7] Configurando inicio automático...${NC}"

PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/com.bittrader.workers.plist"
mkdir -p "$PLIST_DIR"

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
        <string>/bin/bash</string>
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
</dict>
</plist>
EOF

launchctl unload "$PLIST_FILE" 2>/dev/null
launchctl load "$PLIST_FILE"
echo -e "  ${GREEN}✓ Auto-inicio configurado${NC}"

# ── Iniciar workers ahora ──────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ INSTALACIÓN COMPLETADA v6.0              ║${NC}"
echo -e "${GREEN}║           Futures: SHORT / Leverage / Funding            ║${NC}"
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
echo -e "  ${YELLOW}Workers se inician automáticamente al encender el Mac.${NC}"
echo ""
read -p "Presiona Enter para cerrar..."
