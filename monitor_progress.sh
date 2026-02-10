#!/bin/bash
# Monitor de Progreso - Búsquedas Paralelas
# Muestra el estado de ambas búsquedas en tiempo real

GOOGLE_DRIVE_PATH="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
AIR_IP="100.77.179.14"

while true; do
    clear
    echo "================================================================================"
    echo "🔍 MONITOR DE BÚSQUEDAS PARALELAS"
    echo "================================================================================"
    echo ""
    echo "Actualizado: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # Estado MacBook PRO
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💻 MacBook PRO (LOCAL)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [ -f "$GOOGLE_DRIVE_PATH/STATUS_PRO.txt" ]; then
        cat "$GOOGLE_DRIVE_PATH/STATUS_PRO.txt"
    else
        echo "⏳ Esperando inicio..."
    fi

    echo ""

    # Estado MacBook AIR
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💻 MacBook AIR (REMOTO)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if ssh -o ConnectTimeout=3 enderj@$AIR_IP "test -f '$GOOGLE_DRIVE_PATH/STATUS_AIR.txt'" 2>/dev/null; then
        ssh enderj@$AIR_IP "cat '$GOOGLE_DRIVE_PATH/STATUS_AIR.txt'" 2>/dev/null
    else
        echo "⏳ Esperando inicio..."
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Presiona Ctrl+C para salir del monitor"
    echo "Las búsquedas continuarán ejecutándose en segundo plano"
    echo ""

    # Actualizar cada 30 segundos
    sleep 30
done
