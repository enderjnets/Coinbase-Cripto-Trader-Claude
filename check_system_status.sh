#!/usr/bin/bash
#
# 🚀 SCRIPT DE TRADING COMPLETO
# Sistema de trading autónomo con $500 capital
#

echo ""
echo "========================================"
echo "  🚀 SISTEMA DE TRADING v1.0"
echo "========================================"
echo ""
echo "💰 Capital: \$500"
echo "🎯 Objetivo: 5% diario"
echo ""

cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

# Verificar coordinator
echo "📡 Verificando coordinator..."
if curl -s http://localhost:5001/api/status > /dev/null 2>&1; then
    echo "✅ Coordinator activo"
else
    echo "⚠️ Coordinator no responde - iniciando..."
fi

# Ver workers
echo ""
echo "👥 Verificando workers..."
WORKERS=$(curl -s http://localhost:5001/api/workers 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('workers',[]))" 2>/dev/null || echo "0")
echo "Workers activos: $WORKERS"

# Ver Work Units
echo ""
echo "📦 Verificando Work Units..."
WUS=$(sqlite3 coordinator.db "SELECT COUNT(*) FROM work_units" 2>/dev/null || echo "0")
echo "Work Units: $WUS"

# Ver resultados
echo ""
echo "📊 Verificando resultados..."
RESULTS=$(sqlite3 coordinator.db "SELECT COUNT(*) FROM results" 2>/dev/null || echo "0")
echo "Resultados: $RESULTS"

echo ""
echo "========================================"
echo "  📊 ESTADO DEL SISTEMA"
echo "========================================"
echo ""
echo "Workers activos: $WORKERS"
echo "Work Units: $WUS"
echo "Resultados: $RESULTS"
echo ""

# Ver mejor PnL
BEST=$(sqlite3 coordinator.db "SELECT MAX(pnl) FROM results" 2>/dev/null)
echo "Mejor PnL: \$$BEST"

# Verificar archivos de datos
echo ""
echo "📁 Archivos de datos:"
ls -la data/ 2>/dev/null | head -10

echo ""
echo "========================================"
echo "  🎯 PRÓXIMOS PASOS"
echo "========================================"
echo ""
echo "1. Para iniciar trading:"
echo "   python3 crypto_worker.py"
echo ""
echo "2. Para ver dashboards:"
echo "   - http://localhost:5006 (F1 Dashboard)"
echo "   - http://localhost:8501 (Streamlit)"
echo ""
echo "3. Para ver workers activos:"
echo "   sqlite3 coordinator.db \"SELECT id FROM workers\""
echo ""

# Mostrar workers activos
echo "👥 Workers Activos:"
sqlite3 coordinator.db "SELECT id FROM workers WHERE (julianday('now') - last_seen) < 0.01" 2>/dev/null | head -10
