#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# EJECUTAR ESTE SCRIPT EN EL MacBook Pro (WORKER)
# ═══════════════════════════════════════════════════════════════

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║    🔄 REINICIANDO WORKER - CARGAR CÓDIGO CORREGIDO       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. Detener Ray
echo -e "${YELLOW}[1/3]${NC} Deteniendo Ray worker..."

if [ -f "$HOME/.bittrader_worker/venv/bin/ray" ]; then
    "$HOME/.bittrader_worker/venv/bin/ray" stop --force
    echo -e "   ${GREEN}✅ Worker detenido${NC}"
else
    echo -e "   ${YELLOW}⚠️  Ruta ~/.bittrader_worker/venv no encontrada${NC}"
    echo -e "   Buscando Ray en el sistema..."

    # Buscar en Google Drive
    RAY_PATH=$(find "$HOME/Library/CloudStorage" -name "ray" -path "*/bin/ray" 2>/dev/null | grep "Coinbase Cripto Trader" | head -1)

    if [ -n "$RAY_PATH" ]; then
        echo -e "   ${GREEN}✅ Encontrado en: $RAY_PATH${NC}"
        "$RAY_PATH" stop --force
    else
        # Intentar con ray global
        ray stop --force 2>/dev/null && echo -e "   ${GREEN}✅ Ray global detenido${NC}" || echo -e "   ${RED}❌ No se pudo detener Ray${NC}"
    fi
fi

echo ""

# 2. Limpiar caché de Python
echo -e "${YELLOW}[2/3]${NC} Limpiando caché de Python..."

# Buscar y eliminar archivos .pyc en el proyecto
PROJECT_DIR="$HOME/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

if [ -d "$PROJECT_DIR" ]; then
    echo -e "   ${BLUE}Limpiando $PROJECT_DIR${NC}"
    find "$PROJECT_DIR" -name "*.pyc" -delete 2>/dev/null
    find "$PROJECT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
    echo -e "   ${GREEN}✅ Caché limpiado${NC}"
else
    echo -e "   ${YELLOW}⚠️  Proyecto no encontrado en Google Drive${NC}"
fi

# Limpiar también en ~/.bittrader_worker si existe
if [ -d "$HOME/.bittrader_worker" ]; then
    find "$HOME/.bittrader_worker" -name "*.pyc" -delete 2>/dev/null
    find "$HOME/.bittrader_worker" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
fi

echo ""

# 3. Reiniciar Ray
echo -e "${YELLOW}[3/3]${NC} Reiniciando Ray worker..."
echo -e "   ${BLUE}El daemon lo reiniciará automáticamente en ~30-60 segundos${NC}"
echo ""
echo -e "   O reinicia manualmente AHORA con:"
echo ""
echo -e "   ${GREEN}~/.bittrader_worker/venv/bin/ray start \\${NC}"
echo -e "   ${GREEN}    --address=100.118.215.73:6379 \\${NC}"
echo -e "   ${GREEN}    --num-cpus=12${NC}"
echo ""

# Preguntar si quiere reiniciar ahora
read -p "   ¿Reiniciar ahora? (s/N): " RESTART_NOW

if [[ "$RESTART_NOW" =~ ^[Ss]$ ]]; then
    echo ""
    echo -e "   ${BLUE}Iniciando Ray worker...${NC}"

    if [ -f "$HOME/.bittrader_worker/venv/bin/ray" ]; then
        "$HOME/.bittrader_worker/venv/bin/ray" start \
            --address=100.118.215.73:6379 \
            --num-cpus=12 \
            --object-store-memory=2000000000

        if [ $? -eq 0 ]; then
            echo -e "   ${GREEN}✅ Worker reiniciado exitosamente${NC}"
        else
            echo -e "   ${RED}❌ Error al reiniciar worker${NC}"
        fi
    else
        echo -e "   ${RED}❌ No se encontró ray en ~/.bittrader_worker/venv/bin/${NC}"
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ PROCESO COMPLETADO${NC}"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}📊 VERIFICACIÓN (desde MacBook Air - Head Node):${NC}"
echo ""
echo "   .venv/bin/ray status"
echo ""
echo "Deberías ver:"
echo "   ${GREEN}Active: 2 nodes${NC}"
echo "   ${GREEN}Resources: 0.0/22.0 CPU${NC}"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
