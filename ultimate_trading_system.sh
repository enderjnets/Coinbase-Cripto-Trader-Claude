#!/bin/bash
#
# 🚀 ULTIMATE TRADING SYSTEM - SCRIPT PRINCIPAL
# Orchestrates all components of the trading system
#
# Usage:
#   ./ultimate_trading_system.sh [command]
#
# Commands:
#   start     - Start all services
#   stop      - Stop all services
#   status    - Check system status
#   download  - Download market data
#   train     - Train IA agent
#   paper     - Run paper trading
#   live      - Prepare for live trading
#   dashboard - Open dashboards
#   backup    - Backup database
#   logs      - View logs

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
PROJECT_DIR="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
COORDINATOR_DB="$PROJECT_DIR/coordinator.db"
DATA_DIR="$PROJECT_DIR/data"
LOG_DIR="$PROJECT_DIR/logs"

# Functions
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

header() {
    echo ""
    echo "============================================================"
    echo "🚀 ULTIMATE TRADING SYSTEM - $1"
    echo "============================================================"
}

# Command: start
cmd_start() {
    header "INICIANDO SISTEMA"
    
    print_info "Iniciando servicios..."
    
    # Start coordinator
    print_info "Iniciando Coordinator..."
    cd "$PROJECT_DIR"
    python3 coordinator_port5001.py > /dev/null 2>&1 &
    COORD_PID=$!
    print_status "Coordinator PID: $COORD_PID"
    
    # Start workers
    print_info "Iniciando Workers..."
    cd ~/.bittrader_worker
    bash worker_daemon.sh > /dev/null 2>&1 &
    WORKER_PID=$!
    print_status "Workers iniciados"
    
    print_status "Sistema iniciado correctamente"
}

# Command: stop
cmd_stop() {
    header "DETENIENDO SISTEMA"
    
    print_info "Deteniendo servicios..."
    
    # Kill coordinator
    pkill -f coordinator_port5001.py 2>/dev/null || true
    print_status "Coordinator detenido"
    
    # Kill workers
    pkill -f crypto_worker.py 2>/dev/null || true
    print_status "Workers detenidos"
    
    print_status "Sistema detenido correctamente"
}

