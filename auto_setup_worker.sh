#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║           🚀 SCRIPT DE INICIO RÁPIDO DEL WORKER                         ║
# ║                                                                          ║
# ║   Para amigos del owner que están FUERA de la red local                ║
# ║                                                                          ║
# ║   USO:                                                                  ║
# ║     1. Pregunta al owner la URL del coordinator                        ║
# ║     2. Copia esta línea y reemplaza <URL> con la URL:                 ║
# ║                                                                          ║
# ║     bash auto_setup_worker.sh <URL_COORDINATOR>                         ║
# ║                                                                          ║
# ║   Ejemplo:                                                              ║
# ║     bash auto_setup_worker.sh http://100.77.179.14:5001                 ║
# ║                                                                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║           🚀 INICIO RÁPIDO DEL WORKER                                   ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

# Verificar argumentos
if [ -z "$1" ]; then
    echo -e "${YELLOW}⚠️  Necesito la URL del coordinator${RESET}"
    echo ""
    echo "Pregunta al owner y usa:"
    echo "  ${BOLD}bash $0 http://100.xx.xx.xx:5001${RESET}"
    echo ""
    echo "Si estás en la misma red:"
    echo "  ${BOLD}bash $0 http://192.168.x.x:5001${RESET}"
    exit 1
fi

COORDINATOR_URL="$1"
WORKER_ID="$(hostname)_$(uname -s)_W1"
PROJECT_DIR="$(pwd)"

echo ""
echo -e "${BLUE}📌 Worker ID: ${BOLD}$WORKER_ID${RESET}"
echo -e "${BLUE}📌 Coordinator: ${BOLD}$COORDINATOR_URL${RESET}"
echo -e "${BLUE}📌 Proyecto: ${BOLD}$PROJECT_DIR${RESET}"
echo ""

# Paso 1: Verificar Python
echo -e "${CYAN}📌 Paso 1: Verificando Python...${RESET}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ Python no encontrado${RESET}"
    exit 1
fi
echo -e "${GREEN}✅ Python encontrado: $PYTHON_CMD${RESET}"

# Paso 2: Verificar requests
echo ""
echo -e "${CYAN}📌 Paso 2: Verificando requests...${RESET}"
$PYTHON_CMD -c "import requests" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ requests instalado${RESET}"
else
    echo -e "${YELLOW}⚠️  Instalando requests...${RESET}"
    $PYTHON_CMD -m pip install -q requests
    echo -e "${GREEN}✅ requests instalado${RESET}"
fi

# Paso 3: Probar conexión
echo ""
echo -e "${CYAN}📌 Paso 3: Probando conexión al coordinator...${RESET}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$COORDINATOR_URL/api/status" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ ¡Conexión exitosa!${RESET}"
    
    # Mostrar estado
    echo ""
    echo -e "${CYAN}📊 Estado del coordinator:${RESET}"
    curl -s "$COORDINATOR_URL/api/status" | $PYTHON_CMD -c "
