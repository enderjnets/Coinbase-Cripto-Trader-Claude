#!/bin/bash
################################################################################
# SCRIPT DE CONFIGURACIÓN REMOTA DEL WORKER
# Ejecuta este script DESDE EL HEAD para configurar el Worker automáticamente
################################################################################

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║      🌐 CONFIGURACIÓN REMOTA DEL WORKER VÍA SSH                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# CONFIGURACIÓN
HEAD_IP="10.0.0.239"
WORKER_USER="enderj"
WORKER_HOST="Enders-MacBook-Pro.local"

echo "📍 Configuración:"
echo "   Head IP: $HEAD_IP"
echo "   Worker: $WORKER_USER@$WORKER_HOST"
echo ""

# VERIFICAR CONECTIVIDAD SSH
echo "🔌 Verificando conectividad SSH..."

if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$WORKER_USER@$WORKER_HOST" "echo '✅ Conexión SSH exitosa'" 2>/dev/null; then
    echo "✅ SSH funciona correctamente"
else
    echo "❌ No se puede conectar vía SSH"
    echo ""
    echo "Posibles soluciones:"
    echo "1. Verifica que Remote Login esté habilitado en el Worker:"
    echo "   System Settings → General → Sharing → Remote Login (ON)"
    echo ""
    echo "2. Prueba manualmente:"
    echo "   ssh $WORKER_USER@$WORKER_HOST"
    echo ""
    exit 1
fi

echo ""
echo "🔍 Buscando proyecto en el Worker..."

# BUSCAR DIRECTORIO DEL PROYECTO
SEARCH_SCRIPT='
for dir in \
    "$HOME/Bittrader" \
    "$HOME/Documents/Bittrader" \
    "$HOME/Library/CloudStorage/GoogleDrive-"*"/My Drive/Bittrader" \
    "/Users/*/Bittrader"; do
    if [ -d "$dir" ]; then
        # Buscar la carpeta específica
        if [ -d "$dir/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude" ]; then
            echo "$dir/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
            exit 0
        fi
    fi
done
echo "NOT_FOUND"
'

PROJECT_DIR=$(ssh "$WORKER_USER@$WORKER_HOST" "$SEARCH_SCRIPT")

if [ "$PROJECT_DIR" = "NOT_FOUND" ]; then
    echo "❌ No se encontró el proyecto automáticamente"
    echo ""
    read -p "Ingresa la ruta completa del proyecto en el Worker: " PROJECT_DIR
else
    echo "✅ Proyecto encontrado: $PROJECT_DIR"
fi

echo ""
echo "🚀 Configurando Worker..."
echo "   (Esto puede tomar 1-2 minutos)"
echo ""

# SCRIPT DE CONFIGURACIÓN REMOTA
ssh "$WORKER_USER@$WORKER_HOST" bash <<REMOTE_SCRIPT
set -e

cd "$PROJECT_DIR" || exit 1

echo "📂 Directorio: \$(pwd)"
echo ""

# 1. Detener Ray antiguo
echo "🛑 Deteniendo procesos Ray antiguos..."
.venv/bin/ray stop --force 2>/dev/null || true
pkill -f "ray::" 2>/dev/null || true
sleep 2
echo "✅ Ray detenido"
echo ""

# 2. Verificar Python
echo "🐍 Verificando Python..."
PYTHON_VERSION=\$(.venv/bin/python --version 2>&1)
echo "   \$PYTHON_VERSION"

if [[ "\$PYTHON_VERSION" != *"3.9.6"* ]]; then
    echo "⚠️  Versión de Python diferente"
    echo "   Head usa: Python 3.9.6"
    echo "   Worker usa: \$PYTHON_VERSION"
    echo "   Continuando de todas formas..."
fi
echo ""

# 3. Iniciar Worker
echo "🔗 Conectando al Head Node ($HEAD_IP:6379)..."

.venv/bin/ray start \\
    --address="$HEAD_IP:6379" \\
    --num-cpus=\$(sysctl -n hw.ncpu) \\
    --object-store-memory=2000000000

if [ \$? -eq 0 ]; then
    echo ""
    echo "✅ Worker conectado exitosamente"
else
    echo ""
    echo "❌ Error al conectar"
    exit 1
fi

REMOTE_SCRIPT

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  ✅ CONFIGURACIÓN COMPLETADA                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# VERIFICAR EN EL HEAD
echo "📊 Verificando cluster desde el Head..."
sleep 2

.venv/bin/ray status

echo ""
echo "🎯 Próximos pasos:"
echo "   1. Verifica que aparezcan 2 nodos activos arriba"
echo "   2. Verifica que haya ~22 CPUs totales"
echo "   3. Ejecuta el Strategy Miner con la configuración correcta"
echo ""
echo "📊 Dashboard: http://$HEAD_IP:8265"
echo ""
