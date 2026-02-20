#!/bin/bash
#
# 📊 SCRIPT DE VERIFICACIÓN RÁPIDA DEL CLUSTER
# Ejecutar para ver estado actual del sistema
#

echo "========================================"
echo "  📊 VERIFICACIÓN RÁPIDA DEL CLUSTER"
echo "========================================"
echo ""

PROJECT_DIR="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
cd "$PROJECT_DIR"

echo "📡 Consultando estado del sistema..."
echo ""

# Obtener estado del dashboard
STATUS=$(curl -s http://localhost:5006/api/status 2>/dev/null)

if [ -n "$STATUS" ]; then
    echo "🎯 ESTADO GENERAL:"
    echo "   Workers activos: $(echo $STATUS | python3 -c "import sys,json; print(json.load(sys.stdin)['workers']['active'])")"
    echo "   WUs completados: $(echo $STATUS | python3 -c "import sys,json; print(json.load(sys.stdin)['work_units']['completed'])")"
    echo "   WUs en progreso: $(echo $STATUS | python3 -c "import sys,json; print(json.load(sys.stdin)['work_units']['in_progress'])")"
    echo "   Mejor PnL: \$(echo $STATUS | python3 -c "import sys,json; print(json.load(sys.stdin)['best_strategy']['pnl'])")"
else
    echo "❌ No se puede conectar al dashboard"
fi

echo ""
echo "🏆 DISTRIBUCIÓN POR MÁQUINA:"
sqlite3 "$PROJECT_DIR/coordinator.db" "
SELECT 
  CASE 
    WHEN id LIKE '%MacBook-Pro%' THEN '🍎 MacBook Pro'
    WHEN id LIKE '%MacBook-Air%' THEN '🪶 MacBook Air'
    WHEN id LIKE '%rog%' THEN '🐧 Linux ROG'
    WHEN id LIKE '%enderj_Linux%' THEN '🐧 enderj Linux'
    ELSE '🔧 Otro'
  END as machine,
  COUNT(*) as total,
  SUM(CASE WHEN (julianday('now') - last_seen) < (10.0/1440.0) THEN 1 ELSE 0 END) as active
FROM workers 
GROUP BY machine
ORDER BY active DESC, total DESC;
" | while read line; do
    echo "   $line"
done

echo ""
echo "💡 COMANDOS ÚTILES:"
echo "   📊 Ver dashboard: open http://localhost:5006"
echo "   🔄 Reparar workers: python3 autonomous_worker_fix.py"
echo "   📈 Ver log: tail -f /tmp/autonomous.log"
echo ""
