#!/bin/bash
# Monitorear uso de CPU del worker cada 5 segundos

echo "================================================================================
🔍 MONITOR DE CPU - Worker MacBook Pro
================================================================================

Presiona Ctrl+C para detener

"

while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Estado:"
    ps aux | head -1
    ps aux | grep crypto_worker | grep -v grep | grep -v monitor
    echo ""

    # Mostrar threads de Ray si existen
    ray_procs=$(ps aux | grep "ray::" | grep -v grep | wc -l)
    echo "Ray worker processes: $ray_procs"
    echo ""

    sleep 5
done
