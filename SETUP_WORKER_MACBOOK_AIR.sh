#!/bin/bash
# Script de configuración completa para MacBook Air Worker
# Copiar este script al MacBook Air y ejecutarlo

set -e

echo "=========================================="
echo "BITTRADER WORKER - Configuración MacBook Air"
echo "=========================================="
echo ""

# Configuración
HEAD_IP="100.77.179.14"
HEAD_PORT="6379"
WORKER_DIR="$HOME/.bittrader_worker"
VENV_PATH="$WORKER_DIR/venv"

# 1. Verificar Python 3.9.6
echo "🔍 Verificando Python 3.9.6..."
if ! /Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9 --version | grep -q "3.9.6"; then
    echo "❌ Python 3.9.6 no encontrado"
    echo "Por favor instala desde: https://www.python.org/ftp/python/3.9.6/python-3.9.6-macosx10.9.pkg"
    exit 1
fi
echo "✅ Python 3.9.6 OK"

# 2. Verificar Tailscale
echo ""
echo "🔍 Verificando Tailscale..."
if ! tailscale status &>/dev/null; then
    echo "❌ Tailscale no está conectado"
    echo "Por favor inicia Tailscale primero"
    exit 1
fi
echo "✅ Tailscale OK"

# 3. Configurar SSH
echo ""
echo "🔐 Configurando SSH..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Generar clave si no existe
if [ ! -f ~/.ssh/id_ed25519 ]; then
    echo "Generando clave SSH..."
    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "bittrader-worker-air"
fi

# Agregar clave del Head
echo "Agregando clave pública del Head..."
cat >> ~/.ssh/authorized_keys <<'HEADKEY'
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPZ0OwCoG7tqKDiZg7ii0XJy775OC3ir5vuMmgOyAN2p bittrader-head-mbpro
HEADKEY
chmod 600 ~/.ssh/authorized_keys

# Copiar clave privada del Head para conectarnos de vuelta
cat > ~/.ssh/id_bittrader_head <<'HEADPRIVKEY'
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACD2dDsAqBu7aig4mYO4otFycve+Tgt4q+b7jJoADsgDagAAAJhR6bHlUemx
5QAAAAtzc2gtZWQyNTUxOQAAACD2dDsAqBu7aig4mYO4otFycve+Tgt4q+b7jJoADsgDag
AAAEBBP6dWi5d8pxK0Z3hNQAJ/xFqHGGi5s3QEd5Fm0+g8N/Z0OwCoG7tqKDiZg7ii0XJy
975OC3ir5vuMmgOyAN2pAAAAGmJpdHRyYWRlci1oZWFkLW1icHJvAAAABAIDBEU=
-----END OPENSSH PRIVATE KEY-----
HEADPRIVKEY
chmod 600 ~/.ssh/id_bittrader_head

# Agregar host key del Head
ssh-keyscan -H $HEAD_IP >> ~/.ssh/known_hosts 2>/dev/null

echo "✅ SSH configurado"

# 4. Crear directorio de instalación
echo ""
echo "📁 Creando directorio Worker..."
mkdir -p "$WORKER_DIR/logs"

# 5. Crear entorno virtual
echo ""
echo "🐍 Creando entorno virtual..."
rm -rf "$VENV_PATH"
/Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

# 6. Instalar Ray
echo ""
echo "📦 Instalando Ray 2.10.0..."
pip install --upgrade pip -q
pip install ray==2.10.0 -q

# 7. Detectar CPUs
NUM_CPUS=$(sysctl -n hw.ncpu)
echo "✅ Ray instalado - $NUM_CPUS CPUs detectados"
echo "$NUM_CPUS" > "$WORKER_DIR/current_cpus"

# 8. Crear configuración
cat > "$WORKER_DIR/config.env" <<EOF
HEAD_IP=$HEAD_IP
HEAD_PORT=$HEAD_PORT
NUM_CPUS=$NUM_CPUS
INSTALL_DATE=$(date)
WORKER_MODE=SSH_TUNNEL
RAY_VERSION=2.10.0
EOF

