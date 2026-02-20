#!/bin/bash

# Script para iniciar Streamlit en MacBook Pro
# Ejecutar con: chmod +x start_streamlit_pro.command
# Luego: doble-click o ./start_streamlit_pro.command

echo "🚀 Iniciando Streamlit en MacBook Pro..."
echo ""

cd "/Users/enderjnets/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

echo "📂 Directorio: $(pwd)"
echo ""

# Verificar que interface.py existe
if [ ! -f "interface.py" ]; then
    echo "❌ Error: interface.py no encontrado"
    echo "Verifica que estás en el directorio correcto"
    exit 1
fi

echo "✅ interface.py encontrado"
echo ""

# Matar cualquier Streamlit previo
echo "🔍 Verificando procesos previos..."
pkill -f "streamlit run interface.py" 2>/dev/null
sleep 2

echo "🌐 Iniciando Streamlit en puerto 8501..."
echo ""

# Iniciar Streamlit
nohup python3 -m streamlit run interface.py --server.headless=true --server.port=8501 > streamlit_pro.log 2>&1 &

STREAMLIT_PID=$!

sleep 3

# Verificar que inició
if ps -p $STREAMLIT_PID > /dev/null; then
    echo "✅ Streamlit iniciado exitosamente!"
    echo "   PID: $STREAMLIT_PID"
    echo ""
    echo "🌐 Accede a la interfaz en:"
    echo "   http://localhost:8501"
    echo ""
    echo "📝 Ver log:"
    echo "   tail -f streamlit_pro.log"
    echo ""
else
    echo "❌ Error al iniciar Streamlit"
    echo "Ver log: cat streamlit_pro.log"
    exit 1
fi

echo "✅ Todo listo!"
