#!/bin/bash
# Monitor del Strategy Miner en tiempo real

OUTPUT_FILE="/private/tmp/claude/-Users-enderj/tasks/b6d27d0.output"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║         📊 STRATEGY MINER - MONITOR EN TIEMPO REAL              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

if [ ! -f "$OUTPUT_FILE" ]; then
    echo "❌ No se encontró el archivo de output"
    exit 1
fi

# Mostrar últimas 25 líneas de progreso
echo "📈 Progreso reciente:"
echo "════════════════════════════════════════════════════════════════════"
grep -E "🧬 Gen|PnL:" "$OUTPUT_FILE" | tail -25
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Estadísticas
TOTAL_GENS=$(grep -c "🧬 Gen" "$OUTPUT_FILE")
BEST_PNL=$(grep "PnL:" "$OUTPUT_FILE" | grep -o '\$[0-9,.-]*' | tr -d '$,' | sort -n | tail -1)

echo "📊 Estadísticas:"
echo "   • Generaciones completadas: $TOTAL_GENS / 50"
echo "   • Mejor PnL encontrado: \$$BEST_PNL"
echo ""

# Seguir el output en tiempo real
echo "🔄 Siguiendo output en tiempo real (Ctrl+C para salir)..."
echo "════════════════════════════════════════════════════════════════════"
tail -f "$OUTPUT_FILE" | grep --line-buffered -E "🧬|PnL:|🏆|💰|✅"
