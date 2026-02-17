#!/bin/bash
echo "🛑 STOPPING ALL PROCESSES..."
pkill -f "streamlit"
pkill -f "ray"
pkill -f "python" # Aggressive but cleaner for dev env

# Give it a moment to die
sleep 2

echo "🚀 STARTING RAY CLUSTER HEAD (Fixed Mode)..."
# We leverage safe_launcher to ensure Ray starts in a path without spaces
/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My\ Drive/Bittrader/Bittrader\ EA/Dev\ Folder/Coinbase\ Cripto\ Trader\ Antigravity/.venv/bin/python safe_launcher.py start_cluster_head.py

echo "⏳ Waiting 5 seconds for Ray to stabilize..."
sleep 5

echo "🚀 LAUNCHING APP..."
# execute run_app.sh which also uses safe launcher
./run_app.sh
