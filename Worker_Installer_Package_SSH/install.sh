#!/bin/bash
# Bittrader Worker Installer v3.0 - SSH Tunnel Edition
# Universal Worker - Funciona desde CUALQUIER ubicación
# Fecha: 27 de Enero 2026

set -e

VERSION="3.0"
HEAD_IP="100.77.179.14"  # Tailscale IP del MacBook Pro Head
HEAD_PORT="6379"
WORKER_DIR="$HOME/.bittrader_worker"
VENV_PATH="$WORKER_DIR/venv"

echo "=========================================="
echo "Bittrader Worker Installer v${VERSION}"
echo "SSH Tunnel Edition - Universal Worker"
echo "=========================================="
echo ""

# Verificar Python 3.9.6
echo "🔍 Verificando Python 3.9.6..."
PYTHON_VERSION=$(/Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9 --version 2>&1 | awk '{print $2}')

if [ "$PYTHON_VERSION" != "3.9.6" ]; then
    echo "❌ Se requiere Python 3.9.6 exacto"
    echo "   Versión encontrada: $PYTHON_VERSION"
    echo ""
    echo "Por favor instala Python 3.9.6 desde:"
    echo "https://www.python.org/ftp/python/3.9.6/python-3.9.6-macosx10.9.pkg"
    exit 1
fi

echo "✅ Python 3.9.6 encontrado"

# Verificar Tailscale
echo ""
echo "🔍 Verificando Tailscale..."
if ! command -v tailscale &> /dev/null; then
    echo "❌ Tailscale no está instalado"
    echo ""
    echo "Por favor instala Tailscale desde:"
    echo "https://tailscale.com/download/mac"
    exit 1
fi

if ! tailscale status &> /dev/null; then
    echo "❌ Tailscale no está conectado"
    echo ""
    echo "Por favor inicia Tailscale y autentícate"
    exit 1
fi

echo "✅ Tailscale conectado"

# Crear directorio de instalación
echo ""
echo "📁 Creando directorio de instalación..."
mkdir -p "$WORKER_DIR"
mkdir -p "$WORKER_DIR/logs"

# Crear entorno virtual
echo ""
echo "🐍 Creando entorno virtual..."
if [ -d "$VENV_PATH" ]; then
    echo "   Eliminando entorno virtual anterior..."
    rm -rf "$VENV_PATH"
fi

/Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

# Instalar Ray 2.10.0
echo ""
echo "📦 Instalando Ray 2.10.0..."
pip install --upgrade pip > /dev/null 2>&1
pip install ray==2.10.0 > /dev/null 2>&1

# Verificar versión
RAY_VERSION=$(ray --version | awk '{print $3}')
echo "✅ Ray $RAY_VERSION instalado"

# Detectar número de CPUs
NUM_CPUS=$(sysctl -n hw.ncpu)
echo ""
echo "🖥️  CPUs detectados: $NUM_CPUS"
echo "$NUM_CPUS" > "$WORKER_DIR/current_cpus"

# Crear archivo de configuración
echo ""
echo "⚙️  Creando configuración..."
cat > "$WORKER_DIR/config.env" <<EOF
HEAD_IP=$HEAD_IP
HEAD_PORT=$HEAD_PORT
NUM_CPUS=$NUM_CPUS
INSTALL_DATE=$(date)
WORKER_MODE=SSH_TUNNEL
RAY_VERSION=2.10.0
EOF

echo "✅ Configuración guardada"

# Verificar conectividad SSH
echo ""
echo "🔐 Verificando conectividad SSH con Head..."
if ssh -o ConnectTimeout=5 -o BatchMode=yes "enderj@$HEAD_IP" "echo OK" &>/dev/null; then
    echo "✅ Conexión SSH exitosa"
else
    echo "⚠️  No se pudo conectar via SSH automáticamente"
    echo ""
    echo "IMPORTANTE: Necesitas configurar autenticación SSH sin contraseña:"
    echo ""
    echo "1. En esta máquina, genera una clave SSH (si no tienes):"
    echo "   ssh-keygen -t ed25519 -C 'bittrader-worker'"
    echo ""
    echo "2. Copia la clave al Head:"
    echo "   ssh-copy-id enderj@$HEAD_IP"
    echo ""
    echo "3. Vuelve a ejecutar este instalador"
    echo ""
    read -p "Presiona Enter para continuar sin SSH (solo para testing)..."
fi

echo ""
echo "=========================================="
echo "✅ Instalación completada"
echo "=========================================="
echo ""
echo "📋 Configuración:"
echo "   - Head IP: $HEAD_IP"
echo "   - CPUs: $NUM_CPUS"
echo "   - Modo: SSH Tunnel"
echo ""
echo "📝 Próximos pasos:"
echo ""
echo "1. Configura autenticación SSH sin contraseña (si no lo hiciste):"
echo "   ssh-copy-id enderj@$HEAD_IP"
echo ""
echo "2. Instala los daemons:"
echo "   ./install_daemons.sh"
echo ""
echo "3. El Worker se iniciará automáticamente"
echo ""
