#!/bin/bash
# ============================================================================
# CRYPTO WORKER INSTALLER - macOS
# ============================================================================

echo "========================================"
echo "  CRYPTO WORKER INSTALLER - macOS"
echo "========================================"
echo ""

# Configuración
INSTALL_DIR="$HOME/crypto_worker"
VENV_DIR="$HOME/coinbase_worker_venv"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKER_FILES="$SCRIPT_DIR/../worker_files"

# URL del coordinador predefinida
COORDINATOR_URL="http://100.77.179.14:5001"

echo "📡 URL del Coordinador: $COORDINATOR_URL"
echo ""
echo "📦 Instalando worker..."
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no encontrado. Instálalo primero:"
    echo "   brew install python3"
    exit 1
fi

echo "✅ Python3 encontrado: $(python3 --version)"

# Crear directorio de instalación
echo "📁 Creando directorio de instalación..."
mkdir -p "$INSTALL_DIR/data"

# Copiar archivos
echo "📋 Copiando archivos..."
cp "$WORKER_FILES"/*.py "$INSTALL_DIR/"
cp "$WORKER_FILES"/data/*.csv "$INSTALL_DIR/data/"

# Crear entorno virtual
echo "🐍 Creando entorno virtual..."
python3 -m venv "$VENV_DIR"

# Instalar dependencias
echo "📥 Instalando dependencias..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install pandas pandas_ta requests ray python-dotenv

# Crear script de auto-reinicio
echo "📝 Creando script de ejecución..."
cat > "$INSTALL_DIR/run_worker.sh" << EOF
#!/bin/bash
VENV_PATH="$VENV_DIR"
LOG_FILE="/tmp/worker_output.log"
COORDINATOR_URL="$COORDINATOR_URL"

echo "========================================"
echo "CRYPTO WORKER - macOS"
echo "========================================"
echo "Coordinator: \$COORDINATOR_URL"

restart_count=0

while true; do
    pkill -f raylet 2>/dev/null
    pkill -f "ray::" 2>/dev/null
    sleep 2

    restart_count=\$((restart_count + 1))
    echo ""
    echo "Iniciando worker (intento #\$restart_count) - \$(date)"

    source "\$VENV_PATH/bin/activate"
    cd "$INSTALL_DIR"

    COORDINATOR_URL="\$COORDINATOR_URL" PYTHONUNBUFFERED=1 python -u crypto_worker.py 2>&1 | tee -a "\$LOG_FILE"

    echo "Worker terminó. Reiniciando en 5 segundos..."
    sleep 5
done
EOF

chmod +x "$INSTALL_DIR/run_worker.sh"

echo ""
echo "========================================"
echo "✅ INSTALACIÓN COMPLETADA"
echo "========================================"
echo ""
echo "Coordinador configurado: $COORDINATOR_URL"
echo ""
echo "Para iniciar el worker:"
echo "  cd $INSTALL_DIR && ./run_worker.sh"
echo ""
echo "Para ejecutar en segundo plano:"
echo "  cd $INSTALL_DIR && nohup ./run_worker.sh > /tmp/worker.log 2>&1 &"
echo ""
