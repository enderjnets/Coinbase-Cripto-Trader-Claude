#!/bin/bash

# 🖱️ Double-Click Wrapper
# This script ensures we are running in the correct directory, 
# even if launched from Finder.

# 1. Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 2. Clear terminal
clear

# 3. Determine which script to run (Head or Worker)
if [ -f "./setup_head.sh" ]; then
    TARGET_SCRIPT="./setup_head.sh"
elif [ -f "./install.sh" ]; then
    TARGET_SCRIPT="./install.sh"
else
    echo "❌ Error: No se encontró el script de instalación (setup_head.sh o install.sh)"
    echo "   Asegúrate de haber descomprimido toda la carpeta."
    read -p "Presiona Enter para salir..."
    exit 1
fi

# 4. Make executable just in case
chmod +x "$TARGET_SCRIPT"

# 5. Run the actual installer
"$TARGET_SCRIPT"

# 6. Keep window open on error
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ La instalación falló o fue cancelada."
    read -p "Presiona Enter para cerrar..."
fi
