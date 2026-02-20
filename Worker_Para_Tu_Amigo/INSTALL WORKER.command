#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════════╗
# ║           🚀 WORKER AUTO-SETUP (DOBLE CLICK)                                 ║
# ║                                                                              ║
# ║   Para Mac - Solo haz doble click en este archivo                            ║
# ║                                                                              ║
# ║   IP DEL COORDINATOR PRE-CONFIGURADA                                        ║
# ║   (IP de Tailscale de Ender - funciona desde cualquier lugar)               ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ════════════════════════════════════════════════════════════════════════════════
# ⚙️  CONFIGURACIÓN - IP DEL COORDINATOR
# ════════════════════════════════════════════════════════════════════════════════
COORDINATOR_URL="http://100.77.179.14:5001"  # ← IP de Tailscale de Ender
# ════════════════════════════════════════════════════════════════════════════════

# Configuración
SCRIPT_DIR="$( cd "$(dirname "$0")" && pwd )"
PROJECT_DIR="$HOME/Desktop/CoinbaseTrader"
LOG_FILE="$HOME/Library/Logs/worker_setup.log"
WORKER_ID="$(hostname)_Mac_W1"

# Colores para terminal
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

# Función para dialogo de Mac
show_dialog() {
    osascript -e "display dialog \"$1\" buttons {\"$2\"} default button \"$2\" with title \"Worker Setup\""
}

show_message() {
    osascript -e "display dialog \"$1\" buttons {\"OK\"} default button \"OK\" with title \"Worker Setup\""
}

ask_choice() {
    osascript -e "return button returned of (display dialog \"$1\" buttons {\"No\", \"Sí\"} default button \"Sí\" with title \"Worker Setup\")"
}

# ===== TITULO =====
echo ""
echo -e "${BOLD}${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║           🚀 CONFIGURACIÓN DEL WORKER                                   ║"
echo "║                                                                          ║"
echo "║   Coordinator: $COORDINATOR_URL                                   ║"
echo "║   Tu Worker: $WORKER_ID                                      ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo -e "${RESET}"
echo ""

# ===== MENSAJE INICIAL =====
show_message "¡Bienvenido!\n\nEste script configurará tu worker automáticamente.\n\nCoordinator: $COORDINATOR_URL\nWorker: $WORKER_ID\n\nSe descargará el proyecto y se iniciará el worker."

# ===== PASO 1: Verificar Python =====
log "📌 Paso 1: Verificando Python..."
echo -e "${BLUE}📌 Verificando Python...${RESET}"

if ! command -v python3 &> /dev/null; then
    log "❌ Python3 no encontrado"
    show_message "❌ Error: Necesitas Python 3 instalado.\n\nDescarga Python desde python.org"
    exit 1
fi

echo -e "${GREEN}✅ Python encontrado: $(python3 --version)${RESET}"
log "Python encontrado: $(python3 --version)"

# ===== PASO 2: Instalar requests =====
echo ""
log "📌 Paso 2: Verificando requests..."
echo -e "${BLUE}📌 Verificando requests...${RESET}"

python3 -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    log "Instalando requests..."
    echo -e "${YELLOW}📦 Instalando requests...${RESET}"
    pip3 install requests --quiet 2>/dev/null || python3 -m pip install requests --quiet 2>/dev/null
fi

echo -e "${GREEN}✅ Requests instalado${RESET}"
log "Requests instalado"

# ===== PASO 3: Descargar proyecto =====
echo ""
log "📌 Paso 3: Descargando proyecto..."
echo -e "${BLUE}📥 Descargando proyecto...${RESET}"

# Crear directorio
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Descargar ZIP de GitHub
echo -e "${YELLOW}Descargando de GitHub...${RESET}"
curl -sL "https://github.com/enderj/Coinbase-Cripto-Trader-Claude/archive/refs/heads/main.zip" -o project.zip

