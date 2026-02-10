# 🚀 INSTALACIÓN RÁPIDA - WORKERS ADICIONALES

## Bienvenido al Sistema de Trading Distribuido

Este documento te guia para agregar tu máquina al cluster de trading y contribuir con poder de cómputo.

---

## 📋 REQUISITOS

| Requisito | Detalle |
|------------|---------|
| **Python** | 3.9 o superior |
| **Git** | Para clonar el proyecto |
| **Internet** | Para conectar al coordinator |
| **CPU** | Mínimo 2 cores (recomendado 4+) |

---

## 🖥️ INSTALACIÓN POR SISTEMA OPERATIVO

### 🍎 macOS (MacBook, iMac, Mac Mini)

```bash
# Opción 1: Con un solo comando (recomendado)
bash -c "$(curl -fsSL https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main/auto_install_worker.sh)"

# Opción 2: Manual
git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git
cd Coinbase-Cripto-Trader-Claude
chmod +x auto_install_worker.sh
./auto_install_worker.sh
```

**Qué hace el script:**
- ✅ Instala Homebrew si no lo tienes
- ✅ Instala Python 3 y Git
- ✅ Clona el proyecto
- ✅ Configura workers según tus CPUs
- ✅ Configura auto-arranque al reiniciar

---

### 🐧 Linux (Ubuntu, Debian, Fedora, etc.)

```bash
# Opción 1: Con un solo comando
bash -c "$(curl -fsSL https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main/auto_install_worker.sh)"

# Opción 2: Manual
git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git
cd Coinbase-Cripto-Trader-Claude
chmod +x auto_install_worker.sh
./auto_install_worker.sh
```

**Qué hace el script:**
- ✅ Instala Python 3 y Git
- ✅ Clona el proyecto
- ✅ Configura workers según tus CPUs
- ✅ Configura servicio systemd para auto-arranque

---

### 🪟 Windows (10/11)

**Opción 1: Script Batch (recomendado)**

```powershell
# Descargar script
curl -O https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main/install_worker.bat

# Ejecutar como Administrador (clic derecho → Ejecutar como administrador)
install_worker.bat
```

**Opción 2: Manual**

```powershell
# 1. Instalar Python desde https://python.org/downloads/
#   - IMPORTANTE: Marcar "Add Python to PATH"

# 2. Instalar Git desde https://git-scm.com/download/win

# 3. Abrir CMD como Administrador
git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git
cd Coinbase-Cripto-Trader-Claude
install_worker.bat
```

**Qué hace el script:**
- ✅ Detecta Python instalado
- ✅ Instala paquetes necesarios
- ✅ Clona el proyecto
- ✅ Configura workers según tus CPUs
- ✅ Configura auto-arranque al iniciar Windows

---

## ⚙️ CONFIGURACIÓN AVANZADA

### Cambiar número de workers

Por defecto, el script usa CPUs-2 workers (deja 2 cores para el sistema).

```bash
# Para usar todos los CPUs (no recomendado)
WORKERS_COUNT=8 ./auto_install_worker.sh

# Para especificar manualmente
WORKERS_COUNT=4 ./auto_install_worker.sh
```

### Cambiar Coordinator URL

```bash
# Para especificar otro coordinator
COORDINATOR_URL=http://OTRA-IP:5001 ./auto_install_worker.sh

# Ejemplo:
COORDINATOR_URL=http://192.168.1.100:5001 ./auto_install_worker.sh
```

---

## 📊 VERIFICACIÓN

### Verificar que está funcionando

```bash
# Ver procesos
ps aux | grep crypto_worker

# Ver logs
tail -f ~/.crypto_worker/worker_1.log

# Ver estado del coordinator (desde cualquier máquina)
curl http://100.77.179.14:5001/api/status
```

### Ver dashboard web

Abre en tu navegador:
```
http://100.77.179.14:5001
```

---

## 🔧 COMANDOS ÚTILES

### macOS/Linux

```bash
# Ver workers activos
ps aux | grep crypto_worker

# Ver logs en tiempo real
tail -f ~/.crypto_worker/worker_1.log

# Reiniciar workers
~/.crypto_worker/start_workers.sh

# Ver status del coordinator
curl http://100.77.179.14:5001/api/status

# Detener todos los workers
pkill -f crypto_worker
```

### Windows

```bat
REM Ver workers activos
tasklist /fi "ImageName eq python.exe"

REM Ver logs
type %USERPROFILE%\.crypto_worker\worker_1.log

REM Reiniciar workers
%USERPROFILE%\.crypto_worker\start_workers.bat

REM Ver status del coordinator
curl http://100.77.179.14:5001/api/status
```

---

## 🚨 SOLUCIÓN DE PROBLEMAS

### "Python no encontrado"

**macOS:**
```bash
brew install python3
```

**Linux:**
```bash
sudo apt install python3 python3-pip
```

**Windows:**
Descarga Python desde https://python.org/downloads/

---

### "Git no encontrado"

**macOS:**
```bash
brew install git
```

**Linux:**
```bash
sudo apt install git
```

**Windows:**
Descarga Git desde https://git-scm.com/download/win

---

### "Coordinator no accesible"

1. Verifica que el coordinator esté ejecutándose
2. Verifica que estás en la misma red
3. Verifica el firewall:
   - **macOS:** System Settings → Firewall → Allow incoming connections
   - **Linux:** `sudo ufw allow 5001`
   - **Windows:** Allow through Windows Firewall

---

### "Error de permisos"

Ejecuta como **Administrador** (Windows) o con **sudo** (Linux):
```bash
sudo ./auto_install_worker.sh
```

---

## 📁 ARCHIVOS CREADOS

| Archivo/Directorio | Descripción |
|---------------------|-------------|
| `~/.crypto_worker/` | Directorio de configuración y logs |
| `~/.crypto_worker/worker.env` | Variables de entorno |
| `~/.crypto_worker/start_workers.sh` | Script para reiniciar workers |
| `~/.crypto_worker/worker_*.log` | Logs de cada worker |
| `~/Coinbase-Cripto-Trader-Claude/` | Proyecto clonado |

---

## 🔄 ACTUALIZAR A NUEVA VERSIÓN

```bash
cd ~/Coinbase-Cripto-Trader-Claude
git pull origin main
./auto_install_worker.sh
```

---

## 📞 SOPORTE

Si tienes problemas:

1. **Verifica los logs:** `cat ~/.crypto_worker/install.log`
2. **Verifica el status:** `curl http://100.77.179.14:5001/api/status`
3. **Contacta** al administrador del sistema

---

## 🎯 RESUMEN RÁPIDO

```bash
# 🍎 macOS / 🐧 Linux
bash -c "$(curl -fsSL https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main/auto_install_worker.sh)"

# 🪟 Windows (como Administrador)
# Descargar y ejecutar: install_worker.bat
```

**¡Listo! Tu máquina ahora forma parte del cluster de trading.** 🎉
