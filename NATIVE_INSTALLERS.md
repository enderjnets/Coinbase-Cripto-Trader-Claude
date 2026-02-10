# 🧬 INSTALADORES NATIVOS - GUÍA COMPLETA

Este documento explica cómo compilar los instaladores como ejecutables nativos (.app, .exe, .deb)

---

## 📦 ARCHIVOS CREADOS

| Archivo | Descripción | Plataforma |
|---------|-------------|------------|
| `install_worker_mac.py` | Instalador macOS con GUI | macOS |
| `install_worker_windows.py` | Instalador Windows con GUI | Windows |
| `install_worker_linux.py` | Instalador Linux con GUI | Linux |
| `auto_install_worker.sh` | Instalador de terminal | Todas |
| `install_worker.bat` | Instalador Windows batch | Windows |

---

## 🍎 COMPILAR PARA macOS (.app)

### Requisitos:
```bash
# Instalar PyInstaller
pip3 install pyinstaller
```

### Compilar:
```bash
pyinstaller --windowed --name "CryptoWorkerInstaller" \
    --icon installer_icon.icns \
    --add-data "auto_install_worker.sh:." \
    install_worker_mac.py
```

### Resultado:
```
dist/
└── CryptoWorkerInstaller.app/
    └── Contents/
        └── MacOS/
            └── CryptoWorkerInstaller
```

### Crear .dmg (opcional):
```bash
# Instalar create-dmg
brew install create-dmg

# Crear DMG
create-dmg \
    --volname "Crypto Worker Installer" \
    --volicon "installer_icon.icns" \
    --window-pos 400 200 \
    --window-size 600 400 \
    --app-drop-link 400 200 \
    "Crypto Worker Installer.dmg" \
    "dist/CryptoWorkerInstaller.app"
```

---

## 🪟 COMPILAR PARA WINDOWS (.exe)

### Requisitos (en Windows):
```powershell
# Instalar Python
# Descargar desde: https://python.org/downloads/

# Instalar PyInstaller
pip install pyinstaller
```

### Compilar:
```powershell
pyinstaller --onefile --windowed ^
    --name "CryptoWorkerInstaller" ^
    --icon installer_icon.ico ^
    install_worker_windows.py
```

### Resultado:
```
dist/
└── CryptoWorkerInstaller.exe
```

### Crear instalador con NSIS (opcional):
```nsis
# Descargar NSIS desde: https://nsis.sourceforge.io/Download

# Crear script de instalación
!include "MUI2.nsh"

Name "Crypto Worker Installer"
OutFile "CryptoWorkerSetup.exe"
InstallDir "$PROGRAMFILES\CryptoWorker"

Section
    SetOutPath "$INSTDIR"
    File "dist\CryptoWorkerInstaller.exe"
    File "install_worker.bat"
    
    CreateDirectory "$SMPROGRAMS\CryptoWorker"
    CreateShortcut "$SMPROGRAMS\CryptoWorker\Crypto Worker.lnk" "$INSTDIR\CryptoWorkerInstaller.exe"
    CreateShortcut "$SMPROGRAMS\CryptoWorker\Uninstall.lnk" "$INSTDIR\uninstall.exe"
SectionEnd
```

---

## 🐧 COMPILAR PARA LINUX (.deb)

### Requisitos:
```bash
# Instalar PyInstaller
pip3 install pyinstaller
```

### Compilar:
```bash
pyinstaller --onefile \
    --name "crypto-worker-installer" \
    install_worker_linux.py
```

### Crear .deb package:
```bash
# Estructura del paquete
mkdir -p crypto-worker-installer/usr/bin
mkdir -p crypto-worker-installer/usr/share/applications
mkdir -p crypto-worker-installer/usr/share/icons

# Copiar ejecutable
cp dist/crypto-worker-installer crypto-worker-installer/usr/bin/

# Crear archivo .desktop
cat > crypto-worker-installer/usr/share/applications/crypto-worker-installer.desktop << 'EOF'
[Desktop Entry]
Name=Crypto Worker Installer
Comment=Install trading system worker
Exec=/usr/bin/crypto-worker-installer
Icon=installer_icon
Terminal=false
Type=Application
Categories=Utility;
EOF

# Empaquetar
dpkg-deb --build crypto-worker-installer
```

### Resultado:
```
crypto-worker-installer.deb
```

### Instalar:
```bash
sudo dpkg -i crypto-worker-installer.deb
sudo apt-get install -f  # Si hay dependencias
```

---

## 📱 DISTRIBUCIÓN A AMIGOS/COLABORADORES

### Opción 1: Enlace directo (más simple)

```bash
# macOS/Linux
bash -c "$(curl -fsSL https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main/auto_install_worker.sh)"

# Windows
# Descargar: https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main/install_worker.bat
```

### Opción 2: Ejecutables nativos

#### macOS:
1. Compila el .app como se indica arriba
2. Sube a GitHub Releases o Google Drive
3. Envía el enlace

#### Windows:
1. Compila el .exe
2. Sube a GitHub Releases o Google Drive
3. Envía el enlace

#### Linux:
1. Compila el .deb
2. Sube a GitHub Releases o Google Drive
3. Envía el enlace

---

## 🔧 CONFIGURACIÓN PARA COMPILACIÓN

### instalador_icon.py (para generar iconos):

```python
# Crear icono simple
from PIL import Image

# 256x256 icon
img = Image.new('RGB', (256, 256), color='#2E86AB')
img.save('installer_icon.png')

# Convertir a formato específico
# macOS: .icns (usar iconutil en macOS)
# Windows: .ico (usar online converter)
# Linux: .png
```

---

## 📋 GUÍA PARA USUARIOS FINALES

### 🍎 macOS:
1. Descargar: `CryptoWorkerInstaller.dmg`
2. Doble clic para abrir
3. Arrastrar a Aplicaciones
4. Ejecutar desde Aplicaciones

### 🪟 Windows:
1. Descargar: `CryptoWorkerSetup.exe`
2. Doble clic para ejecutar
3. Seguir las instrucciones en pantalla

### 🐧 Linux:
1. Descargar: `crypto-worker-installer.deb`
2. Doble clic para instalar
3. Buscar "Crypto Worker" en aplicaciones

---

## 📞 SOPORTE

Si hay problemas:

1. **Verificar Python**: `python --version`
2. **Verificar Git**: `git --version`
3. **Revisar logs**: Carpeta `~/.crypto_worker/`

---

## 🎯 RESUMEN RÁPIDO

| Plataforma | Installador | Ejecutable |
|------------|-------------|-------------|
| macOS | `bash auto_install_worker.sh` | .app (con PyInstaller) |
| Windows | `install_worker.bat` | .exe (con PyInstaller) |
| Linux | `bash auto_install_worker.sh` | .deb (con PyInstaller) |

---

**¡Listo para distribuir!** 🚀
