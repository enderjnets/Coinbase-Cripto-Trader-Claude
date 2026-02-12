#!/bin/bash
#
# 🗑️ Bittrader Worker Uninstaller
# Removes all worker components from your Mac
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="$HOME/.bittrader_worker"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo ""
echo -e "${YELLOW}🗑️  Bittrader Worker Uninstaller${NC}"
echo ""

read -p "¿Estás seguro de que quieres desinstalar el worker? (s/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Ss]$ ]]; then
    echo "Cancelado."
    exit 0
fi

echo ""
echo "Deteniendo servicios..."

# Stop Ray
ray stop 2>/dev/null || true

# Unload launch agents
launchctl unload "$LAUNCH_AGENTS_DIR/com.bittrader.worker.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.bittrader.throttle.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.bittrader.status.plist" 2>/dev/null || true

echo "Eliminando archivos..."

# Remove plist files
rm -f "$LAUNCH_AGENTS_DIR/com.bittrader.worker.plist"
rm -f "$LAUNCH_AGENTS_DIR/com.bittrader.throttle.plist"
rm -f "$LAUNCH_AGENTS_DIR/com.bittrader.status.plist"

# Remove install directory
rm -rf "$INSTALL_DIR"

echo ""
echo -e "${GREEN}✅ Desinstalación completada.${NC}"
echo ""
echo "Nota: Tailscale no fue desinstalado."
echo "Si deseas removerlo, usa: brew uninstall tailscale"
echo ""

# Show notification
osascript -e 'display notification "Worker desinstalado correctamente" with title "Bittrader Worker" sound name "Basso"' 2>/dev/null || true
