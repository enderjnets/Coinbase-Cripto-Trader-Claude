#!/usr/bin/env python3
"""
Script para capturar imagen del portapapeles en macOS
Uso: 
1. Copia una imagen (Cmd+C)
2. Ejecuta: python clipboard_image.py
3. La imagen se guarda en: clipboard_images/
"""

import subprocess
import os
from datetime import datetime

def get_clipboard_image():
    """Captura imagen del portapapeles usando osascript"""
    
    script = '''
    tell application "System Events"
        try
            set the clipboard to the clipboard as «class PNGf»
            return "OK"
        on error
            return "NO_IMAGE"
        end try
    end tell
    '''
    
    result = subprocess.run(['osascript', '-e', script], 
                          capture_output=True, text=True)
    
    if "NO_IMAGE" in result.stdout:
        return None
    
    # Obtener la imagen como data
    script2 = '''
    tell application "System Events"
        try
            set imgData to the clipboard as «class PNGf»
            return do shell script "base64 <<EOF
" & (contents of imgData) & "
EOF
"
        on error errMsg
            return "ERROR: " & errMsg
        end try
    end tell
    '''
    
    result = subprocess.run(['osascript', '-e', script2], 
                          capture_output=True, text=True, shell=True)
    
    return result.stdout

def save_image(base64_data):
    """Guarda la imagen desde base64"""
    
    # Crear directorio de salida
    output_dir = os.path.dirname(os.path.abspath(__file__))
    images_dir = os.path.join(output_dir, "clipboard_images")
    os.makedirs(images_dir, exist_ok=True)
    
    # Generar nombre de archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"clipboard_{timestamp}.png"
    filepath = os.path.join(images_dir, filename)
    
    # Decodificar y guardar
    try:
        import base64
        image_data = base64.b64decode(base64_data)
        with open(filepath, 'wb') as f:
            f.write(image_data)
        return filepath
    except Exception as e:
        print(f"Error al decodificar: {e}")
        return None

def main():
    print("📋 Verificando portapapeles...")
    
    # Intentar obtener imagen
    script = '''
    tell application "System Events"
        try
            set imgData to the clipboard as «class PNGf»
            return do shell script "base64 <(echo " & quoted form of (do shell script "base64 <<'EOF'
" & (contents of imgData) & "
EOF
") & ")"
        on error
            return "NO_IMAGE"
        end try
    end tell
    '''
    
    result = subprocess.run(['osascript', '-e', script], 
                          capture_output=True, text=True, shell=True)
    
    if "NO_IMAGE" in result.stdout or result.returncode != 0:
        print("❌ No hay imagen en el portapapeles")
        print("   1. Copia una imagen (Cmd+C)")
        print("   2. Ejecuta este script de nuevo")
        return
    
    # Guardar imagen
    filepath = save_image(result.stdout)
    
    if filepath:
        print(f"✅ Imagen guardada: {filepath}")
        print(f"\n📁 Ubicación: {filepath}")
    else:
        print("❌ Error al guardar la imagen")

if __name__ == "__main__":
    main()
