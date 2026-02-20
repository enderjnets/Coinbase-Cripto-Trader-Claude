# Crypto Worker Installer Package

Sistema distribuido de descubrimiento de estrategias de trading usando algoritmos genéticos.

## Requisitos

### Todos los sistemas:
- Python 3.9 o superior
- Conexión de red al coordinador
- ~100MB de espacio en disco

### Windows:
- Descargar Python desde https://python.org
- **IMPORTANTE:** Marcar "Add Python to PATH" durante la instalación

### macOS:
- Python 3 (viene preinstalado o instalar con `brew install python3`)

### Linux (Ubuntu/Debian):
- Python 3 (instalar con `sudo apt install python3 python3-venv python3-pip`)

---

## Instalación Rápida

### Windows
1. Extraer el ZIP
2. Hacer doble clic en `scripts\install_windows.bat`
3. Ingresar la URL del coordinador cuando se solicite
4. Ejecutar `run_worker.bat` en la carpeta de instalación

### macOS
```bash
# Extraer y navegar al directorio
cd Worker_Installer_Package

# Dar permisos y ejecutar
chmod +x scripts/install_mac.sh
./scripts/install_mac.sh

# Iniciar worker
cd ~/crypto_worker && ./run_worker.sh
```

### Linux
```bash
# Extraer y navegar al directorio
cd Worker_Installer_Package

# Dar permisos y ejecutar
chmod +x scripts/install_linux.sh
./scripts/install_linux.sh

# Iniciar worker
cd ~/crypto_worker && ./run_worker.sh
```

---

## URL del Coordinador

**URL preconfigurada:** `http://100.77.179.14:5001` (Tailscale)

Los instaladores ya incluyen la URL del coordinador. No necesitas configurar nada adicional.

**Requisito:** La máquina debe tener Tailscale instalado y conectado a la misma red.

**URLs alternativas (si no usas Tailscale):**
- Red local: `http://10.0.0.232:5001`
- Editar manualmente en `run_worker.sh` o `run_worker.bat`

---

## Ejecutar en Segundo Plano

### macOS/Linux
```bash
cd ~/crypto_worker
nohup ./run_worker.sh > /tmp/worker.log 2>&1 &
```

### Linux (como servicio systemd)
```bash
sudo cp ~/crypto_worker/crypto-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable crypto-worker
sudo systemctl start crypto-worker
```

### Windows
- Crear acceso directo de `run_worker.bat`
- Agregar a la carpeta de inicio para ejecución automática

---

## Monitoreo

### Ver logs del worker
```bash
# macOS/Linux
tail -f /tmp/worker_output.log

# Windows
type %TEMP%\worker_output.log
```

### Verificar conexión al coordinador
```bash
curl http://[COORDINATOR_URL]/api/status
```

---

## Solución de Problemas

### "No module named X"
Reinstalar dependencias:
```bash
# macOS/Linux
source ~/coinbase_worker_venv/bin/activate
pip install pandas pandas_ta requests ray python-dotenv

# Windows
%USERPROFILE%\coinbase_worker_venv\Scripts\activate
pip install pandas pandas_ta requests ray python-dotenv
```

### "Connection refused" al coordinador
- Verificar que el coordinador esté corriendo
- Verificar la URL y puerto
- Verificar firewall/conexión de red

### Worker se reinicia constantemente
- Normal: Ray puede fallar en algunos sistemas, el script lo reinicia automáticamente
- Los work units se completan aunque haya reinicios

---

## Estructura del Paquete

```
Worker_Installer_Package/
├── README.md                 # Este archivo
├── scripts/
│   ├── install_windows.bat   # Instalador Windows
│   ├── install_mac.sh        # Instalador macOS
│   └── install_linux.sh      # Instalador Linux
└── worker_files/
    ├── crypto_worker.py      # Worker principal
    ├── strategy_miner.py     # Algoritmo genético
    ├── backtester.py         # Motor de backtesting
    ├── config.py             # Configuración
    ├── strategy.py           # Estrategias
    ├── dynamic_strategy.py   # Estrategias dinámicas
    ├── data_manager.py       # Gestión de datos
    └── data/
        ├── BTC-USD_ONE_MINUTE.csv    # Datos 1 min
        └── BTC-USD_FIVE_MINUTE.csv   # Datos 5 min
```

---

## Contacto

Sistema desarrollado para Bittrader - Strategy Mining Distributed System
