#!/bin/bash
# Script de inicio para Ray Head en Docker

set -e

echo "=========================================="
echo "Bittrader Ray Head Node - Docker"
echo "Iniciando..."
echo "=========================================="

# Iniciar Tailscale daemon en segundo plano
echo "🔐 Iniciando Tailscale..."
tailscaled --tun=userspace-networking --socks5-server=localhost:1055 &
sleep 3

# Autenticar con Tailscale (usa authkey si existe)
if [ -n "$TAILSCALE_AUTHKEY" ]; then
    echo "🔑 Autenticando con Tailscale..."
    tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname=bittrader-head-docker
else
    echo "⚠️  No TAILSCALE_AUTHKEY proporcionada"
    echo "   Usa: docker run -e TAILSCALE_AUTHKEY=<key> ..."
fi

# Obtener IP de Tailscale
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "pendiente")
echo "📡 Tailscale IP: $TAILSCALE_IP"

# Iniciar Ray Head
echo ""
echo "🚀 Iniciando Ray Head Node..."
RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 ray start \
    --head \
    --port=6379 \
    --node-ip-address=0.0.0.0 \
    --include-dashboard=false \
    --num-cpus=12 \
    --block

# El --block mantiene el contenedor corriendo
echo "✅ Ray Head iniciado"
