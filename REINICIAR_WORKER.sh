#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# REINICIAR WORKER - Para cargar código corregido
# ═══════════════════════════════════════════════════════════════
# EJECUTAR ESTO EN EL MacBook Pro (WORKER)
# ═══════════════════════════════════════════════════════════════

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║       🔄 REINICIAR WORKER - CARGAR CÓDIGO CORREGIDO      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 1. Detener Ray en el worker
echo "1️⃣  Deteniendo Ray worker..."
if [ -f "$HOME/.bittrader_worker/venv/bin/ray" ]; then
    "$HOME/.bittrader_worker/venv/bin/ray" stop --force
    echo "   ✅ Worker detenido"
else
    echo "   ⚠️  No se encontró ray en ~/.bittrader_worker/venv"
    echo "   Intentando con ray global..."
    ray stop --force 2>/dev/null || echo "   ℹ️  Ray no estaba corriendo"
fi

echo ""

# 2. Esperar
echo "2️⃣  Esperando 5 segundos..."
sleep 5

# 3. Reiniciar (el daemon lo hará automáticamente)
echo "3️⃣  El daemon reiniciará automáticamente en ~30 segundos..."
echo ""
echo "   O reinicia manualmente ahora con:"
echo ""
echo "   ~/.bittrader_worker/venv/bin/ray start \\"
echo "       --address=100.118.215.73:6379 \\"
echo "       --num-cpus=12"
echo ""

# 4. Verificar
echo "═══════════════════════════════════════════════════════════"
echo "📊 VERIFICACIÓN"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Espera 30 segundos y luego verifica desde el HEAD NODE:"
echo ""
echo "   .venv/bin/ray status"
echo ""
echo "Deberías ver:"
echo "   Active: 2 nodes"
echo "   Resources: 0.0/22.0 CPU"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
