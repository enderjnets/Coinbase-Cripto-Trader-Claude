#!/bin/bash
# ============================================================================
#  BITTRADER WORKER - Instalador Automatico v5.1 - Linux
#  Ejecutar: bash instalar.sh
#  Compatible con Ubuntu, Debian, Fedora, Arch, y derivados.
# ============================================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

clear
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        BITTRADER WORKER INSTALLER v5.1 - Linux          ║${NC}"
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
TOTAL_CPUS=$(nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo 4)
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

# ── 4. Instalar Python y dependencias del sistema ──────────────────────────
echo -e "${BLUE}[4/7] Instalando dependencias del sistema...${NC}"

if command -v apt-get &>/dev/null; then
    echo "  Detectado Debian/Ubuntu..."
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-pip python3-venv curl -qq
elif command -v dnf &>/dev/null; then
    echo "  Detectado Fedora/RHEL..."
    sudo dnf install -y python3 python3-pip curl -q
elif command -v pacman &>/dev/null; then
    echo "  Detectado Arch Linux..."
    sudo pacman -S --noconfirm python python-pip curl
elif command -v zypper &>/dev/null; then
    echo "  Detectado openSUSE..."
    sudo zypper install -y python3 python3-pip curl
fi

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: No se pudo instalar Python3. Instálalo manualmente.${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓ Python $(python3 --version)${NC}"

# ── 5. Descargar archivos desde GitHub ─────────────────────────────────────
echo -e "${BLUE}[5/7] Descargando archivos desde GitHub...${NC}"
FILES=(crypto_worker.py numba_backtester.py backtester.py dynamic_strategy.py strategy_miner.py)
for f in "${FILES[@]}"; do
    printf "  Descargando %-30s " "$f..."
    if curl -fsSL "$GITHUB_RAW/$f" -o "$f" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Error al descargar $f${NC}"
        echo "  Verifica tu conexión a internet."
        exit 1
    fi
done

# Crear entorno virtual e instalar paquetes
python3 -m venv venv
source venv/bin/activate

echo "  Instalando paquetes Python..."
pip install --upgrade pip -q
pip install requests numpy numba pandas -q

python3 -c "import numba; print(f'  ✓ Numba {numba.__version__} instalado')"

# ── 6. Crear scripts auxiliares ────────────────────────────────────────────
echo -e "${BLUE}[6/7] Creando scripts...${NC}"
mkdir -p logs

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
COUNT=$(pgrep -f crypto_worker.py | wc -l)
pkill -f crypto_worker.py 2>/dev/null
echo "✅ $COUNT workers detenidos"
STOPEOF

# Script de estado
cat > status.sh << 'STATEOF'
#!/bin/bash
source "$HOME/crypto_worker/config.env"
COUNT=$(pgrep -f crypto_worker.py | wc -l)
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

chmod +x start_workers.sh stop_workers.sh status.sh update.sh

# ── 7. Configurar auto-inicio con systemd ──────────────────────────────────
echo -e "${BLUE}[7/7] Configurando inicio automático (systemd)...${NC}"

SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_DIR"

cat > "$SYSTEMD_DIR/bittrader-workers.service" << EOF
[Unit]
Description=Bittrader Crypto Worker v5.1
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
WorkingDirectory=$WORK_DIR
ExecStartPre=/bin/sleep 10
ExecStart=$WORK_DIR/start_workers.sh
ExecStop=$WORK_DIR/stop_workers.sh
Restart=on-failure
RestartSec=30
Environment=COORDINATOR_URL=$COORDINATOR_URL
Environment=NUM_WORKERS=$NUM_WORKERS
Environment=USE_RAY=false
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:$WORK_DIR/logs/systemd.log
StandardError=append:$WORK_DIR/logs/systemd_err.log

[Install]
WantedBy=default.target
EOF

# Habilitar servicio
systemctl --user daemon-reload 2>/dev/null
systemctl --user enable bittrader-workers.service 2>/dev/null
# Habilitar linger para que el servicio arranque sin login
loginctl enable-linger "$USER" 2>/dev/null

echo -e "  ${GREEN}✓ Servicio systemd habilitado (se iniciará al encender)${NC}"

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
echo "    Servicio    : systemctl --user status bittrader-workers"
echo ""
echo -e "  ${YELLOW}Los workers se iniciarán automáticamente al encender el equipo.${NC}"
