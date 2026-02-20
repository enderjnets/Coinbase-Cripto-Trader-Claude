#!/bin/bash
#
# 🚀 SCRIPT DE INICIO RÁPIDO
# Ejecuta todo el sistema de trading en modo autónomo
#

echo "========================================"
echo "  🚀 SISTEMA COMPLETO DE TRADING v1.0"
echo "========================================"
echo ""
echo "💰 Capital: \$500"
echo "🎯 Objetivo: 5% diario"
echo "📊 Timeframes: 1m, 5m, 15m, 30m, 1h"
echo "🪙 Activos: Top 30 por liquidez"
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"; }
log_success() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')]${NC} $1"; }
log_error() { echo -e "${RED}[$(date '+%H:%M:%S')${NC} ERROR: $1"; }

# Directorio del proyecto
PROJECT_DIR="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
cd "$PROJECT_DIR"

echo "📂 Directorio: $PROJECT_DIR"
echo ""

# Función para ejecutar paso
ejecutar_paso() {
    local nombre=$1
    local comando=$2
    
    echo ""
    log_info "Ejecutando: $nombre"
    echo "Command: $comando"
    echo ""
    
    eval $comando
    
    if [ $? -eq 0 ]; then
        log_success "✅ $nombre completado"
        return 0
    else
        log_error "❌ Error en $nombre"
        return 1
    fi
}

# Menú
echo "========================================"
echo "  📋 MENÚ DE OPCIONES"
echo "========================================"
echo ""
echo "1. 🚀 Ejecutar TODO el sistema (recomendado)"
echo "2. 📥 Solo descargar datos"
echo "3. 🧬 Solo generar Work Units"
echo "4. 🧠 Solo entrenar IA"
echo "5. 📊 Ver estado del sistema"
echo "6. 🎯 Ejecutar modo autónomo continuo"
echo "7. 🚪 Salir"
echo ""
read -p "Selecciona una opción [1-7]: " opcion

case $opcion in
    1)
        echo ""
        log_info "MODO: EJECUTAR TODO EL SISTEMA"
        echo ""
        
        # Paso 1: Descargar datos
        ejecutar_paso "DESCARGA DE DATOS" "python3 download_multi_data.py" || exit 1
        
        sleep 5
        
        # Paso 2: Generar Work Units
        ejecutar_paso "WORK UNITS OPTIMIZADOS" "python3 generate_optimized_wus.py" || exit 1
        
        sleep 3
        
        # Paso 3: Entrenar IA
        ejecutar_paso "ENTRENAR IA" "python3 ia_trading_agent.py --train" || exit 1
        
        sleep 3
        
        # Resumen
        echo ""
        log_success "========================================"
        log_success "  ✅ SISTEMA COMPLETADO"
        log_success "========================================"
        echo ""
        echo "📊 Resumen:"
        echo "   - Datos: Descargados"
        echo "   - Work Units: Generados"
        echo "   - IA: Entrenada"
        echo ""
        echo "🚀 Para ejecutar trading automático:"
        echo "   python3 ia_trading_agent.py --trade"
        ;;
    
    2)
        ejecutar_paso "DESCARGA DE DATOS" "python3 download_multi_data.py"
        ;;
    
    3)
        ejecutar_paso "WORK UNITS" "python3 generate_optimized_wus.py"
        ;;
    
    4)
        ejecutar_paso "ENTRENAR IA" "python3 ia_trading_agent.py --train"
        ;;
    
    5)
        echo ""
        log_info "ESTADO DEL SISTEMA"
        echo ""
        
        echo "📥 Archivos descargados:"
        ls -la data_multi/*.csv 2>/dev/null | wc -l
        echo ""
        
        echo "🧬 Work Units:"
        sqlite3 coordinator.db "SELECT COUNT(*) FROM work_units" 2>/dev/null || echo "   No disponible"
        echo ""
        
        echo "🤖 Workers activos:"
        sqlite3 coordinator.db "SELECT COUNT(*) FROM workers WHERE (julianday('now') - last_seen) < (10.0/1440.0)" 2>/dev/null || echo "   No disponible"
        ;;
    
    6)
        log_info "MODO AUTÓNOMO CONTINUO"
        echo ""
        log_warn "Ejecutando en bucle infinito..."
        log_warn "Presiona Ctrl+C para detener"
        echo ""
        
        while true; do
            python3 master_orchestrator.py --mode full
            log_warn "Ciclo completado. Esperando 1 hora..."
            sleep 3600
        done
        ;;
    
    7)
        echo "👋 ¡Hasta luego!"
        exit 0
        ;;
    
    *)
        echo "❌ Opción inválida: $opcion"
        exit 1
        ;;
esac
