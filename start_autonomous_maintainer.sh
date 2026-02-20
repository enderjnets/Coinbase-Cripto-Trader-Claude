#!/bin/bash
#
# 🚀 Inicia el Mantenimiento Autónomo del Cluster
# Este script ejecuta el sistema de mantenimiento en background
#

echo "========================================"
echo "  🚀 MANTENIMIENTO AUTÓNOMO INICIADO"
echo "========================================"
echo ""
echo "📊 Ejecutando verificación inicial..."

cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

# Ejecutar verificación inicial
python3 autonomous_maintainer.py --once

echo ""
echo "✅ Sistema verificado"
echo ""
echo "📝 Iniciando modo continuo en background..."

# Ejecutar continuamente en background
nohup python3 autonomous_maintainer.py --continuous > /tmp/autonomous_maintainer.log 2>&1 &

MAINT_PID=$!

echo "🔄 Mantenimiento autónomo corriendo (PID: $MAINT_PID)"
echo ""
echo "📊 Logs: tail -f /tmp/autonomous_maintainer.log"
echo ""
echo "========================================"
echo "  ✅ SISTEMA ACTIVO"
echo "========================================"

# Verificar que está corriendo
sleep 2
if ps -p $MAINT_PID > /dev/null; then
    echo "✅ Proceso activo"
else
    echo "❌ Error al iniciar proceso"
fi
