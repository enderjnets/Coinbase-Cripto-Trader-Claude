#!/bin/bash
# ============================================================================
# Auto Backup Script - Strategy Miner
# Ejecuta backups automáticos cada hora
# ============================================================================

PROJECT_DIR="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
VENV_DIR="$HOME/coinbase_trader_venv"
LOG_FILE="/tmp/auto_backup.log"

echo "========================================" >> $LOG_FILE
echo "$(date '+%Y-%m-%d %H:%M:%S') - Iniciando backup automático..." >> $LOG_FILE

# Activar venv y ejecutar backup
cd "$PROJECT_DIR"
source "$VENV_DIR/bin/activate"
python optimization_persistence.py >> $LOG_FILE 2>&1

# Verificar que se crearon los archivos
if [ -f "$PROJECT_DIR/optimization_history/statistics/snapshot_latest.json" ]; then
    echo "✅ Backup completado exitosamente" >> $LOG_FILE
else
    echo "❌ Error en backup" >> $LOG_FILE
fi

echo "----------------------------------------" >> $LOG_FILE