# Command: status
cmd_status() {
    header "ESTADO DEL SISTEMA"
    
    # Check coordinator
    print_info "Verificando Coordinator..."
    if curl -s http://localhost:5001/api/status > /dev/null 2>&1; then
        DATA=$(curl -s http://localhost:5001/api/status)
        WORKERS=$(echo $DATA | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"workers\"][\"active\"]}')")
        WUS=$(echo $DATA | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"work_units\"][\"completed\"]}')")
        PNL=$(echo $DATA | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"best_strategy\"][\"pnl\"]:.2f}')")
        
        echo ""
        echo "📊 COORDINATOR STATUS:"
        echo "   👥 Workers Activos: $WORKERS"
        echo "   📦 WUs Completados: $WUS"
        echo "   💰 Mejor PnL: \$$PNL"
    else
        print_warning "Coordinator no responde"
    fi
    
    # Check database
    echo ""
    print_info "Verificando Base de Datos..."
    if [ -f "$COORDINATOR_DB" ]; then
        RESULTS=$(sqlite3 "$COORDINATOR_DB" "SELECT COUNT(*) FROM results" 2>/dev/null || echo "0")
        print_status "Resultados: $RESULTS"
    else
        print_error "Base de datos no encontrada"
    fi
    
    # Check data
    echo ""
    print_info "Verificando Datos..."
    if [ -d "$DATA_DIR" ]; then
        FILES=$(ls -1 "$DATA_DIR"/*.csv 2>/dev/null | wc -l)
        print_status "Archivos de datos: $FILES"
    else
        print_error "Directorio de datos no existe"
    fi
}

# Command: download
cmd_download() {
    header "DESCARGANDO DATOS"
    
    print_info "Iniciando descarga de datos..."
    cd "$PROJECT_DIR"
    python3 complete_data_downloader.py
}

# Command: train
cmd_train() {
    header "ENTRENANDO AGENTE IA"
    
    print_info "Iniciando entrenamiento..."
    cd "$PROJECT_DIR"
    python3 ia_trading_agent_v2.py
}

# Command: paper
cmd_paper() {
    header "PAPER TRADING"
    
    print_info "Iniciando paper trading..."
    cd "$PROJECT_DIR"
    python3 paper_trading_system.py
}

# Command: live
cmd_live() {
    header "LIVE TRADING"
    
    print_warning "ADVERTENCIA: Trading con dinero real"
    cd "$PROJECT_DIR"
    python3 live_trading_system.py
}

# Command: dashboard
cmd_dashboard() {
    header "DASHBOARDS"
    
    echo ""
    echo "📊 Dashboards disponibles:"
    echo ""
    echo "   [1] Coordinator (Puerto 5001)"
    echo "   [2] F1 Dashboard (Puerto 5006)"
    echo "   [3] Streamlit Interface (Puerto 8501)"
    echo ""
    
    read -p "👉 Elige un dashboard (1-3): " choice
    
    case $choice in
        1)
            echo ""
            print_info "Abriendo: http://localhost:5001"
            open http://localhost:5001
            ;;
        2)
            echo ""
            print_info "Abriendo: http://localhost:5006"
            open http://localhost:5006
            ;;
        3)
            echo ""
            print_info "Abriendo: http://localhost:8501"
            open http://localhost:8501
            ;;
        *)
            print_error "Opción inválida"
            ;;
    esac
}

# Command: backup
cmd_backup() {
    header "RESPALDANDO"
    
    print_info "Creando respaldo..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="$PROJECT_DIR/backups"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    if [ -f "$COORDINATOR_DB" ]; then
        cp "$COORDINATOR_DB" "$BACKUP_DIR/coordinator_$TIMESTAMP.db"
        print_status "Base de datos respaldada"
    fi
    
    # Backup models
    if [ -f "$PROJECT_DIR/ia_trading_agent_model.json" ]; then
        cp "$PROJECT_DIR/ia_trading_agent_model.json" "$BACKUP_DIR/"
        print_status "Modelo IA respaldado"
    fi
    
    echo ""
    print_status "Respaldo completado: $BACKUP_DIR"
}

# Command: logs
cmd_logs() {
    header "LOGS"
    
    echo ""
    echo "📝 Últimas 50 líneas del log:"
    echo ""
    tail -50 /tmp/coordinator.log 2>/dev/null || echo "No hay logs disponibles"
}

# Main
case "$1" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    status)
        cmd_status
        ;;
    download)
        cmd_download
        ;;
    train)
        cmd_train
        ;;
    paper)
        cmd_paper
        ;;
    live)
        cmd_live
        ;;
    dashboard)
        cmd_dashboard
        ;;
    backup)
        cmd_backup
        ;;
    logs)
        cmd_logs
        ;;
    help|"")
        echo ""
        echo "============================================================"
        echo "🚀 ULTIMATE TRADING SYSTEM - AYUDA"
        echo "============================================================"
        echo ""
        echo "Comandos disponibles:"
        echo ""
        echo "   start     - Iniciar todos los servicios"
        echo "   stop      - Detener todos los servicios"
        echo "   status    - Verificar estado del sistema"
        echo "   download  - Descargar datos de mercado"
        echo "   train     - Entrenar agente IA"
        echo "   paper     - Ejecutar paper trading"
        echo "   live      - Preparar live trading"
        echo "   dashboard - Abrir dashboards"
        echo "   backup    - Respaldar base de datos"
        echo "   logs      - Ver logs"
        echo "   help      - Mostrar esta ayuda"
        echo ""
        ;;
    *)
        print_error "Comando desconocido: $1"
        echo "Usa: ./ultimate_trading_system.sh help"
        ;;
esac
