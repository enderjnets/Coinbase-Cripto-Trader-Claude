# SKILL: Configurar Worker para Sistema Distribuido de Strategy Mining

## Descripción
Este skill permite a una IA configurar y ejecutar un worker que contribuye al sistema distribuido de búsqueda de estrategias de trading.

## Requisitos Previos
- Python 3.9+ instalado
- Acceso a la carpeta del proyecto (Google Drive sincronizado)
- Conexión de red al coordinador

## Información del Coordinador
- **URL del Coordinador:** `http://100.118.215.73:5001` (MacBook Pro via Tailscale)
- **Alternativa local:** `http://localhost:5001` (si el coordinador corre localmente)

---

## INSTRUCCIONES PASO A PASO

### Paso 1: Crear Entorno Virtual
```bash
# Crear entorno virtual en el home del usuario (evita problemas con Google Drive)
python3 -m venv ~/coinbase_trader_venv
```

### Paso 2: Instalar Dependencias
```bash
source ~/coinbase_trader_venv/bin/activate
pip install streamlit pandas pandas_ta plotly python-dotenv requests flask "ray[default]" coinbase-advanced-py
```

### Paso 3: Navegar al Proyecto
```bash
cd "/Users/[USERNAME]/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
```
**NOTA:** Reemplaza `[USERNAME]` con el nombre de usuario del sistema.

### Paso 4: Verificar Conectividad con el Coordinador
```bash
curl -s http://100.118.215.73:5001/api/status | python3 -m json.tool
```
Deberías ver algo como:
```json
{
    "work_units": {
        "completed": X,
        "in_progress": Y,
        "pending": Z,
        "total": N
    },
    "workers": {
        "active": W
    }
}
```

### Paso 5: Crear Script de Auto-Reinicio
Crear archivo `auto_worker.sh` en el directorio del proyecto:

```bash
#!/bin/bash
PROJECT_DIR="/Users/[USERNAME]/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
VENV_PATH="$HOME/coinbase_trader_venv"
LOG_FILE="/tmp/worker_output.log"
COORDINATOR_URL="http://100.118.215.73:5001"

echo "========================================"
echo "AUTO-WORKER MONITOR"
echo "========================================"

restart_count=0

while true; do
    pkill -f raylet 2>/dev/null
    pkill -f "ray::" 2>/dev/null
    sleep 2

    restart_count=$((restart_count + 1))
    echo ""
    echo "Iniciando worker (intento #$restart_count) - $(date)"

    source "$VENV_PATH/bin/activate"
    cd "$PROJECT_DIR"

    COORDINATOR_URL="$COORDINATOR_URL" PYTHONUNBUFFERED=1 python -u crypto_worker.py 2>&1 | tee -a "$LOG_FILE"

    echo "Worker terminó. Reiniciando en 5 segundos..."
    sleep 5
done
```

### Paso 6: Hacer Ejecutable y Lanzar
```bash
chmod +x auto_worker.sh
nohup ./auto_worker.sh > /tmp/auto_worker.log 2>&1 &
echo "Worker iniciado"
```

### Paso 7: Verificar que Funciona
```bash
# Ver log del worker
tail -50 /tmp/auto_worker.log

# Verificar status del coordinador
curl -s http://100.118.215.73:5001/api/workers | python3 -m json.tool
```

---

## COMANDOS DE MONITOREO

### Ver progreso del worker local:
```bash
grep -E "Gen [0-9]+.*PnL|intento #" /tmp/auto_worker.log | tail -20
```

### Ver estado del sistema:
```bash
curl -s http://100.118.215.73:5001/api/status | python3 -m json.tool
```

### Ver todos los workers conectados:
```bash
curl -s http://100.118.215.73:5001/api/workers | python3 -m json.tool
```

### Detener el worker:
```bash
pkill -f auto_worker.sh
pkill -f crypto_worker
```

---

## NOTAS IMPORTANTES

1. **Ray puede fallar** después de ~60 segundos en macOS. El script `auto_worker.sh` lo reinicia automáticamente.

2. **El worker necesita acceso a los datos** en `data/BTC-USD_*.csv`. Asegúrate de que Google Drive esté sincronizado.

3. **Cada worker contribuye** al descubrimiento de estrategias rentables. Más workers = búsqueda más rápida.

4. **El coordinador asigna trabajo automáticamente**. No necesitas configurar nada más.

---

## RESUMEN DE COMANDOS (COPIAR Y PEGAR)

```bash
# Setup completo (ejecutar línea por línea)
python3 -m venv ~/coinbase_trader_venv
source ~/coinbase_trader_venv/bin/activate
pip install streamlit pandas pandas_ta plotly python-dotenv requests flask "ray[default]" coinbase-advanced-py

# Ir al proyecto (ajustar username)
cd "/Users/$(whoami)/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

# Verificar coordinador
curl -s http://100.118.215.73:5001/api/status

# Lanzar worker con auto-reinicio
chmod +x auto_worker.sh
nohup ./auto_worker.sh > /tmp/auto_worker.log 2>&1 &

# Monitorear
tail -f /tmp/auto_worker.log
```
