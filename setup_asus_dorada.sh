#!/bin/bash
################################################################################
# CONFIGURACIÓN RÁPIDA - EJECUTAR EN LA ASUS DORADA (10.0.0.56)
################################################################################

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     🔧 CONFIGURACIÓN WORKER - ASUS DORADA (Kubuntu)         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Contraseña de sudo cuando la pida
read -s -p "📝 Ingresa tu contraseña de sudo (se usará para instalar): " SUDO_PASS
echo ""

# ==============================================================================
# 1. ACTUALIZAR E INSTALAR DEPENDENCIAS
# ==============================================================================
echo "🔄 Actualizando sistema..."
echo "$SUDO_PASS" | sudo -S apt update -y > /dev/null 2>&1
echo "$SUDO_PASS" | sudo -S apt upgrade -y > /dev/null 2>&1
echo "✅ Sistema actualizado"

# Instalar Python y git
echo "📦 Instalando Python y git..."
echo "$SUDO_PASS" | sudo -S apt install -y python3 python3-pip git curl > /dev/null 2>&1
echo "✅ Dependencias instaladas"

# ==============================================================================
# 2. CONFIGURAR PROYECTO
# ==============================================================================
echo ""
echo "📁 Configurando proyecto..."

# Ir al home
cd ~

# Clonar o actualizar proyecto
if [ -d "Coinbase-Cripto-Trader-Claude" ]; then
    echo "Actualizando proyecto..."
    cd Coinbase-Cripto-Trader-Claude
    git pull origin main > /dev/null 2>&1
else
    echo "Clonando proyecto..."
    git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git
    cd Coinbase-Cripto-Trader-Claude
fi

PROJECT_DIR=$(pwd)
echo "✅ Proyecto en: $PROJECT_DIR"

# ==============================================================================
# 3. INSTALAR DEPENDENCIAS PYTHON
# ==============================================================================
echo ""
echo "🐍 Instalando dependencias Python..."

pip3 install --quiet requests pandas numpy --break-system-packages 2>/dev/null || \
pip3 install --quiet requests pandas numpy

echo "✅ Dependencias Python listas"

# ==============================================================================
# 4. INICIAR WORKERS
# ==============================================================================
echo ""
echo "🚀 Iniciando workers..."

COORDINATOR_URL="http://100.77.179.14:5001"
NUM_WORKERS=4

# Detener workers anteriores si existen
pkill -f crypto_worker 2>/dev/null || true
sleep 1

# Iniciar workers
for i in $(seq 1 $NUM_WORKERS); do
    WORKER_INSTANCE=$i nohup python3 crypto_worker.py $COORDINATOR_URL > ~/worker_$i.log 2>&1 &
    echo "   Worker $i iniciado"
    sleep 1
done

echo ""
echo "✅ Workers iniciados"

# ==============================================================================
# 5. VERIFICAR
# ==============================================================================
sleep 3

echo ""
echo "🔍 Verificando..."
ps aux | grep crypto_worker | grep -v grep | wc -l

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              ✅ CONFIGURACIÓN COMPLETADA                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Verificar en coordinator:"
echo "   curl http://100.77.179.14:5001/api/status"
echo ""
echo "📝 Logs de workers:"
echo "   tail -f ~/worker_*.log"
echo ""
