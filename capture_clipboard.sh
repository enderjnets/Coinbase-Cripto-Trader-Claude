#!/bin/bash

# 🎯 Script para capturar imagen del portapapeles
# Uso: 
#   1. Copia una imagen (Cmd+C)
#   2. Ejecuta: ./capture_clipboard.sh
#   3. La imagen se guarda en el escritorio

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="$HOME/Desktop"
OUTPUT_FILE="${OUTPUT_DIR}/clipboard_${TIMESTAMP}.png"

echo "📋 Verificando portapapeles..."

# Método AppleScript
osascript << 'EOF' 2>/dev/null
tell application "System Events"
    try
        set imgData to the clipboard as «class PNGf»
        set fp to open for access file ("${OUTPUT_FILE}" as POSIX file) with write permission
        write imgData to fp
        close access fp
        return "OK"
    on error
        return "NO_IMAGE"
    end try
end tell
EOF

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "✅ Imagen guardada: $OUTPUT_FILE"
    echo ""
    echo "📁 El archivo está en: $OUTPUT_FILE"
    # Abrir en Finder
    open -R "$OUTPUT_FILE"
else
    echo "❌ No hay imagen en el portapapeles"
    echo ""
    echo "Pasos:"
    echo "  1. Copia una imagen (Cmd+C)"
    echo "  2. Ejecuta este script de nuevo"
    echo ""
    echo "¿Quieres capturar la pantalla en su lugar?"
    echo "  Presiona ENTER para capturar selección, o Ctrl+C para cancelar"
    read -r
    screencapture -is "$OUTPUT_DIR/screenshot_${TIMESTAMP}.png"
    echo "✅ Captura guardada: $OUTPUT_DIR/screenshot_${TIMESTAMP}.png"
fi
