#!/bin/bash
#
# 🔍 Bittrader Worker Verification Script
# Run this on the worker machine to diagnose setup issues
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="$HOME/.bittrader_worker"

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       🔍 BITTRADER WORKER - VERIFICACIÓN                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Track overall status
ERRORS=0
WARNINGS=0

# 1. Check Installation
echo -e "${YELLOW}[1/7]${NC} Verificando instalación..."
if [ -d "$INSTALL_DIR" ]; then
    echo -e "   ✅ Directorio de instalación existe: $INSTALL_DIR"
else
    echo -e "   ${RED}❌ Directorio de instalación no encontrado${NC}"
    echo -e "      Ejecuta: bash install.sh"
    ERRORS=$((ERRORS + 1))
    exit 1
fi

# 2. Check Python Version
echo ""
echo -e "${YELLOW}[2/7]${NC} Verificando Python..."
if [ -f "$INSTALL_DIR/venv/bin/python" ]; then
    PYTHON_VERSION=$("$INSTALL_DIR/venv/bin/python" --version 2>&1 | cut -d' ' -f2)
    MAJOR_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1-2)

    if [ "$MAJOR_MINOR" == "3.9" ]; then
        echo -e "   ✅ Python version: $PYTHON_VERSION"

        if [ "$PYTHON_VERSION" != "3.9.6" ]; then
            echo -e "   ${YELLOW}⚠️  Head Node usa 3.9.6, Worker usa $PYTHON_VERSION${NC}"
            echo -e "      Esto puede causar problemas. Ver TROUBLESHOOTING.txt"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo -e "   ${RED}❌ Versión incorrecta: $PYTHON_VERSION (necesitas 3.9.x)${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "   ${RED}❌ Python no encontrado en venv${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 3. Check Ray Installation
echo ""
echo -e "${YELLOW}[3/7]${NC} Verificando Ray..."
if [ -f "$INSTALL_DIR/venv/bin/ray" ]; then
    RAY_VERSION=$("$INSTALL_DIR/venv/bin/ray" --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -1)
    echo -e "   ✅ Ray version: $RAY_VERSION"

    # Test Ray import
    if "$INSTALL_DIR/venv/bin/python" -c "import ray; print('✅ Ray importado correctamente')" 2>/dev/null; then
        echo -e "   ✅ Ray importado correctamente"
    else
        echo -e "   ${RED}❌ Error al importar Ray${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "   ${RED}❌ Ray no instalado${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 4. Check Configuration
echo ""
echo -e "${YELLOW}[4/7]${NC} Verificando configuración..."
if [ -f "$INSTALL_DIR/config.env" ]; then
    source "$INSTALL_DIR/config.env"
    echo -e "   ✅ Config encontrada"
    echo -e "      Head Node IP: $HEAD_IP"
    echo -e "      Tailscale IP: $TAILSCALE_IP"
else
    echo -e "   ${RED}❌ config.env no encontrado${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 5. Check Connectivity to Head Node
echo ""
echo -e "${YELLOW}[5/7]${NC} Verificando conectividad..."
if [ -n "$HEAD_IP" ]; then
    echo -e "   Probando ping a $HEAD_IP..."
    if ping -c 2 -W 3 "$HEAD_IP" &> /dev/null; then
        echo -e "   ✅ Head Node alcanzable"
    else
        echo -e "   ${RED}❌ No se puede contactar al Head Node${NC}"
        echo -e "      1. Verifica que el Head Node esté corriendo"
        echo -e "      2. Verifica Tailscale: tailscale status"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "   ${YELLOW}⚠️  HEAD_IP no configurado${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 6. Check Project Code (Google Drive)
echo ""
echo -e "${YELLOW}[6/7]${NC} Verificando código del proyecto..."

# Search for project directory
PROJECT_DIR=$(find "$HOME/Library/CloudStorage" -type d -name "Coinbase Cripto Trader Claude" -print -quit 2>/dev/null)

if [ -z "$PROJECT_DIR" ]; then
    # Try wildcard
    PROJECT_DIR=$(find "$HOME/Library/CloudStorage" -type d -name "Coinbase Cripto Trader*" -print -quit 2>/dev/null)
fi

if [ -n "$PROJECT_DIR" ]; then
    echo -e "   ✅ Proyecto encontrado: $PROJECT_DIR"

    # Check critical files
    REQUIRED_FILES=("backtester.py" "dynamic_strategy.py" "optimizer.py" "strategy_miner.py")
    MISSING_FILES=()

    for file in "${REQUIRED_FILES[@]}"; do
        if [ -f "$PROJECT_DIR/$file" ]; then
            echo -e "      ✅ $file"
        else
            echo -e "      ${RED}❌ $file (falta)${NC}"
            MISSING_FILES+=("$file")
        fi
    done

    if [ ${#MISSING_FILES[@]} -gt 0 ]; then
        echo -e "   ${RED}❌ Archivos faltantes: ${MISSING_FILES[*]}${NC}"
        echo -e "      Espera a que Google Drive termine de sincronizar"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "   ✅ Todos los módulos críticos presentes"
    fi
else
    echo -e "   ${YELLOW}⚠️  Proyecto no encontrado en Google Drive${NC}"
    echo -e "      El worker usará Modo Universal (código vía Ray)"
    echo -e "      Esto puede causar ModuleNotFoundError - ver TROUBLESHOOTING.txt"
    WARNINGS=$((WARNINGS + 1))
fi

# 7. Check Worker Status
echo ""
echo -e "${YELLOW}[7/7]${NC} Verificando estado del worker..."

if pgrep -x "raylet" > /dev/null; then
    echo -e "   ✅ Ray worker corriendo (raylet activo)"

    # Try to get cluster status
    if "$INSTALL_DIR/venv/bin/ray" status 2>/dev/null | grep -q "Active:"; then
        echo -e "   ✅ Conectado al cluster"
        echo ""
        echo -e "${GREEN}   Cluster Status:${NC}"
        "$INSTALL_DIR/venv/bin/ray" status 2>/dev/null | head -15 | sed 's/^/      /'
    else
        echo -e "   ${YELLOW}⚠️  Ray corriendo pero no conectado al cluster${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "   ${RED}❌ Ray worker no está corriendo${NC}"
    echo -e "      Reinicia: launchctl start com.bittrader.worker"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       RESUMEN                                               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ ¡TODO PERFECTO! Worker configurado correctamente.${NC}"
    echo ""
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Worker funcional pero con advertencias ($WARNINGS)${NC}"
    echo -e "   Revisa los warnings arriba para optimizar el setup."
    echo ""
    exit 0
else
    echo -e "${RED}❌ Se encontraron $ERRORS errores y $WARNINGS advertencias${NC}"
    echo -e "   Revisa los mensajes arriba y consulta TROUBLESHOOTING.txt"
    echo ""
    echo -e "   Logs del worker:"
    echo -e "   tail -50 ~/.bittrader_worker/worker.log"
    echo ""
    exit 1
fi
