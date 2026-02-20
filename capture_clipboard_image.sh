#!/bin/bash

# Script para capturar imagen del portapapeles en macOS
# Uso: Copia una imagen (Cmd+C) luego ejecuta este script

# Verificar si hay imagen en el portapapeles
osascript -e '
tell application "System Events"
    try
        set the clipboard to the clipboard as «class PNGf»
        return "OK"
    on error
        return "NO_IMAGE"
    end try
end tell
' 2>/dev/null

# Si hay imagen, guardarla
if osascript -e '
tell application "System Events"
    try
        set the clipboard to the clipboard as «class PNGf»
        return "OK"
    on error
        return "NO"
    end try
end tell
' 2>/dev/null | grep -q "OK"; then
    
    # Generar nombre de archivo con timestamp
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    OUTPUT_DIR="/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
    OUTPUT_FILE="${OUTPUT_DIR}/clipboard_image_${TIMESTAMP}.png"
    
    # Usar AppleScript para guardar la imagen
    osascript << 'APPLESCRIPT'
    tell application "System Events"
        try
            set the clipboard to the clipboard as «class PNGf»
            set imgData to the clipboard as «class PNGf»
            
            -- Guardar usando-do shell script con base64
            set base64Data to do shell script "echo " & quoted form of (do shell script "base64 <<EOF
" & (contents of imgData) & "
EOF
") & " | base64 -d > " & POSIX path of (path to desktop as text) & "temp_clipboard.png""
        on error errMsg
            return "ERROR: " & errMsg
        end try
    end tell
APPLESCRIPT
    
    echo "Imagen guardada en el portapapeles"
    
else
    echo "ERROR: No hay imagen en el portapapeles"
    echo "Copia una imagen primero (Cmd+C)"
    exit 1
fi
