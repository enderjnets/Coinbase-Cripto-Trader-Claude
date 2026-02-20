#!/bin/bash
# Setup automático Ray Head en Docker - MacBook Pro
# Este script se ejecuta UNA VEZ después de instalar Docker

set -e

PROJECT_DIR="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

echo "=========================================="
echo "Bittrader Ray Head Docker - Setup"
echo "=========================================="
echo ""

# Verificar que Docker esté corriendo
echo "🔍 Verificando Docker..."
if ! docker ps &>/dev/null; then
    echo "❌ Docker no está corriendo"
    echo "   Por favor inicia Docker Desktop y vuelve a ejecutar este script"
    exit 1
fi
echo "✅ Docker corriendo"

# Ir al directorio del proyecto
cd "$PROJECT_DIR"

# Construir imagen Docker
echo ""
echo "🏗️  Construyendo imagen Ray Head..."
docker build -t bittrader-ray-head:latest -f Dockerfile.rayhead .

echo "✅ Imagen construida"

# Obtener Tailscale authkey
echo ""
echo "🔑 Para que el contenedor se conecte a Tailscale, necesitas un authkey"
echo ""
echo "   1. Ve a: https://login.tailscale.com/admin/settings/keys"
echo "   2. Click en 'Generate auth key'"
echo "   3. Marca 'Reusable' y 'Ephemeral'"
echo "   4. Copia el key"
echo ""
read -p "Pega tu Tailscale authkey aquí: " TAILSCALE_AUTHKEY

if [ -z "$TAILSCALE_AUTHKEY" ]; then
    echo ""
    echo "⚠️  Sin authkey, el contenedor no se conectará a Tailscale"
    echo "   Podrás configurarlo después"
    echo ""
fi

# Detener contenedor anterior si existe
echo ""
echo "🛑 Deteniendo contenedor anterior (si existe)..."
docker stop bittrader-ray-head 2>/dev/null || true
docker rm bittrader-ray-head 2>/dev/null || true

# Iniciar contenedor
echo ""
echo "🚀 Iniciando Ray Head en Docker..."
docker run -d \
    --name bittrader-ray-head \
    --restart unless-stopped \
    -e TAILSCALE_AUTHKEY="$TAILSCALE_AUTHKEY" \
    -p 6379:6379 \
    -p 8265:8265 \
    --cap-add=NET_ADMIN \
    --device=/dev/net/tun \
    bittrader-ray-head:latest

echo "✅ Contenedor iniciado"

# Esperar a que Ray esté listo
echo ""
echo "⏳ Esperando a que Ray Head esté listo..."
sleep 15

# Verificar estado
echo ""
echo "📊 Estado del contenedor:"
docker ps --filter name=bittrader-ray-head

echo ""
echo "=========================================="
echo "✅ Ray Head Docker configurado"
echo "=========================================="
echo ""
echo "📋 Información:"

# Obtener IP del contenedor
CONTAINER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' bittrader-ray-head)
echo "   - IP del contenedor: $CONTAINER_IP"

# Intentar obtener Tailscale IP
TAILSCALE_IP=$(docker exec bittrader-ray-head tailscale ip -4 2>/dev/null || echo "Configurando...")
echo "   - Tailscale IP: $TAILSCALE_IP"

echo ""
echo "📝 Comandos útiles:"
echo "   - Ver logs: docker logs -f bittrader-ray-head"
echo "   - Verificar Ray: docker exec bittrader-ray-head ray status"
echo "   - Detener: docker stop bittrader-ray-head"
echo "   - Reiniciar: docker restart bittrader-ray-head"
echo ""
echo "🎯 Siguiente paso:"
echo "   Configura el Worker en MacBook Air para conectarse a: $TAILSCALE_IP:6379"
echo ""
