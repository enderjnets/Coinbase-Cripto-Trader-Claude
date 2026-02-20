#!/bin/bash

# Monitor para sistema de 18 cores
# Verifica Air y Pro en tiempo real

LOG_FILE="monitor_18_cores.log"

echo "🤖 MONITOR 18 CORES INICIADO" | tee -a "$LOG_FILE"
echo "$(date)" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

while true; do
    clear
    timestamp=$(date '+%H:%M:%S')

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 SISTEMA 18 CORES - MONITOR EN TIEMPO REAL"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⏰ $timestamp"
    echo ""

    # MacBook Air
    echo "💻 MacBook Air:"
    air_cores=$(ps aux | grep "ray::run_backtest_task" | grep -v grep | wc -l | tr -d ' ')
    air_cpu=$(ps aux | grep "ray::run_backtest_task" | grep -v grep | awk '{sum+=$3} END {printf "%.0f", sum}')

    if [ "$air_cores" -gt 0 ]; then
        echo "   ✅ ACTIVO - $air_cores cores @ ${air_cpu}% CPU"
    else
        echo "   ⏸️  IDLE - 0 cores activos"
    fi

    # Progreso Air
    air_progress=$(tail -50 worker_air.log 2>/dev/null | grep -E "Gen [0-9]+/" | tail -1)
    if [ -n "$air_progress" ]; then
        echo "   📈 $air_progress"
    fi

    echo ""

    # MacBook Pro (verificar vía Tailscale)
    echo "💻 MacBook Pro:"
    pro_status=$(curl -s --max-time 2 http://100.118.215.73:5001/api/workers 2>/dev/null | grep -c "MacBook-Pro")

    if [ "$pro_status" -gt 0 ]; then
        echo "   ✅ CONECTADO al coordinator"
        # Intentar verificar cores (esto solo funcionará si tenemos acceso)
        echo "   📊 Verificando cores..."
    else
        echo "   ⏳ ESPERANDO INICIO"
        echo "   💡 Ejecuta: start_pro_worker.command"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Total
    total_cores=$air_cores
    total_cpu="${air_cpu}"

    echo "📊 TOTALES:"
    echo "   Cores activos: $total_cores / 18"
    echo "   CPU total: ${total_cpu}%"

    if [ "$total_cores" -eq 18 ]; then
        echo "   🎉 SISTEMA COMPLETO ACTIVO!"
    fi

    echo ""
    echo "Presiona Ctrl+C para salir | Actualización cada 5s"

    # Log
    echo "$timestamp | Air:$air_cores cores@${air_cpu}% | Pro:$pro_status connected" >> "$LOG_FILE"

    sleep 5
done
