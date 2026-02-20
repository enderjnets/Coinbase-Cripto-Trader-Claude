#!/bin/bash
# Instalar daemons de SSH Tunnel y Worker Ray

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKER_DIR="$HOME/.bittrader_worker"

echo "=========================================="
echo "Instalando Bittrader Worker Daemons"
echo "=========================================="
echo ""

# Verificar que el worker esté instalado
if [ ! -f "$WORKER_DIR/config.env" ]; then
    echo "❌ Error: Worker no está instalado"
    echo "   Ejecuta primero: ./install.sh"
    exit 1
fi

# Copiar scripts al directorio del worker
echo "📁 Copiando scripts..."
cp "$SCRIPT_DIR/ssh_tunnel_daemon.sh" "$WORKER_DIR/"
cp "$SCRIPT_DIR/worker_daemon.sh" "$WORKER_DIR/"
chmod +x "$WORKER_DIR/ssh_tunnel_daemon.sh"
chmod +x "$WORKER_DIR/worker_daemon.sh"

# Crear plist para SSH Tunnel
echo ""
echo "🔐 Creando daemon SSH Tunnel..."
cat > "$HOME/Library/LaunchAgents/com.bittrader.ssh_tunnel.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bittrader.ssh_tunnel</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$WORKER_DIR/ssh_tunnel_daemon.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$WORKER_DIR/logs/ssh_tunnel_daemon.log</string>

    <key>StandardErrorPath</key>
    <string>$WORKER_DIR/logs/ssh_tunnel_daemon_error.log</string>

    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
EOF

# Crear plist para Worker Ray
echo "🐍 Creando daemon Worker Ray..."
cat > "$HOME/Library/LaunchAgents/com.bittrader.worker.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bittrader.worker</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$WORKER_DIR/worker_daemon.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$WORKER_DIR/logs/worker_daemon.log</string>

    <key>StandardErrorPath</key>
    <string>$WORKER_DIR/logs/worker_daemon_error.log</string>

    <key>ThrottleInterval</key>
    <integer>15</integer>
</dict>
</plist>
EOF

# Cargar daemons
echo ""
echo "🚀 Activando daemons..."

# Descargar si ya existen
launchctl unload "$HOME/Library/LaunchAgents/com.bittrader.ssh_tunnel.plist" 2>/dev/null || true
launchctl unload "$HOME/Library/LaunchAgents/com.bittrader.worker.plist" 2>/dev/null || true

# Cargar nuevos
launchctl load "$HOME/Library/LaunchAgents/com.bittrader.ssh_tunnel.plist"
launchctl load "$HOME/Library/LaunchAgents/com.bittrader.worker.plist"

echo ""
echo "=========================================="
echo "✅ Daemons instalados y activados"
echo "=========================================="
echo ""
echo "📋 Estado:"
echo "   - SSH Tunnel: activo (conectando a Head)"
echo "   - Worker Ray: activo (esperando tunnel)"
echo ""
echo "📝 Ver logs:"
echo "   tail -f ~/.bittrader_worker/logs/ssh_tunnel.log"
echo "   tail -f ~/.bittrader_worker/logs/worker.log"
echo ""
echo "⏸️  Detener daemons:"
echo "   launchctl unload ~/Library/LaunchAgents/com.bittrader.ssh_tunnel.plist"
echo "   launchctl unload ~/Library/LaunchAgents/com.bittrader.worker.plist"
echo ""
echo "▶️  Reiniciar daemons:"
echo "   launchctl load ~/Library/LaunchAgents/com.bittrader.ssh_tunnel.plist"
echo "   launchctl load ~/Library/LaunchAgents/com.bittrader.worker.plist"
echo ""
