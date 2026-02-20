#!/bin/bash
################################################################################
# SCRIPT DE CONFIGURACIÓN AUTOMÁTICA DEL WORKER
# Ejecuta este script en tu MacBook Pro Worker y todo se configurará solo
################################################################################

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║           CONFIGURACIÓN AUTOMÁTICA DEL WORKER                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# COLORES
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. DETECTAR DIRECTORIO DEL PROYECTO
echo "🔍 Detectando directorio del proyecto..."

# Buscar en ubicaciones comunes
POSSIBLE_PATHS=(
    "$HOME/Bittrader"
    "$HOME/Documents/Bittrader"
    "$HOME/Library/CloudStorage/GoogleDrive-*/My Drive/Bittrader"
    "/Users/*/Bittrader"
)

PROJECT_DIR=""
for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -d "$path" ]; then
        echo -e "${GREEN}✓${NC} Encontrado: $path"
        PROJECT_DIR="$path"
        break
    fi
done

if [ -z "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}⚠${NC}  No se encontró automáticamente."
    read -p "Ingresa la ruta completa del proyecto: " PROJECT_DIR
fi

cd "$PROJECT_DIR" || exit 1
echo -e "${GREEN}✓${NC} Directorio: $(pwd)"
echo ""

# 2. VERIFICAR PYTHON Y VENV
echo "🐍 Verificando Python y entorno virtual..."

if [ -d ".venv" ]; then
    echo -e "${GREEN}✓${NC} Entorno virtual existe"
    PYTHON_CMD=".venv/bin/python"
else
    echo -e "${YELLOW}⚠${NC}  No hay .venv, usando Python del sistema"
    PYTHON_CMD="python3"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${GREEN}✓${NC} $PYTHON_VERSION"
echo ""

# 3. DETENER RAY ANTIGUO
echo "🛑 Deteniendo procesos Ray antiguos..."

$PYTHON_CMD -m ray stop --force 2>/dev/null || true
pkill -f "ray::" 2>/dev/null || true
sleep 2

echo -e "${GREEN}✓${NC} Ray detenido"
echo ""

# 4. OBTENER IP DEL HEAD NODE
echo "🌐 Configurando conexión al Head Node..."

# Intentar detectar automáticamente
HEAD_IP=$(arp -a | grep -i "tailscale\|100\." | head -1 | awk '{print $2}' | tr -d '()')

if [ -z "$HEAD_IP" ]; then
    # Pedir al usuario
    echo -e "${YELLOW}⚠${NC}  No se detectó la IP del Head Node automáticamente"
    echo ""
    echo "Opciones comunes:"
    echo "  - 10.0.0.239 (Red local)"
    echo "  - 100.x.x.x (Tailscale)"
    echo ""
    read -p "Ingresa la IP del Head Node: " HEAD_IP
fi

echo -e "${GREEN}✓${NC} Head Node IP: $HEAD_IP"
echo ""

# 5. VERIFICAR CONECTIVIDAD
echo "🔌 Verificando conectividad..."

if ping -c 1 -W 2 "$HEAD_IP" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Head Node alcanzable"
else
    echo -e "${RED}✗${NC} No se puede alcanzar $HEAD_IP"
    echo "   Verifica:"
    echo "   - Que ambas máquinas estén en la misma red"
    echo "   - Firewall desactivado"
    echo "   - IP correcta"
    exit 1
fi

# Verificar puerto Ray
if nc -z -w 2 "$HEAD_IP" 6379 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Puerto Ray (6379) abierto"
else
    echo -e "${YELLOW}⚠${NC}  Puerto 6379 no responde (¿Head Node corriendo?)"
fi
echo ""

# 6. INSTALAR/ACTUALIZAR DEPENDENCIAS
echo "📦 Verificando dependencias..."

if [ -d ".venv" ]; then
    echo "Actualizando Ray..."
    .venv/bin/pip install -q --upgrade "ray[default]==2.51.2" 2>&1 | grep -v "Requirement already satisfied" || true
    echo -e "${GREEN}✓${NC} Dependencias actualizadas"
else
    echo -e "${YELLOW}⚠${NC}  Sin venv, saltando instalación"
fi
echo ""

# 7. INICIAR WORKER
echo "🚀 Iniciando Ray Worker..."
echo "   Conectando a: $HEAD_IP:6379"
echo ""

export RAY_ADDRESS="$HEAD_IP:6379"

$PYTHON_CMD -m ray start \
    --address="$HEAD_IP:6379" \
    --num-cpus=$(sysctl -n hw.ncpu) \
    --object-store-memory=2000000000

echo ""

# 8. VERIFICAR ESTADO
sleep 3
echo "📊 Verificando estado del cluster..."
$PYTHON_CMD -m ray status

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  ✅ CONFIGURACIÓN COMPLETADA                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Dashboard: http://$HEAD_IP:8265"
echo ""
echo "🔹 Para detener el worker:"
echo "   $PYTHON_CMD -m ray stop"
echo ""
echo "🔹 Para verificar estado:"
echo "   $PYTHON_CMD -m ray status"
echo ""
