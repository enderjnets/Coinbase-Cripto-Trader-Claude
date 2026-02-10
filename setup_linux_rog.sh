#!/bin/bash
################################################################################
# SCRIPT DE CONFIGURACIÓN AUTOMÁTICA - LINUX ROG
# Ejecutar ESTE SCRIPT en la Linux ROG restaurada
################################################################################

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🔧 CONFIGURACIÓN AUTOMÁTICA - LINUX ROG                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ==============================================================================
# 1. PEDIR IP PARA SSH
# ==============================================================================
echo -e "${YELLOW}📝 PRIMERO: Necesito dar acceso SSH al MacBook Pro${NC}"
echo ""
echo "Este script configurará la Linux ROG para que yo pueda acceder."
echo ""
read -p "📍 IP de la Linux ROG (donde ejecutas este script): " LOCAL_IP

if [ -z "$LOCAL_IP" ]; then
    echo -e "${RED}❌ IP requerida${NC}"
    exit 1
fi

# ==============================================================================
# 2. INSTALAR DEPENDENCIAS
# ==============================================================================
echo ""
echo -e "${BLUE}🔄 Instalando dependencias...${NC}"

# Actualizar
sudo apt update -y 2>/dev/null || apt update -y
sudo apt upgrade -y 2>/dev/null || apt upgrade -y

# Instalar Python y git
sudo apt install -y python3 python3-pip git curl openssh-server 2>/dev/null || \
    apt install -y python3 python3-pip git curl openssh-server

echo -e "${GREEN}✅ Dependencias instaladas${NC}"

# ==============================================================================
# 3. HABILITAR SSH (si no está activo)
# ==============================================================================
echo ""
echo -e "${BLUE}🔐 Configurando SSH...${NC}"

# Iniciar servicio SSH si no está corriendo
if ! pgrep -x "sshd" > /dev/null; then
    sudo service ssh start 2>/dev/null || sudo systemctl start ssh 2>/dev/null || true
    echo "SSH iniciado"
fi

# ==============================================================================
# 4. COPIAR CLAVE SSH DEL MACBOOK PRO
# ==============================================================================
echo ""
echo -e "${BLUE}🔑 Copiando clave SSH del MacBook Pro...${NC}"

# Crear directorio .ssh si no existe
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Copiar clave pública (asegúrate de tenerla antes de ejecutar este script)
if [ ! -f ~/.ssh/authorized_keys ]; then
    echo "" > ~/.ssh/authorized_keys
fi

# La clave pública del MacBook Pro debe estar aquí ANTES de ejecutar
# Pídele a Claude que ejecute: ssh-copy-id enderj@$LOCAL_IP

echo -e "${YELLOW}⚠️  IMPORTANTE: Antes de continuar, ejecuta ESTO en el MacBook Pro:${NC}"
echo ""
echo "   ssh-copy-id enderj@$LOCAL_IP"
echo ""
echo -e "${YELLOW}Esto copiará tu clave SSH para acceso sin contraseña.${NC}"
echo ""

# ==============================================================================
# 5. CLONAR PROYECTO
# ==============================================================================
echo -e "${BLUE}📁 Clonando proyecto...${NC}"

cd ~

if [ -d "Coinbase-Cripto-Trader-Claude" ]; then
    echo "Proyecto ya existe, actualizando..."
    cd Coinbase-Cripto-Trader-Claude
    git pull origin main
else
    git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git
    cd Coinbase-Cripto-Trader-Claude
fi

PROJECT_DIR=$(pwd)
echo -e "${GREEN}✅ Proyecto en: $PROJECT_DIR${NC}"

# ==============================================================================
# 6. INSTALAR DEPENDENCIAS PYTHON
# ==============================================================================
echo ""
echo -e "${BLUE}🐍 Instalando dependencias Python...${NC}"

pip3 install --quiet requests pandas numpy 2>/dev/null || \
pip3 install requests pandas numpy 2>/dev/null || \
python3 -m pip install requests pandas numpy 2>/dev/null

echo -e "${GREEN}✅ Dependencias Python listas${NC}"

# ==============================================================================
# 7. VERIFICAR SSH
# ==============================================================================
echo ""
echo -e "${BLUE}🔍 Verificando conexión SSH desde MacBook Pro...${NC}"

# Esperar a que el usuario copie la clave
read -p "🤖 ¿Ya ejecutaste 'ssh-copy-id enderj@$LOCAL_IP' en el MacBook Pro? (s/n): " SSH_READY

if [ "$SSH_READY" != "s" ]; then
    echo -e "${YELLOW}⚠️  Ejecuta esto en el MacBook Pro primero:${NC}"
    echo "   ssh-copy-id enderj@$LOCAL_IP"
    echo ""
    echo "Luego ejecuta este comando aquí para verificar:"
    echo "   ssh enderj@$LOCAL_IP 'hostname'"
    exit 0
fi

# ==============================================================================
# 8. VERIFICAR CONEXIÓN
# ==============================================================================
echo ""
echo -e "${BLUE}✅ Verificando conexión desde MacBook Pro...${NC}"

if ssh -o ConnectTimeout=5 -o BatchMode=yes enderj@localhost "hostname" 2>/dev/null; then
    echo -e "${GREEN}✅ SSH sin contraseña funcionando${NC}"
else
    # Probar con IP también
    if ssh -o ConnectTimeout=5 -o BatchMode=yes enderj@127.0.0.1 "hostname" 2>/dev/null; then
        echo -e "${GREEN}✅ SSH sin contraseña funcionando${NC}"
    else
        echo -e "${RED}⚠️  SSH sin contraseña NO configurado${NC}"
        echo "Ejecuta en el MacBook Pro:"
        echo "   ssh-copy-id enderj@$LOCAL_IP"
        echo ""
        echo "Luego verifica con:"
        echo "   ssh enderj@$LOCAL_IP 'hostname'"
        exit 1
    fi
fi

# ==============================================================================
# 9. INICIAR WORKERS
# ==============================================================================
echo ""
echo -e "${BLUE}🚀 Iniciando workers...${NC}"

COORDINATOR_URL="http://100.77.179.14:5001"
NUM_WORKERS=4

# Detener workers anteriores
pkill -f crypto_worker 2>/dev/null || true
sleep 1

# Iniciar workers
for i in $(seq 1 $NUM_WORKERS); do
    WORKER_INSTANCE=$i nohup python3 crypto_worker.py $COORDINATOR_URL > ~/worker_$i.log 2>&1 &
    echo -e "   ${GREEN}Worker $i iniciado${NC}"
    sleep 1
done

echo ""

# ==============================================================================
# 10. VERIFICACIÓN FINAL
# ==============================================================================
echo -e "${BLUE}🔍 Verificando...${NC}"
sleep 3

WORKERS_COUNT=$(ps aux | grep crypto_worker | grep -v grep | wc -l)
echo -e "${GREEN}✅ Workers activos: $WORKERS_COUNT${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ CONFIGURACIÓN COMPLETADA                       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "📊 Para verificar en el MacBook Pro:"
echo "   curl http://100.77.179.14:5001/api/status"
echo ""
echo "📝 Logs:"
echo "   tail -f ~/worker_*.log"
echo ""
