#!/bin/bash
# ============================================================================
# Bittrader Worker Installer v5.0 - Linux
# Fecha: 2026-02-24
# Cambios: Soporte multi-maquina, Numba JIT, Dashboard mejorado
# ============================================================================

set -e

COORDINATOR_URL="${COORDINATOR_URL:-http://100.77.179.14:5001}"
NUM_WORKERS="${NUM_WORKERS:-5}"
WORK_DIR="$HOME/crypto_worker"

echo "=========================================="
echo "  Bittrader Worker Installer v5.0 - Linux"
echo "=========================================="
echo ""
echo "Coordinator: $COORDINATOR_URL"
echo "Workers: $NUM_WORKERS"
echo "Directory: $WORK_DIR"
echo ""

# Crear directorio
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Copiar archivos
echo "Copiando archivos..."
cp -r "$(dirname "$0")/crypto_worker.py" .
cp -r "$(dirname "$0")/strategy_miner.py" .
cp -r "$(dirname "$0")/numba_backtester.py" .
cp -r "$(dirname "$0")/backtester.py" .
cp -r "$(dirname "$0")/dynamic_strategy.py" .

# Crear config.env
cat > config.env << 'EOF'
COORDINATOR_URL=$COORDINATOR_URL
NUM_WORKERS=$NUM_WORKERS
USE_RAY=false
PYTHONUNBUFFERED=1
EOF

# Detectar distribucion
if command -v apt-get &> /dev/null; then
    echo "Detectado sistema Debian/Ubuntu..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
elif command -v dnf &> /dev/null; then
    echo "Detectado sistema Fedora/RHEL..."
    sudo dnf install -y python3 python3-pip
elif command -v pacman &> /dev/null; then
    echo "Detectado sistema Arch..."
    sudo pacman -S --noconfirm python python-pip
fi

# Crear entorno virtual
echo "Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
echo "Instalando dependencias..."
pip install --upgrade pip
pip install requests numpy numba pandas

# Verificar Numba
echo "Verificando Numba JIT..."
python3 -c "import numba; print(f'Numba version: {numba.__version__}')"

# Crear script de inicio
cat > start_workers.sh << 'EOF'
#!/bin/bash
cd "$HOME/crypto_worker"
source venv/bin/activate
COORDINATOR_URL="${COORDINATOR_URL:-http://100.77.179.14:5001}"
NUM_WORKERS="${NUM_WORKERS:-5}"

for i in $(seq 1 $NUM_WORKERS); do
    COORDINATOR_URL="$COORDINATOR_URL" NUM_WORKERS="$NUM_WORKERS" WORKER_INSTANCE="$i" USE_RAY="false" \
    PYTHONUNBUFFERED=1 nohup python3 -u crypto_worker.py > /tmp/worker_$i.log 2>&1 &
    echo "Worker $i iniciado"
    sleep 2
done
echo "✅ $NUM_WORKERS workers iniciados"
EOF
chmod +x start_workers.sh

# Crear script de parada
cat > stop_workers.sh << 'EOF'
#!/bin/bash
pkill -f crypto_worker.py
echo "✅ Workers detenidos"
EOF
chmod +x stop_workers.sh

# Crear script de estado
cat > status.sh << 'EOF'
#!/bin/bash
echo "=== Workers activos ==="
ps aux | grep -c "[c]rypto_worker.py"
echo ""
echo "=== Ultimos logs ==="
for i in 1 2 3 4 5; do
    if [ -f /tmp/worker_$i.log ]; then
        echo "--- Worker $i ---"
        tail -3 /tmp/worker_$i.log 2>/dev/null
    fi
done
EOF
chmod +x status.sh

echo ""
echo "=========================================="
echo "  Instalacion completada!"
echo "=========================================="
echo ""
echo "Para iniciar workers:"
echo "  cd $WORK_DIR && ./start_workers.sh"
echo ""
echo "Para detener workers:"
echo "  cd $WORK_DIR && ./stop_workers.sh"
echo ""
echo "Para ver estado:"
echo "  cd $WORK_DIR && ./status.sh"
