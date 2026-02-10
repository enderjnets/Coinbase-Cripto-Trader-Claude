#!/bin/bash
echo "💀 SUPER KILL: Force stopping all Python and Ray processes..."

# Kill Ray aggressively
pkill -9 -f ray
pkill -9 -f gcs_server
pkill -9 -f raylet
pkill -9 -f plasma_store_server
pkill -9 -f monitor
pkill -9 -f dashboard

# Kill Streamlit and Python
pkill -9 -f streamlit
pkill -9 -f python
pkill -9 -f Python  # Case sensitive on some systems

echo "🧹 Cleaning up temp files..."
rm -rf /tmp/ray/*
rm -rf *.log
rm -rf OPTIMIZER_CRASH.txt

echo "✅ System is 100% CLEAN. Now you can run ./restart_system.sh"
