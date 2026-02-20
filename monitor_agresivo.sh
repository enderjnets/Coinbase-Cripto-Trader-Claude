#!/bin/bash

# MONITOR AGRESIVO - Modo Peligrosamente Autónomo
# Sin permisos, actúa inmediatamente ante cualquier problema

LOG_FILE="monitor_agresivo.log"
WORKER_LOG="worker_air.log"
CHECK_INTERVAL=120  # Verificar cada 2 minutos

echo "🤖 MODO PELIGROSAMENTE AUTÓNOMO ACTIVADO" | tee -a "$LOG_FILE"
echo "⏰ $(date)" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

iteration=0

while true; do
    iteration=$((iteration + 1))
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
    echo "📊 ITERACIÓN #$iteration - $timestamp" | tee -a "$LOG_FILE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

    # 1. Verificar Ray workers
    ray_count=$(ps aux | grep "ray::run_backtest_task" | grep -v grep | wc -l | tr -d ' ')

    if [ "$ray_count" -eq 0 ]; then
        echo "❌ CRÍTICO: Ray workers caídos - REINICIANDO INMEDIATAMENTE" | tee -a "$LOG_FILE"
        pkill -9 -f "crypto_worker"
        pkill -9 -f "ray::"
        rm -rf /tmp/ray* 2>/dev/null
        sleep 5
        echo "✅ Reinicio completado - daemon levantará worker" | tee -a "$LOG_FILE"
    elif [ "$ray_count" -lt 7 ]; then
        echo "⚠️  WARNING: Solo $ray_count workers (esperado 9) - REINICIANDO" | tee -a "$LOG_FILE"
        pkill -9 -f "crypto_worker"
        sleep 5
        echo "✅ Reinicio preventivo completado" | tee -a "$LOG_FILE"
    else
        echo "✅ Ray Workers: $ray_count activos" | tee -a "$LOG_FILE"

        # CPU usage
        cpu_total=$(ps aux | grep "ray::run_backtest_task" | grep -v grep | awk '{sum+=$3} END {printf "%.0f", sum}')
        echo "💻 CPU Total: ${cpu_total}%" | tee -a "$LOG_FILE"

        if [ -n "$cpu_total" ] && [ "$cpu_total" -lt 300 ]; then
            echo "⚠️  CPU bajo - posible problema de rendimiento" | tee -a "$LOG_FILE"
        fi
    fi

    # 2. Verificar progreso
    last_gen=$(tail -100 "$WORKER_LOG" 2>/dev/null | grep -E "Gen [0-9]+/100" | tail -1)
    if [ -n "$last_gen" ]; then
        echo "📈 Progreso: $last_gen" | tee -a "$LOG_FILE"
    fi

    # 3. Detectar raylet crashes
    raylet_errors=$(tail -50 "$WORKER_LOG" 2>/dev/null | grep -c "raylet died")
    if [ "$raylet_errors" -gt 5 ]; then
        echo "❌ Múltiples raylet crashes detectados ($raylet_errors) - ACCIÓN CORRECTIVA" | tee -a "$LOG_FILE"

        # Reducir población si hay muchos crashes
        python3 << 'EOF'
import sqlite3, json
conn = sqlite3.connect('coordinator.db')
cursor = conn.cursor()
cursor.execute('SELECT id, strategy_params FROM work_units WHERE id=9')
unit_id, params_str = cursor.fetchone()
params = json.loads(params_str)
current_pop = params.get('population_size', 30)
if current_pop > 20:
    params['population_size'] = max(20, current_pop - 5)
    cursor.execute('UPDATE work_units SET strategy_params=? WHERE id=?',
                   (json.dumps(params), unit_id))
    conn.commit()
    print(f"Población reducida a {params['population_size']}")
conn.close()
EOF

        pkill -9 -f "crypto_worker"
        sleep 5
        echo "✅ Configuración ajustada y worker reiniciado" | tee -a "$LOG_FILE"
    fi

    # 4. Verificar coordinator
    coordinator_status=$(curl -s http://localhost:5001/api/status 2>/dev/null | grep -c "running")
    if [ "$coordinator_status" -eq 0 ]; then
        echo "❌ Coordinator no responde - REINICIANDO" | tee -a "$LOG_FILE"
        pkill -f coordinator_server.py
        sleep 2
        cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
        nohup python3 coordinator_server.py > coordinator.log 2>&1 &
        sleep 3
        echo "✅ Coordinator reiniciado" | tee -a "$LOG_FILE"
    fi

    echo "" | tee -a "$LOG_FILE"
    echo "⏳ Próxima verificación en ${CHECK_INTERVAL}s..." | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    sleep $CHECK_INTERVAL
done
