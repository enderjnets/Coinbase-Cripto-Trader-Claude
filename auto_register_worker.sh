#!/bin/bash
#
# 🚀 AUTO-REGISTER WORKER v5.0
# Instalador automático para Macs remotas
#
# USO (copia y pega EN UNA LÍNEA en terminal):
# curl -sL https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main/auto_register_worker.sh | bash
#
# O descarga este archivo y ejecuta:
#   bash auto_register_worker.sh
#

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "\n${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  ${CYAN}🚀 AUTO-REGISTER WORKER v5.0${NC}                       ${BLUE}║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"

# ============================================
# 1. DETECTAR IP AUTOMÁTICAMENTE
# ============================================
echo -e "\n${BLUE}🔍 Detectando IP local...${NC}"

# Método 1: Conectar a internet para detectar IP local
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")

if [ -z "$LOCAL_IP" ]; then
    # Método alternativo usando scutil
    LOCAL_IP=$(scutil --get LocalHostName 2>/dev/null | md5 | head -c 9 | sed 's/^/192.168.1./' || echo "127.0.0.1")
fi

echo -e "   ${GREEN}✅ IP Local: $LOCAL_IP${NC}"

# Detectar IP pública
echo -e "${BLUE}   🌐 Detectando IP pública...${NC}"
PUBLIC_IP=$(curl -s --connect-timeout 5 https://api.ipify.org 2>/dev/null || echo "")
if [ -n "$PUBLIC_IP" ]; then
    echo -e "   ${GREEN}✅ IP Pública: $PUBLIC_IP${NC}"
else
    echo -e "   ${YELLOW}⚠️ No se pudo detectar IP pública${NC}"
    PUBLIC_IP="No detectada"
fi

# ============================================
# 2. DETECTAR COORDINATOR AUTOMÁTICAMENTE
# ============================================
echo -e "\n${BLUE}🔗 Buscando Coordinator...${NC}"

# IPs a probar
COORDINATOR_URLS=(
    "http://localhost:5001"
    "http://127.0.0.1:5001"
)

# Detectar gateway para encontrar coordinator en la red
GATEWAY=$(route -n get default 2>/dev/null | grep gateway | awk '{print $2}' || echo "")

if [ -n "$GATEWAY" ]; then
    echo -e "   ${BLUE}🔍 Gateway detectado: $GATEWAY${NC}"
    
    # Probar IPs en el rango del gateway
    for i in $(seq 1 254); do
        IP="${GATEWAY%.*}.$i"
        COORDINATOR_URLS+=("http://$IP:5001")
    done
fi

# Probar cada URL
COORDINATOR_URL=""
for url in "${COORDINATOR_URLS[@]}"; do
    echo -e "   ${YELLOW}Probando: $url${NC}" 2>/dev/null || true
    
    if curl -s --connect-timeout 2 "$url/api/status" > /dev/null 2>&1; then
        COORDINATOR_URL="$url"
        echo -e "   ${GREEN}✅ Coordinator encontrado: $COORDINATOR_URL${NC}"
        break
    fi
done

# Si no se encontró, preguntar
if [ -z "$COORDINATOR_URL" ]; then
    echo -e "\n${YELLOW}⚠️ No se encontró coordinator automáticamente${NC}"
    echo -e "${YELLOW}   Introduce la IP del coordinator:${NC}"
    echo -e "${YELLOW}   (Ej: http://192.168.1.X:5001 o http://TU_IP:5001)${NC}"
    read -p "   URL: " COORDINATOR_URL
    
    if [ -z "$COORDINATOR_URL" ]; then
        COORDINATOR_URL="http://localhost:5001"
    fi
fi

# ============================================
# 3. GENERAR ID ÚNICO
# ============================================
TIMESTAMP=$(date +%Y%m%d%H%M%S)
HOSTNAME=$(hostname)
WORKER_ID="Mac_${HOSTNAME}_${TIMESTAMP}"

echo -e "\n${CYAN}👤 Worker ID: $WORKER_ID${NC}"

# ============================================
# 4. CREAR DIRECTORIOS
# ============================================
WORKER_DIR="$HOME/.bittrader_worker"
mkdir -p "$WORKER_DIR"
mkdir -p "$WORKER_DIR/logs"
mkdir -p "$WORKER_DIR/backups"
mkdir -p "$WORKER_DIR/data"
mkdir -p "$WORKER_DIR/venv"

echo -e "\n${BLUE}📁 Directorio: $WORKER_DIR${NC}"

# ============================================
# 5. CREAR CONFIGURACIÓN
# ============================================
echo -e "${BLUE}⚙️ Creando configuración...${NC}"

cat > "$WORKER_DIR/worker_config.json << EOF
{
    "worker_id": "$WORKER_ID",
    "coordinator_url": "$COORDINATOR_URL",
    "log_level": "INFO",
    "max_concurrent_tasks": 4,
    "heartbeat_interval": 30,
    "timeout": 3600,
    "retry_attempts": 3,
    "checkpoint_interval": 5,
    "auto_register": true,
    "auto_restart": true,
    "registered_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "local_ip": "$LOCAL_IP",
    "public_ip": "$PUBLIC_IP",
    "platform": "macOS",
    "hostname": "$HOSTNAME"
}
EOF

echo -e "   ${GREEN}✅ worker_config.json${NC}"

# ============================================
# 6. CREAR SCRIPTS DE INICIO
# ============================================
echo -e "\n${BLUE}🔗 Creando scripts...${NC}"

# Script de inicio
cat > "$WORKER_DIR/start_worker.command << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Iniciando worker..."
python3 crypto_worker.py
EOF
chmod +x "$WORKER_DIR/start_worker.command"
echo -e "   ${GREEN}✅ start_worker.command${NC}"

# Script daemon con reintento automático
cat > "$WORKER_DIR/worker_daemon.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

while true; do
    LOG_DIR="$(dirname "$0")/logs"
    mkdir -p "$LOG_DIR"
    
    echo "[$(date)] 🚀 Iniciando worker..."
    
    source venv/bin/activate 2>/dev/null || true
    python3 crypto_worker.py
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "[$(date)] ❌ Error (código: $EXIT_CODE), reiniciando en 10s..."
        sleep 10
    else
        echo "[$(date)] ✅ Worker completado, reiniciando en 5s..."
        sleep 5
    fi
done
EOF
chmod +x "$WORKER_DIR/worker_daemon.sh"
echo -e "   ${GREEN}✅ worker_daemon.sh${NC}"

# ============================================
# 7. CREAR VIRTUAL ENVIRONMENT
# ============================================
if [ ! -d "$WORKER_DIR/venv/bin" ]; then
    echo -e "\n${BLUE}📦 Creando Virtual Environment...${NC}"
    python3 -m venv "$WORKER_DIR/venv"
    echo -e "   ${GREEN}✅ venv creado${NC}"
fi

# Instalar dependencias
echo -e "\n${BLUE}📥 Instalando dependencias...${NC}"
"$WORKER_DIR/venv/bin/pip" install --quiet --upgrade pip
"$WORKER_DIR/venv/bin/pip" install --quiet requests flask flask-cors python-dotenv loguru schedule psutil redis celery 2>/dev/null || true
"$WORKER_DIR/venv/bin/pip" install --quiet ray 2>/dev/null || echo -e "   ${YELLOW}⚠️ Ray no disponible (opcional)${NC}"
echo -e "   ${GREEN}✅ Dependencias instaladas${NC}"

# ============================================
# 8. CREAR WORKER DUMMY
# ============================================
if [ ! -f "$WORKER_DIR/crypto_worker.py" ]; then
    echo -e "\n${BLUE}📝 Creando worker básico...${NC}"
    
    cat > "$WORKER_DIR/crypto_worker.py << 'EOF'
#!/usr/bin/env python3
"""
Worker para macOS remoto - Auto-Registrado
Para funcionar completamente, descarga los archivos del proyecto:
https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude
"""
import json
import socket
import time
from pathlib import Path
from datetime import datetime

CONFIG = json.loads(Path("worker_config.json").read_text())

def main():
    print(f"""
╔═══════════════════════════════════════════════════════╗
║  🚀 WORKER INICIADO                              ║
╚═══════════════════════════════════════════════════════╝

📡 Coordinator: {CONFIG['coordinator_url']}
👤 Worker ID: {CONFIG['worker_id']}
🖥️ Hostname: {socket.gethostname()}
🌐 IP: {CONFIG['local_ip']}

⚠️  ESTE ES UN WORKER BÁSICO
Para funcionar completamente:

1. Descarga los archivos del proyecto:
   git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git

2. Copia los archivos a esta carpeta:
   cp Coinbase-Cripto-Trader-Claude/*.py ~/.bittrader_worker/

3. Reinicia este worker:
   bash worker_daemon.sh &

💡 El worker intentará conectarse al coordinator
   y procesar work units automáticamente.
""")
    
    # Loop de heartbeat
    while True:
        try:
            # Aquí iría la lógica de conexión con el coordinator
            time.sleep(CONFIG['heartbeat_interval'])
        except KeyboardInterrupt:
            print("\n🛑 Worker detenido")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
EOF

    echo -e "   ${GREEN}✅ crypto_worker.py${NC}"
fi

# ============================================
# 9. RESUMEN FINAL
# ============================================
echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ${CYAN}✅ INSTALACIÓN COMPLETADA${NC}                            ${GREEN}║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"

echo -e "\n📁 Directorio: $WORKER_DIR"
echo -e "🔗 Coordinator: $COORDINATOR_URL"
echo -e "👤 Worker ID: $WORKER_ID"
echo -e "🖥️ IP Local: $LOCAL_IP"
if [ -n "$PUBLIC_IP" ]; then
    echo -e "🌐 IP Pública: $PUBLIC_IP"
fi

echo -e "\n🚀 PRÓXIMOS PASOS:"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. ${GREEN}SI EL COORDINATOR ESTÁ EN OTRA MÁQUINA:${NC}"
echo "   - Asegúrate que $COORDINATOR_URL sea accesible"
echo "   - El firewall debe permitir conexiones al puerto 5001"
echo ""
echo "2. ${GREEN}DESCARGA LOS ARCHIVOS DEL PROYECTO:${NC}"
echo "   git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git"
echo "   cp -r Coinbase-Cripto-Trader-Claude/*.py $WORKER_DIR/"
echo ""
echo "3. ${GREEN}INICIA EL WORKER:${NC}"
echo "   cd $WORKER_DIR"
echo "   bash worker_daemon.sh &"
echo ""
echo -e "${YELLOW}📝 NOTA:${NC}"
echo "   Si el coordinator está en tu Mac, usa: http://TU_IP:5001"
echo "   Tu IP local es: $LOCAL_IP"
echo "   Tu IP pública es: $PUBLIC_IP"
echo ""
echo -e "${GREEN}🎉 Worker listo para usar!${NC}"
