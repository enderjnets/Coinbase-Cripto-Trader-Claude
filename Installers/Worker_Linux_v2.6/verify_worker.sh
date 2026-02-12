#!/bin/bash
#
# Bittrader Worker Verification Script - Linux Edition
#

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="$HOME/.bittrader_worker"

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      Bittrader Worker Verification (Linux)                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

ERRORS=0

# Check installation
echo -e "${YELLOW}[1/5]${NC} Checking installation..."
if [ -d "$INSTALL_DIR" ]; then
    echo -e "   ${GREEN}✅ Installation directory exists${NC}"
else
    echo -e "   ${RED}❌ Not installed${NC}"
    exit 1
fi

# Check Python
echo ""
echo -e "${YELLOW}[2/5]${NC} Checking Python..."
if [ -f "$INSTALL_DIR/venv/bin/python" ]; then
    PYTHON_VERSION=$("$INSTALL_DIR/venv/bin/python" --version 2>&1 | cut -d' ' -f2)
    echo -e "   ${GREEN}✅ Python version: $PYTHON_VERSION${NC}"
else
    echo -e "   ${RED}❌ Python not found in venv${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check Ray
echo ""
echo -e "${YELLOW}[3/5]${NC} Checking Ray..."
if [ -f "$INSTALL_DIR/venv/bin/ray" ]; then
    echo -e "   ${GREEN}✅ Ray installed${NC}"
else
    echo -e "   ${RED}❌ Ray not installed${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check configuration
echo ""
echo -e "${YELLOW}[4/5]${NC} Checking configuration..."
if [ -f "$INSTALL_DIR/config.env" ]; then
    source "$INSTALL_DIR/config.env"
    echo -e "   ${GREEN}✅ Configuration found${NC}"
    echo -e "      Head Node IP: $HEAD_IP"
else
    echo -e "   ${RED}❌ config.env not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check Ray status
echo ""
echo -e "${YELLOW}[5/5]${NC} Checking Ray status..."
if pgrep -x "raylet" > /dev/null; then
    echo -e "   ${GREEN}✅ Ray worker is running${NC}"
else
    echo -e "   ${RED}❌ Ray worker not running${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    SUMMARY                                   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Logs: $INSTALL_DIR/logs/worker.log"
    echo "Monitor: tail -f $INSTALL_DIR/logs/worker.log"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Found $ERRORS error(s)${NC}"
    echo ""
    echo "Check logs: tail -50 $INSTALL_DIR/logs/worker.log"
    echo ""
    exit 1
fi
