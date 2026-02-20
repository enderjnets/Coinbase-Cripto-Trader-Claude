#!/bin/bash
# Script para iniciar Streamlit con cluster Ray configurado

# Directorio del proyecto
PROJECT_DIR="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
cd "$PROJECT_DIR"

# Verificar que Ray Head está corriendo
if ! nc -z 100.77.179.14 6379 2>/dev/null; then
    echo "❌ Error: Ray Head no está disponible en 100.77.179.14:6379"
    echo "   Por favor, verifica que el Head Node esté corriendo en el MacBook Pro."
    exit 1
fi

echo "✅ Ray Head detectado en 100.77.179.14:6379"

# Verificar Worker local
if ps aux | grep -q "[w]orker_daemon.sh"; then
    echo "✅ Worker daemon corriendo localmente"
else
    echo "⚠️  Worker daemon NO está corriendo"
    echo "   Iniciando Worker..."
    rm -f ~/.bittrader_worker/worker_daemon.lock
    cd ~/.bittrader_worker && nohup ./worker_daemon.sh > /dev/null 2>&1 &
    sleep 3
    cd "$PROJECT_DIR"
fi

# Configurar variables de entorno para el cluster
export RAY_ADDRESS="100.77.179.14:6379"
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1

# Detener Streamlit anterior si existe
pkill -9 -f "streamlit run interface.py" 2>/dev/null

# Esperar a que el puerto se libere
sleep 2

echo ""
echo "🚀 Iniciando Streamlit con Cluster Ray..."
echo "   • RAY_ADDRESS: $RAY_ADDRESS"
echo "   • Puerto: 8501"
echo ""

# Iniciar Streamlit con las variables configuradas
python3 -m streamlit run interface.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    > /tmp/streamlit_cluster.log 2>&1 &

STREAMLIT_PID=$!
echo "✅ Streamlit iniciado (PID: $STREAMLIT_PID)"

# Esperar a que Streamlit arranque
sleep 5

# Verificar que está corriendo
if ps -p $STREAMLIT_PID > /dev/null 2>&1; then
    echo ""
    echo "🌐 URLs de Acceso:"
    echo "   • Local: http://localhost:8501"
    echo "   • Tailscale: http://100.118.215.73:8501"
    echo ""
    echo "📊 Para verificar el cluster:"
    echo "   python3 -c 'import ray; ray.init(address=\"auto\"); print(f\"CPUs: {int(ray.cluster_resources().get(\"CPU\", 0))}\"); ray.shutdown()'"
    echo ""
    echo "📝 Logs: tail -f /tmp/streamlit_cluster.log"

    # Abrir navegador
    open "http://localhost:8501"
else
    echo "❌ Error: Streamlit no pudo iniciar"
    echo "Ver logs: cat /tmp/streamlit_cluster.log"
    exit 1
fi
