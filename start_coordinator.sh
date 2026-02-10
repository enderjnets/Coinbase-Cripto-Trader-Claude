#!/bin/bash
# Script de inicio rápido para Coordinator
# Uso: ./start_coordinator.sh

echo ""
echo "================================================================================"
echo "🧬 INICIANDO COORDINATOR - Sistema Distribuido"
echo "================================================================================"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "coordinator.py" ]; then
    echo "❌ ERROR: coordinator.py no encontrado"
    echo "   Ejecuta este script desde el directorio del proyecto"
    exit 1
fi

# Verificar Flask instalado
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Flask no instalado - Instalando..."
    pip3 install flask
fi

# Obtener IP local
echo "📡 Configuración de Red:"
echo ""

if command -v tailscale &> /dev/null; then
    TAILSCALE_IP=$(tailscale ip -4)
    echo "   Tailscale IP: $TAILSCALE_IP"
fi

LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
echo "   IP Local: $LOCAL_IP"
echo ""

echo "💡 Workers deben conectarse a:"
echo "   http://$LOCAL_IP:5000"
if [ -n "$TAILSCALE_IP" ]; then
    echo "   o http://$TAILSCALE_IP:5000 (vía Tailscale)"
fi

echo ""
echo "================================================================================"
echo ""

# Iniciar coordinator
python3 coordinator.py
