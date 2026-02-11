#!/bin/bash
#
# ⏰ CRON JOBS PARA AUTO-MEJOR CONTINUA
# Schedule automático para el sistema de trading
#
# Esta configuración ejecuta:
# - Domingo 00:00 UTC: Ciclo completo de auto-mejora
# - Domingo 01:00 UTC: Backup automático
# - Cada hora: Health check del sistema
# - Cada 6 horas: Verificación de workers
#

# Configurar timezone
export TZ=UTC

# Paths del proyecto
PROJECT_DIR="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
PYTHON_BIN="/opt/homebrew/bin/python3"
LOG_DIR="$PROJECT_DIR/logs"

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

# ==================== CRON CONFIGURATION ====================
# Copiar este contenido a crontab: crontab -e

# ┌───────────── minute (0 - 59)
# │ ┌───────────── hour (0 - 23)
# │ │ ┌───────────── day of month (1 - 31)
# │ │ │ ┌───────────── month (1 - 12)
# │ │ │ │ ┌───────────── day of week (0 - 6) (Sunday=0)
# │ │ │ │ │
# ↓ ↓ ↓ ↓ ↓

# --- DOMINGO: DÍA DE AUTO-MEJOR ---
# 00:00 UTC - Iniciar ciclo de auto-mejora completo
0 0 * * 0 cd "$PROJECT_DIR" && $PYTHON_BIN auto_improvement_system.py --run >> "$LOG_DIR/auto_improvement.log" 2>&1

# 01:00 UTC - Backup automático después de actualización
0 1 * * 0 cd "$PROJECT_DIR" && bash auto_backup_hourly.sh >> "$LOG_DIR/backup.log" 2>&1

# --- CADA HORA: Health Check ---
# * * * * * cd "$PROJECT_DIR" && $PYTHON_BIN health_check.py >> "$LOG_DIR/health.log" 2>&1

# --- CADA 6 HORAS: Verificación de Workers ---
0 */6 * * * cd "$PROJECT_DIR" && $PYTHON_BIN autonomous_maintainer.py --once >> "$LOG_DIR/worker_maintenance.log" 2>&1

# --- CADA DÍA: Reporte de performance ---
0 23 * * * cd "$PROJECT_DIR" && $PYTHON_BIN daily_report.py >> "$LOG_DIR/daily_report.log" 2>&1

# --- LUNES 02:00 UTC: Verificación post-fin de semana ---
0 2 * * 1 cd "$PROJECT_DIR" && $PYTHON_BIN weekly_verification.py >> "$LOG_DIR/weekly_verify.log" 2>&1

# ==================== INSTALACIÓN ====================
# Para instalar estos cron jobs:
#
# 1. Editar crontab:
#    crontab -e
#
# 2. Copiar las líneas de arriba (quitando los comentarios #)
#
# 3. Verificar instalación:
#    crontab -l
#
# 4. Asegurar que cron está corriendo:
#    (macOS)
#    sudo cron start
#    sudo cron restart
#
#    (Linux)
#    sudo systemctl enable cron
#    sudo systemctl start cron

# ==================== COMANDOS MANUALES ====================

# Ver cron jobs instalados
function show_crons() {
    echo "=== CRON JOBS INSTALADOS ==="
    crontab -l 2>/dev/null || echo "No hay cron jobs instalados"
}

# Ver logs recientes
function show_logs() {
    echo "=== LOGS RECIENTES ==="
    echo ""
    echo "Auto-Improvement:"
    tail -20 "$LOG_DIR/auto_improvement.log" 2>/dev/null || echo "No hay logs"
    echo ""
    echo "Workers:"
    tail -20 "$LOG_DIR/worker_maintenance.log" 2>/dev/null || echo "No hay logs"
}

# Verificar estado del sistema
function system_status() {
    echo "=== ESTADO DEL SISTEMA ==="
    echo ""
    
    # Coordinator
    if curl -s http://localhost:5001/api/status > /dev/null 2>&1; then
        echo "✅ Coordinator: ONLINE"
    else
        echo "❌ Coordinator: OFFLINE"
    fi
    
    # Workers
    WORKERS=$(curl -s http://localhost:5001/api/status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['workers']['active'])" 2>/dev/null || echo "0")
    echo "👥 Workers activos: $WORKERS"
    
    # WUs
    curl -s http://localhost:5001/api/status 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f\"📦 Work Units: {d['work_units']['total']} (P:{d['work_units']['pending']}, I:{d['work_units']['in_progress']}, C:{d['work_units']['completed']})\")
" 2>/dev/null || echo "❌ No se pudo obtener estado"
}

# Reiniciar servicios
function restart_services() {
    echo "=== REINICIANDO SERVICIOS ==="
    
    # Restart coordinator
    pkill -f coordinator_port5001.py 2>/dev/null || true
    sleep 2
    cd "$PROJECT_DIR" && nohup python3 coordinator_port5001.py > "$LOG_DIR/coordinator.log" 2>&1 &
    echo "✅ Coordinator reiniciado"
    
    # Restart workers
    cd ~/.bittrader_worker && nohup bash worker_daemon.sh > "$LOG_DIR/workers.log" 2>&1 &
    echo "✅ Workers reiniciados"
    
    sleep 3
    system_status
}

# ==================== DOCKER/CONTAINER SETUP ====================
# Si usas Docker, el entrypoint sería:

# Dockerfile.entrypoint
# =====================
# FROM python:3.11-slim
#
# WORKDIR /app
# COPY . .
#
# RUN apt-get update && apt-get install -y cron && \
#     echo "0 0 * * 0 cd /app && python3 auto_improvement_system.py --run >> /var/log/auto_improvement.log 2>&1" >> /etc/crontab
#
# CMD ["sh", "-c", "service cron start && python3 coordinator.py"]
# =====================

# ==================== KUBERNETES (OPSIONAL) ====================
# Si usas K8s, el schedule sería:

# k8s-cronjob.yaml
# ================
# apiVersion: batch/v1
# kind: CronJob
# metadata:
#   name: auto-improvement-weekly
# spec:
#   schedule: "0 0 * * 0"
#   jobTemplate:
#     spec:
#       template:
#         spec:
#           containers:
#           - name: auto-improvement
#             image: trading-system:latest
#             command: ["python3", "auto_improvement_system.py", "--run"]
#           restartPolicy: OnFailure
# =====================

echo ""
echo "=== AUTO-MEJOR CONTINUA - CONFIGURACIÓN ==="
echo ""
echo "Para instalar cron jobs:"
echo "   1. Editar: crontab -e"
echo "   2. Copiar las líneas de arriba"
echo "   3. Guardar y salir"
echo ""
echo "Comandos disponibles:"
echo "   show_crons   - Ver cron jobs instalados"
echo "   show_logs   - Ver logs recientes"
echo "   system_status - Ver estado del sistema"
echo "   restart_services - Reiniciar todos los servicios"
echo ""
