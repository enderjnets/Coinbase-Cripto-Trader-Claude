#!/bin/bash

# Script para iniciar Worker en MacBook Pro
# Guarda este archivo en el Pro y hazlo ejecutable: chmod +x start_pro_worker.command

cd /Users/enderjnets

echo "🚀 Iniciando Worker Pro..."
echo "📡 Conectando a coordinator: http://100.118.215.73:5001"

# Limpiar Ray primero
pkill -9 -f "ray::" 2>/dev/null
sleep 2
rm -rf /tmp/ray* 2>/dev/null

# Iniciar worker
python3 crypto_worker.py http://100.118.215.73:5001 2>&1 | tee worker_pro.log

echo "✅ Worker Pro iniciado"