# 9. Crear daemon SSH Tunnel
echo ""
echo "🔐 Creando daemon SSH Tunnel..."
cat > "$WORKER_DIR/ssh_tunnel_daemon.sh" <<'SSHTUNNELEOF'
#!/bin/bash
set -e

WORKER_DIR="$HOME/.bittrader_worker"
source "$WORKER_DIR/config.env"

LOG_FILE="$WORKER_DIR/logs/ssh_tunnel.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "SSH Tunnel Daemon iniciando..."

while true; do
    if ping -c 1 -W 2 "$HEAD_IP" &> /dev/null; then
        log "🔐 Estableciendo SSH tunnel a $HEAD_IP..."

        ssh -i ~/.ssh/id_bittrader_head -N \
            -L 6379:localhost:6379 \
            -o ServerAliveInterval=60 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -o StrictHostKeyChecking=no \
            "enderj@$HEAD_IP" &>> "$LOG_FILE"

        log "⚠️  Tunnel desconectado"
    else
        log "❌ Head no accesible"
    fi

    sleep 10
done
SSHTUNNELEOF

chmod +x "$WORKER_DIR/ssh_tunnel_daemon.sh"

# 10. Crear daemon Worker
echo "🐍 Creando daemon Worker..."
cat > "$WORKER_DIR/worker_daemon.sh" <<'WORKEREOF'
#!/bin/bash
set -e

WORKER_DIR="$HOME/.bittrader_worker"
VENV_PATH="$WORKER_DIR/venv"
LOG_FILE="$WORKER_DIR/logs/worker.log"

source "$WORKER_DIR/config.env"
source "$VENV_PATH/bin/activate"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Worker Daemon iniciando..."

while true; do
    # Esperar SSH tunnel
    log "🔍 Esperando SSH tunnel..."
    while ! nc -z localhost 6379 2>/dev/null; do
        sleep 5
    done
    log "✅ Tunnel activo"

    # Leer CPUs
    if [ -f "$WORKER_DIR/current_cpus" ]; then
        NUM_CPUS=$(cat "$WORKER_DIR/current_cpus")
    else
        NUM_CPUS=$(sysctl -n hw.ncpu)
    fi

    log "🚀 Conectando Worker con $NUM_CPUS CPUs..."

    ray start --address=127.0.0.1:6379 --num-cpus="$NUM_CPUS" &>> "$LOG_FILE"

    if [ $? -eq 0 ]; then
        log "✅ Worker conectado"

        while ray status --address=127.0.0.1:6379 &>/dev/null; do
            sleep 30
        done

        log "⚠️  Conexión perdida"
        ray stop &>/dev/null || true
    fi

    sleep 15
done
WORKEREOF

chmod +x "$WORKER_DIR/worker_daemon.sh"

# 11. Crear LaunchAgents
echo ""
echo "🚀 Instalando daemons..."

cat > ~/Library/LaunchAgents/com.bittrader.ssh_tunnel.plist <<EOF
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

cat > ~/Library/LaunchAgents/com.bittrader.worker.plist <<EOF
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
launchctl unload ~/Library/LaunchAgents/com.bittrader.ssh_tunnel.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.bittrader.worker.plist 2>/dev/null || true

launchctl load ~/Library/LaunchAgents/com.bittrader.ssh_tunnel.plist
launchctl load ~/Library/LaunchAgents/com.bittrader.worker.plist

echo ""
echo "=========================================="
echo "✅ WORKER INSTALADO Y ACTIVADO"
echo "=========================================="
echo ""
echo "📋 Ver logs:"
echo "   tail -f ~/.bittrader_worker/logs/ssh_tunnel.log"
echo "   tail -f ~/.bittrader_worker/logs/worker.log"
echo ""
echo "El Worker se conectará automáticamente al Head"
echo ""
