#!/bin/bash

# Update system
# sudo apt-get update && sudo apt-get upgrade -y

# Check if Python3 is installed
if ! command -v python3 &> /dev/null
then
    echo "Python3 could not be found. Please install it (sudo apt install python3 python3-pip)."
    exit
fi

# Create Virtual Environment (Optional but Recommended)
# python3 -m venv venv
# source venv/bin/activate

# Install Requirements
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Run the Bot Interface in Background with nohup (optional) or directly
echo "Starting Coinbase Trading Bot..."
echo "Access the dashboard at http://<YOUR_VPS_IP>:8501"

python3 -m streamlit run interface.py --server.port 8501 --server.address 0.0.0.0
