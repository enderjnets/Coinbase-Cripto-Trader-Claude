#!/bin/bash

# Auto-Setup Script for VPS (Ubuntu/Debian)

echo "🚀 Starting Bot Setup..."

# 1. Update & Install Python3-pip if checking missing
# sudo apt-get update && sudo apt-get install -y python3-pip

# 2. Install Dependencies
echo "📦 Installing Requirements..."
pip3 install -r requirements.txt

# 3. Optimize Linux Limits (Optional for high frequency)
ulimit -n 65535

# 4. Run Streamlit in Headless Mode on Port 80 (or 8501)
echo "🔥 Launching Bot..."
# Using nohup to keep running after disconnect
nohup python3 -m streamlit run interface.py --server.port 8501 --server.headless true --browser.gatherUsageStats false > bot_log.txt 2>&1 &

echo "✅ Bot started in background!"
echo "👉 Access at: http://<YOUR_VPS_IP>:8501"
echo "📄 Logs: tail -f bot_log.txt"
