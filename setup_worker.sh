#!/bin/bash

# colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 0. Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}=== Mac Worker Node Setup for CryptoOptimizer ===${NC}"
echo "This script will turn this Mac into a worker node for your main optimization cluster."
echo ""

# 1. Virtual Environment Setup (Version Matching is CRITICAL)
# Head Node is using Python 3.9.6. Worker MUST match.
echo -e "${GREEN}[1/3] Setting up Python 3.9 environment (to match Head Node)...${NC}"

# Find Python 3.9
PYTHON_39=$(which python3.9 || echo "/usr/bin/python3")
VERSION=$($PYTHON_39 --version 2>&1)

if [[ $VERSION != *"3.9"* ]]; then
    echo -e "${RED}Warning: Python 3.9 not found (Found $VERSION).${NC}"
    echo "Ray requires MATCHING Python versions (3.9.x) to connect nodes."
    echo "Attempting to continue with default, but if it fails, please install Python 3.9."
    PROMPT_PYTHON="/usr/bin/python3"
else
    echo -e "Found matching Python: ${BLUE}$VERSION${NC}"
    PROMPT_PYTHON=$PYTHON_39
fi

# FORCE DELETE existing env to ensure we use the correct Python version
if [ -d "worker_env" ]; then
    echo "Refreshing environment..."
    rm -rf worker_env
fi

echo "Creating virtual environment using $PROMPT_PYTHON..."
$PROMPT_PYTHON -m venv worker_env

# Activate the environment
source worker_env/bin/activate

# Verify activation
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${RED}Error: Failed to activate virtual environment.${NC}"
    exit 1
fi

# 2. Install Dependencies
echo -e "${GREEN}[2/3] Installing Dependencies (inside venv)...${NC}"
./worker_env/bin/pip install --upgrade pip setuptools wheel
# Allow latest numpy (Head node is on 2.0.x, so we must match)
./worker_env/bin/pip install "ray[default]" pandas numpy plotly python-dotenv coinbase-advanced-py

# pandas-ta is not strictly required for current strategies (implemented in native pandas)
echo "Skipping pandas-ta installation (not required)."



if [ $? -eq 0 ]; then
    echo "Dependencies installed successfully."
else
    echo -e "${RED}Error installing dependencies.${NC}"
    exit 1
fi

# 3. Auto-Connect to Cluster
echo ""
echo -e "${GREEN}[3/3] Scanning network for Main Mac...${NC}"
echo "Running auto-discovery..."

# Create the listener script on the fly (so you don't need to copy 2 files)
cat << 'EOF' > listen.py
import socket
import sys

def listen_for_head():
    PORT = 50000
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind to all interfaces
    try:
        sock.bind(('', PORT))
    except Exception as e:
        print(f"Error binding to port {PORT}: {e}")
        return

    print("🔍 Scanning...", file=sys.stderr)
    
    while True:
        data, addr = sock.recvfrom(1024)
        message = data.decode()
        if message.startswith("RAY_HEAD:"):
            head_ip = message.split(":")[1]
            print(head_ip)
            return

if __name__ == "__main__":
    listen_for_head()
EOF

# Run the python listener script and capture the output (IP)
HEAD_IP=$(python3 listen.py)

# Cleanup
rm listen.py

if [ -z "$HEAD_IP" ]; then
    echo -e "${RED}Auto-discovery failed or timed out.${NC}"
    read -p "Please enter the IP manually: " HEAD_IP
else
    echo -e "Found Head Node at: ${BLUE}$HEAD_IP${NC}"
fi

# 4. Connect
echo ""
echo -e "${GREEN}Joining the Swarm...${NC}"
# CRITICAL: Allow cross-platform clusters
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
echo "Running: ray start --address=$HEAD_IP:6379"

# Use the virtual environment Python explicitly to avoid "command not found"
VENV_PYTHON="./worker_env/bin/python3"

# Stop previous instances
$VENV_PYTHON -c "import sys; from ray.scripts.scripts import main; sys.argv=['ray', 'stop']; main()" &> /dev/null

# Start worker node
$VENV_PYTHON -c "import sys; from ray.scripts.scripts import main; sys.argv=['ray', 'start', '--address=$HEAD_IP:6379']; main()"


if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}SUCCESS! This Mac is now a worker node connected to $HEAD_IP.${NC}"
    echo "You can close this window, but keep the computer awake."
    echo "To stop working later, run this script again or delete the 'worker_env' folder."
else
    echo ""
    echo -e "${RED}Connection failed.${NC}"
    echo "Please check:"
    echo "1. The Main Mac is currently running the optimization."
    echo "2. Both Macs are on the same WiFi."
    echo "3. The IP address $HEAD_IP is correct."
fi