import json, sys
data = json.load(sys.stdin)
print(f\"  Workers activos: {data.get('workers', {}).get('active', 'N/A')}\")
print(f\"  Work Units: {data.get('work_units', {}).get('completed', 'N/A')}/{data.get('work_units', {}).get('total', 'N/A')}\")
"
else
    echo -e "${RED}❌ No se puede conectar (HTTP $HTTP_CODE)${RESET}"
    echo ""
    echo -e "${YELLOW}Posibles causas:${RESET}"
    echo "  1. La URL es incorrecta"
    echo "  2. El coordinator no está ejecutándose"
    echo "  3. Firewall bloqueando"
    echo ""
    echo -e "${YELLOW}¿Quieres continuar de todos modos? (s/n): ${RESET}" 
    read -r response
    if [[ ! "$response" =~ ^([sS][iI]?|[yY]?)$ ]]; then
        exit 1
    fi
fi

# Paso 4: Verificar datos
echo ""
echo -e "${CYAN}📌 Paso 4: Verificando datos...${RESET}"
if [ -d "data" ]; then
    CSV_COUNT=$(ls data/*.csv 2>/dev/null | wc -l)
    if [ "$CSV_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ $CSV_COUNT archivos CSV encontrados${RESET}"
    else
        echo -e "${YELLOW}⚠️  No hay archivos CSV en data/${RESET}"
    fi
else
    echo -e "${YELLOW}⚠️  No existe directorio data/${RESET}"
fi

# Paso 5: Crear script de inicio
echo ""
echo -e "${CYAN}📌 Paso 5: Preparando worker...${RESET}"

# Verificar crypto_worker.py
if [ ! -f "crypto_worker.py" ]; then
    echo -e "${RED}❌ crypto_worker.py no encontrado${RESET}"
    echo "Este script debe ejecutarse desde el directorio del proyecto"
    exit 1
fi

# Crear script de inicio si no existe
STARTUP_SCRIPT="start_my_worker.sh"
cat > "$STARTUP_SCRIPT" << EOFSCRIPT
#!/bin/bash
# Worker startup script - Generated $(date)
# Worker ID: $WORKER_ID
# Coordinator: $COORDINATOR_URL

export COORDINATOR_URL="$COORDINATOR_URL"
export WORKER_INSTANCE="1"
export USE_RAY="false"
export PYTHONUNBUFFERED=1

echo "Iniciando worker..."
echo "Coordinator: \$COORDINATOR_URL"
echo "Worker: $WORKER_ID"

nohup python3 -u crypto_worker.py > /tmp/worker_1.log 2>&1 &
WORKER_PID=\$!

echo "Worker iniciado (PID: \$WORKER_PID)"
echo "Logs: tail -f /tmp/worker_1.log"
EOFSCRIPT

chmod +x "$STARTUP_SCRIPT"
echo -e "${GREEN}✅ Script creado: $STARTUP_SCRIPT${RESET}"

# Preguntar si iniciar
echo ""
echo -e "${CYAN}📌 ¿Iniciar el worker ahora? (s/n): ${RESET}"
read -r response
if [[ "$response" =~ ^([sS][iI]?|[yY]?)$ ]]; then
    echo ""
    echo -e "${GREEN}🚀 Iniciando worker...${RESET}"
    
    bash "$STARTUP_SCRIPT"
    
    echo ""
    echo -e "${GREEN}✅ Worker iniciado!${RESET}"
    echo ""
    echo -e "${CYAN}Verificando que se registró...${RESET}"
    sleep 3
    
    # Verificar registro
    WORKERS_RESPONSE=$(curl -s "$COORDINATOR_URL/api/workers" 2>/dev/null)
    if echo "$WORKERS_RESPONSE" | grep -q "$WORKER_ID"; then
        echo -e "${GREEN}✅ ¡El worker aparece en el coordinator!${RESET}"
    else
        echo -e "${YELLOW}⚠️  Worker iniciado, puede tomar unos segundos aparecer${RESET}"
    fi
    
    echo ""
    echo -e "${CYAN}Comandos útiles:${RESET}"
    echo "  Ver logs:  ${BOLD}tail -f /tmp/worker_1.log${RESET}"
    echo "  Detener:   ${BOLD}pkill -f crypto_worker${RESET}"
    echo "  Verificar: ${BOLD}curl $COORDINATOR_URL/api/workers${RESET}"
else
    echo ""
    echo -e "${YELLOW}Worker no iniciado${RESET}"
    echo ""
    echo -e "${CYAN}Para iniciar después:${RESET}"
    echo "  ${BOLD}cd $PROJECT_DIR && bash $STARTUP_SCRIPT${RESET}"
fi

echo ""
echo -e "${BOLD}──────────────────────────────────────────────────────────────────────${RESET}"
echo -e "${GREEN}🎉 ¡Listo!${RESET}"
echo ""
echo "Tu worker debería aparecer en la interfaz del coordinator"
echo "en la pestaña: 🌐 Sistema Distribuido > 👥 Workers"
echo -e "${BOLD}──────────────────────────────────────────────────────────────────────${RESET}"