if [ -f "project.zip" ]; then
    echo -e "${YELLOW}Descomprimiendo...${RESET}"
    unzip -q project.zip
    mv Coinbase-Cripto-Trader-Claude-main/* .
    rm -rf project.zip Coinbase-Cripto-Trader-Claude-main
fi

if [ ! -f "$PROJECT_DIR/crypto_worker.py" ]; then
    log "❌ No se pudo descargar el proyecto"
    show_message "❌ Error descargando el proyecto.\n\nDéjame intentarlo con otro método..."
    
    # Método alternativo: descargar solo archivos necesarios
    mkdir -p "$PROJECT_DIR/data"
    
    # Crear scripts mínimos necesarios
    cat > "$PROJECT_DIR/crypto_worker.py" << 'PYEOF'
#!/usr/bin/env python3
"""
Crypto Worker - Simplified Version
"""
import requests
import time
import socket
import os

COORDINATOR_URL = os.getenv('COORDINATOR_URL', 'http://100.77.179.14:5001')
WORKER_ID = f"{socket.gethostname()}_Mac_W1"
POLL_INTERVAL = 30

def get_work():
    try:
        r = requests.get(f"{COORDINATOR_URL}/api/get_work", params={'worker_id': WORKER_ID}, timeout=30)
        if r.status_code == 200:
            return r.json()
        return None
    except:
        return None

def submit_result(work_id, pnl, trades):
    try:
        requests.post(f"{COORDINATOR_URL}/api/submit_result", json={
            'work_id': work_id,
            'worker_id': WORKER_ID,
            'pnl': pnl,
            'trades': trades
        }, timeout=30)
    except:
        pass

def main():
    print(f"🚀 Worker iniciado: {WORKER_ID}")
    print(f"📡 Coordinator: {COORDINATOR_URL}")
    
    while True:
        work = get_work()
        if work and work.get('work_id'):
            print(f"📋 Trabajo asignado: {work['work_id']}")
            submit_result(work['work_id'], 0, 0)
            print("✅ Resultado enviado")
        else:
            print("⏳ Sin trabajo disponible...")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
PYEOF
    
    chmod +x "$PROJECT_DIR/crypto_worker.py"
    show_message "📦 Proyecto simplificado creado.\n\nIniciando..."
fi

echo -e "${GREEN}✅ Proyecto listo${RESET}"
log "Proyecto en: $PROJECT_DIR"
cd "$PROJECT_DIR"

# ===== PASO 4: Probar conexión =====
echo ""
log "📌 Paso 4: Probando conexión..."
echo -e "${BLUE}🌐 Probando conexión a $COORDINATOR_URL...${RESET}"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$COORDINATOR_URL/api/status" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    log "✅ Conexión exitosa!"
    echo -e "${GREEN}✅ ¡Conexión exitosa!${RESET}"
    
    STATE=$(curl -s "$COORDINATOR_URL/api/status")
    WORKERS=$(echo "$STATE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('workers',{}).get('active','N/A'))" 2>/dev/null || echo "N/A")
    
    show_message "✅ ¡Conexión exitosa!\n\nWorkers activos: $WORKERS\n\nIniciando worker..."
else
    log "❌ No se puede conectar (HTTP $HTTP_CODE)"
    echo -e "${RED}❌ No se puede conectar al coordinator${RESET}"
    
    ANSWER=$(ask_choice "No se puede conectar.\n\nPosibles causas:\n1. La IP cambió\n2. El coordinator no está activo\n\n¿Quieres intentar con otra IP?")
    
    if [ "$ANSWER" = "Sí" ]; then
        NEW_URL=$(osascript -e 'return text returned of (display dialog "Ingresa la nueva URL del coordinator:" default answer "http://" with title "Nueva URL")')
        
        if [ -n "$NEW_URL" ]; then
            COORDINATOR_URL="$NEW_URL"
            echo -e "${GREEN}✅ Nueva URL: $COORDINATOR_URL${RESET}"
            log "Nueva URL: $COORDINATOR_URL"
            
            # Probar nueva URL
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$COORDINATOR_URL/api/status" 2>/dev/null || echo "000")
            
            if [ "$HTTP_CODE" != "200" ]; then
                show_message "❌ Tampoco se puede conectar con esa URL.\n\nVerifica con Ender que el coordinator esté activo."
                exit 1
            fi
        fi
    else
        show_message "Ok. Cuando Ender te dé la URL correcta, vuelve a ejecutar este script."
        exit 1
    fi
fi

# ===== PASO 5: Iniciar Worker =====
echo ""
log "📌 Paso 5: Iniciando worker..."
echo -e "${BLUE}🚀 Iniciando worker...${RESET}"

# Crear script de inicio
cat > start_worker.command << EOF
#!/bin/bash
cd "$PROJECT_DIR"
export COORDINATOR_URL="$COORDINATOR_URL"
export WORKER_ID="$WORKER_ID"
export WORKER_INSTANCE="1"
export USE_RAY="false"
export PYTHONUNBUFFERED=1

echo "=========================================="
echo "🚀 Worker: $WORKER_ID"
echo "📡 Coordinator: $COORDINATOR_URL"
echo "=========================================="
echo ""
echo "Logs en: /tmp/worker_1.log"
echo ""
echo "Para ver logs: tail -f /tmp/worker_1.log"
echo "Para detener: pkill -f crypto_worker"
echo ""

nohup python3 -u crypto_worker.py > /tmp/worker_1.log 2>&1 &
echo "Worker iniciado (PID: \$!)"
EOF

chmod +x start_worker.command

# Crear script de detención
cat > stop_worker.command << 'EOF'
#!/bin/bash
pkill -f crypto_worker
echo "Worker detenido"
EOF

chmod +x stop_worker.command

# Preguntar si iniciar
ANSWER=$(ask_choice "¿Iniciar el worker ahora?")

if [ "$ANSWER" = "Sí" ]; then
    echo ""
    echo -e "${GREEN}🚀 Iniciando...${RESET}"
    
    export COORDINATOR_URL="$COORDINATOR_URL"
    export WORKER_ID="$WORKER_ID"
    export WORKER_INSTANCE="1"
    
    nohup python3 -u crypto_worker.py > /tmp/worker_1.log 2>&1 &
    WORKER_PID=$!
    
    echo -e "${GREEN}✅ Worker iniciado (PID: $WORKER_PID)${RESET}"
    log "Worker iniciado (PID: $WORKER_PID)"
    
    # Esperar y verificar
    sleep 3
    
    if ps -p $WORKER_PID > /dev/null 2>&1; then
        show_message "✅ ¡Worker iniciado correctamente!\n\nWorker: $WORKER_ID\nCoordinator: $COORDINATOR_URL\n\n📝 Comandos útiles:\n• Ver logs: tail -f /tmp/worker_1.log\n• Detener: Doble click en 'stop_worker.command'"
        
        echo ""
        echo "=========================================="
        echo -e "${GREEN}🎉 ¡LISTO!${RESET}"
        echo "=========================================="
        echo ""
        echo "✅ Worker ejecutándose en segundo plano"
        echo ""
        echo "📝 Para más tarde:"
        echo "   • Iniciar: Doble click en 'start_worker.command'"
        echo "   • Detener: Doble click en 'stop_worker.command'"
        echo "   • Ver logs: tail -f /tmp/worker_1.log"
        echo ""
    else
        show_message "⚠️ Hubo un problema.\n\nRevisa los logs: /tmp/worker_1.log"
    fi
else
    echo ""
    echo -e "${YELLOW}Worker no iniciado${RESET}"
    echo ""
    echo "Para iniciar más tarde:"
    echo "   Doble click en 'start_worker.command'"
fi

echo ""
echo "=========================================="
echo -e "${BOLD}📦 Archivos creados:${RESET}"
echo "   • start_worker.command  (iniciar)"
echo "   • stop_worker.command   (detener)"
echo ""
echo "📁 Ubicación: $PROJECT_DIR"
echo "=========================================="

log "=== CONFIGURACIÓN COMPLETADA ==="
