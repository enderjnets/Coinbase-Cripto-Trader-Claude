#!/bin/bash
# Script para iniciar Ray Head Node con versión correcta de Python

echo "🚀 Iniciando Ray Head Node con Python del venv..."

# Cambiar al directorio del proyecto
cd "$(dirname "$0")"

# Activar venv
source .venv/bin/activate

# Detener cualquier proceso Ray existente
.venv/bin/ray stop --force 2>/dev/null || true
sleep 2

# Obtener IP de la máquina
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")

echo "📡 IP del Head Node: $IP"
echo "🐍 Python: $(.venv/bin/python --version)"

# Iniciar Ray Head
.venv/bin/ray start \
    --head \
    --port=6379 \
    --dashboard-host=0.0.0.0 \
    --dashboard-port=8265 \
    --num-cpus=$(sysctl -n hw.ncpu) \
    --object-store-memory=2000000000

echo ""
echo "✅ Ray Head Node iniciado"
echo ""
echo "📊 Para ver el dashboard: http://$IP:8265"
echo "🔗 Para conectar workers: RAY_ADDRESS=$IP:6379"
echo ""
echo "Para verificar status: .venv/bin/ray status"
echo ""
