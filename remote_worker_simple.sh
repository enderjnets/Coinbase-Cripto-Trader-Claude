#!/bin/bash
################################################################################
# SCRIPT DE CONFIGURACIÓN REMOTA SIMPLIFICADA DEL WORKER
# Usa el setup_worker.sh existente vía SSH (más robusto)
################################################################################

set -e

# COLORES
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║      🌐 CONFIGURACIÓN REMOTA DEL WORKER (SIMPLIFICADA)         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# CONFIGURACIÓN
HEAD_IP="10.0.0.239"
WORKER_USER="enderj"
WORKER_HOST="Enders-MacBook-Pro.local"

echo -e "${BLUE}📍 Configuración:${NC}"
echo "   Head IP: $HEAD_IP"
echo "   Worker: $WORKER_USER@$WORKER_HOST"
echo ""

# 1. VERIFICAR CONECTIVIDAD SSH
echo -e "${BLUE}🔌 Verificando conectividad SSH...${NC}"

if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$WORKER_USER@$WORKER_HOST" "echo '✅ SSH OK'" 2>/dev/null; then
    echo -e "${GREEN}✅ SSH funciona correctamente${NC}"
else
    echo -e "${RED}❌ No se puede conectar vía SSH${NC}"
    echo ""
    echo "Posibles soluciones:"
    echo "1. Verifica que Remote Login esté habilitado en el Worker:"
    echo "   System Settings → General → Sharing → Remote Login (ON)"
    echo ""
    echo "2. Prueba manualmente:"
    echo "   ssh $WORKER_USER@$WORKER_HOST"
    echo ""
    exit 1
fi

echo ""

# 2. BUSCAR DIRECTORIO DEL PROYECTO EN EL WORKER
echo -e "${BLUE}🔍 Buscando proyecto en el Worker...${NC}"

FIND_PROJECT_CMD='
# Buscar setup_worker.sh en ubicaciones comunes
for search_path in \
    "$HOME/Library/CloudStorage/GoogleDrive-"*"/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude" \
    "$HOME/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude" \
    "$HOME/Documents/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"; do

    if [ -f "$search_path/setup_worker.sh" ]; then
        echo "$search_path"
        exit 0
    fi
done

# Si no se encontró, buscar en todo /Users
FOUND=$(find /Users -name "setup_worker.sh" -path "*/Coinbase Cripto Trader Claude/*" 2>/dev/null | head -1)
if [ -n "$FOUND" ]; then
    dirname "$FOUND"
    exit 0
fi

echo "NOT_FOUND"
'

PROJECT_DIR=$(ssh "$WORKER_USER@$WORKER_HOST" "$FIND_PROJECT_CMD" 2>/dev/null)

if [ "$PROJECT_DIR" = "NOT_FOUND" ] || [ -z "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}⚠️  No se encontró automáticamente${NC}"
    echo ""
    read -p "Ingresa la ruta completa del proyecto en el Worker: " PROJECT_DIR

    # Validar que existe
    if ! ssh "$WORKER_USER@$WORKER_HOST" "[ -d '$PROJECT_DIR' ]" 2>/dev/null; then
        echo -e "${RED}❌ El directorio no existe en el Worker${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Proyecto encontrado: $PROJECT_DIR${NC}"
fi

echo ""

# 3. VERIFICAR QUE setup_worker.sh EXISTE
echo -e "${BLUE}📋 Verificando setup_worker.sh...${NC}"

if ssh "$WORKER_USER@$WORKER_HOST" "[ -f '$PROJECT_DIR/setup_worker.sh' ]" 2>/dev/null; then
    echo -e "${GREEN}✅ setup_worker.sh existe${NC}"
else
    echo -e "${RED}❌ setup_worker.sh no encontrado en $PROJECT_DIR${NC}"
    exit 1
fi

echo ""

# 4. EJECUTAR SETUP_WORKER.SH REMOTAMENTE
echo -e "${BLUE}🚀 Ejecutando configuración del worker...${NC}"
echo -e "${YELLOW}   (El script pedirá la IP del Head - se proporcionará automáticamente)${NC}"
echo ""

# Crear script temporal que inyecta la IP automáticamente
TEMP_SCRIPT=$(mktemp)
cat > "$TEMP_SCRIPT" <<'WRAPPER'
#!/bin/bash
# Wrapper para auto-proporcionar la IP del HEAD

HEAD_IP="HEAD_IP_PLACEHOLDER"

# Ejecutar setup_worker.sh y proporcionar IP cuando la pida
cd "PROJECT_DIR_PLACEHOLDER" || exit 1

# El setup_worker.sh usa un listener UDP que espera un broadcast
# En lugar de eso, vamos a modificar temporalmente el script

# Opción 1: Si listen.py falla, el script pide input manual
# Vamos a interceptar eso
(
    # Esperar a que pida la IP (timeout 30s para el auto-discovery)
    sleep 35

    # Si todavía está corriendo, enviar la IP
    echo "$HEAD_IP"
) | timeout 120 ./setup_worker.sh

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "✅ Worker configurado exitosamente"
else
    echo ""
    echo "⚠️ El script terminó con código: $exit_code"
    echo "   El worker podría estar configurado parcialmente"
fi

exit $exit_code
WRAPPER

# Reemplazar placeholders
sed -i '' "s|HEAD_IP_PLACEHOLDER|$HEAD_IP|g" "$TEMP_SCRIPT"
sed -i '' "s|PROJECT_DIR_PLACEHOLDER|$PROJECT_DIR|g" "$TEMP_SCRIPT"

# Copiar el wrapper al worker
scp -q "$TEMP_SCRIPT" "$WORKER_USER@$WORKER_HOST:/tmp/worker_wrapper.sh"

# Ejecutar remotamente
ssh -t "$WORKER_USER@$WORKER_HOST" "chmod +x /tmp/worker_wrapper.sh && /tmp/worker_wrapper.sh; rm /tmp/worker_wrapper.sh"

# Limpiar temporal local
rm "$TEMP_SCRIPT"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  ✅ CONFIGURACIÓN COMPLETADA                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# 5. VERIFICAR EN EL HEAD
echo -e "${BLUE}📊 Verificando cluster desde el Head...${NC}"
sleep 3

cd "$(dirname "$0")" || exit 1

if [ -f ".venv/bin/ray" ]; then
    .venv/bin/ray status
elif [ -f "worker_env/bin/ray" ]; then
    worker_env/bin/ray status
else
    echo -e "${YELLOW}⚠️  No se pudo verificar status (ray no encontrado)${NC}"
    echo "   Verifica manualmente con: .venv/bin/ray status"
fi

echo ""
echo -e "${GREEN}🎯 Próximos pasos:${NC}"
echo "   1. Verifica arriba que aparezcan 2 nodos activos"
echo "   2. Verifica que haya ~22 CPUs totales"
echo "   3. Ejecuta el Strategy Miner con la configuración correcta"
echo ""
echo -e "${BLUE}📊 Dashboard: http://$HEAD_IP:8265${NC}"
echo ""
