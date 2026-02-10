#!/bin/bash
# Script de inicio rápido para Worker
# Uso: ./start_worker.sh [COORDINATOR_URL]
#
# Ejemplo:
#   ./start_worker.sh http://100.118.215.73:5000

echo ""
echo "================================================================================"
echo "🤖 INICIANDO WORKER - Sistema Distribuido"
echo "================================================================================"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "crypto_worker.py" ]; then
    echo "❌ ERROR: crypto_worker.py no encontrado"
    echo "   Ejecuta este script desde el directorio del proyecto"
    exit 1
fi

# Verificar dependencias
echo "🔍 Verificando dependencias..."
python3 -c "import pandas, numpy, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Dependencias faltantes - Instalando..."
    pip3 install pandas numpy requests
fi
echo "   ✅ Dependencias OK"
echo ""

# Verificar datos
if [ ! -f "data/BTC-USD_FIVE_MINUTE.csv" ]; then
    echo "❌ ERROR: Archivo de datos no encontrado"
    echo "   Esperado: data/BTC-USD_FIVE_MINUTE.csv"
    exit 1
fi
echo "✅ Datos encontrados"
echo ""

# URL del coordinator
if [ -z "$1" ]; then
    echo "⚠️  No se especificó URL del coordinator"
    echo ""
    echo "Uso: ./start_worker.sh [COORDINATOR_URL]"
    echo ""
    echo "Ejemplos:"
    echo "  ./start_worker.sh http://100.118.215.73:5000"
    echo "  ./start_worker.sh http://localhost:5000"
    echo ""
    read -p "Ingresa URL del coordinator: " COORDINATOR_URL
else
    COORDINATOR_URL=$1
fi

echo ""
echo "📡 Coordinator: $COORDINATOR_URL"
echo ""

# Probar conexión
echo "🔍 Probando conexión con coordinator..."
curl -s -m 5 "$COORDINATOR_URL/api/status" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Conexión OK"
else
    echo "   ⚠️  No se pudo conectar (el coordinator puede no estar ejecutando)"
    echo "   El worker reintentará automáticamente"
fi

echo ""
echo "================================================================================"
echo ""

# Iniciar worker
python3 crypto_worker.py "$COORDINATOR_URL"
