# 🚀 Guía de Configuración de Cluster Distribuido (Ray)

Esta guía permite utilizar múltiples Macs para acelerar la optimización drásticamente, utilizando el poder combinado de todos tus procesadores.

## ✨ Características del Sistema
- **Auto-Discovery:** Los workers encuentran al Maestro automáticamente en la red.
- **Code Sync:** El código (`strategy.py`, `backtester.py`, etc.) se envía automáticamente del Maestro a los Workers al iniciar.
- **Setup Robusto:** Scripts alineados para evitar conflictos de versiones.

---

## 1. Preparación (En Mac Principal / Head Node)

Simplemente inicia la UI o el script dedicado:

```bash
python3 start_cluster_head.py
```
*Si usas la UI (`streamlit run interface.py`), el cluster se inicia automáticamente cuando comienza una optimización si usaste el script anterior.*

---

## 2. Preparación (En Macs Workers)

Cada Mac adicional necesita:
1. **Python 3.9+** instalado.
2. Copiar la carpeta del proyecto (o al menos el script `setup_worker.sh`).

**Pasos de Instalación:**

1. Abre una terminal en la carpeta del proyecto.
2. Ejecuta el instalador:
   ```bash
   chmod +x setup_worker.sh
   ./setup_worker.sh
   ```

El script realizará lo siguiente automáticamente:
- Creará un entorno virtual (`worker_env`).
- Instalará las dependencias **EXACTAS** requeridas:
  - `ray[default]`
  - `pandas`, `numpy` (Versión 2.0+ alineada con el Maestro)
  - `plotly`
  - `python-dotenv` (CRÍTICO para leer config)
  - `coinbase-advanced-py` (CRÍTICO si es importado por scanners)
- Se conectará al Maestro.

### 🪟 Para PCs con Windows (Nuevo)

Si tienes una PC Gamer (ej: ROG, Alienware), puedes usarla como worker.

1. Instala **Python 3.9** en Windows (asegúrate de marcar "Add Python to PATH" en el instalador).
2. Copia el archivo `setup_worker_windows.bat` a tu PC.
3. Haz doble click en el archivo.
4. Te pedirá la **IP del Maestro** (mírala en la pantalla de tu Mac, ej: 10.0.0.239).
5. ¡Listo! Se unirá al cluster automáticamente.

---

## 3. Verificación

Una vez conectados los workers:

1. **Prueba Rápida:**
   En la Mac Principal:
   ```bash
   python3 test_cluster.py
   ```
   Deberías ver `Active Nodes: 2` (o más) y la suma total de CPUs.

2. **Prueba Real:**
   Corre una optimización desde la UI. Verifica el log:
   `✅ Conectado a Cluster Ray existente (Modo Distribuido + Code Sync)`

---

## 🛠 Troubleshooting (Errores Comunes)

### 🔴 Error: `ModuleNotFoundError: No module named 'numpy._core.numeric'`
**Causa:** Conflicto de versiones de NumPy. El Maestro tiene NumPy 2.0+ y el Worker tiene una versión antigua (<2.0).
**Solución:**
El script `setup_worker.sh` ha sido actualizado para instalar la última versión. Ejecuta `./setup_worker.sh` nuevamente en el Worker.

### 🔴 Error: `ModuleNotFoundError: No module named 'dotenv'` o `'coinbase'`
**Causa:** Faltan librerías en el Worker que son importadas por el código compartido (aunque no se usen activamente en el worker, Python las chequea al importar).
**Solución:**
Asegúrate de que `setup_worker.sh` incluya `python-dotenv` y `coinbase-advanced-py`. Ejecútalo de nuevo.

### 🔴 El Worker se desconecta o da `Connection failed`
**Causa:** Firewall o IPs diferentes.
**Solución:**
- Verifica que ambas Macs estén en la misma red WiFi.
- Desactiva temporalmente el Firewall de macOS o permite conexiones entrantes a Python (`System Settings -> Network -> Firewall`).

### 🔴 Error: `TimeoutError: Backtest exceeded 120s/600s...`
**Causa:** Una prueba individual (Backtest) tomó demasiado tiempo y fue eliminada por seguridad.
**Solución:**
- El sistema ahora tiene un límite de **600 segundos (10 min)** por prueba. 
- Si sigue fallando, la estrategia es demasiado lenta o estás probando demasiados datos (años) con granularidad de 1 minuto. Reduce el rango de fechas.

### 🔴 Error: `SegFault` o `Raylet` crash al iniciar
**Causa:** A veces ocurre si mueves la carpeta del proyecto. Los ejecutables de Ray en `.venv/bin/ray` tienen rutas absolutas hardcodeadas ("shebang").
**Solución:**
- Reinstala Ray forzando la regeneración de scripts:
  ```bash
  .venv/bin/python -m pip install --force-reinstall "ray[default]"
  ```

### 🔴 Procesos "Zombie" (CPU al 100% después de Stop)
**Causa:** Ray no siempre limpia todos los workers si se mata el proceso principal abruptamente.
**Solución:**
- Usa el botón **"💀 Force Kill Ray (Panic)"** en la interfaz.
- O ejecuta en terminal:
  ```bash
  pkill -f "ray::"
  ray stop --force
  ```

### ⚡ Optimización Lenta (Solo usa 1 CPU)
**Causa:** Optuna por defecto es secuencial (`n_jobs=1`).
**Solución:**
- El código ahora detecta automáticamente tus CPUs y lanza hilos en paralelo (`n_jobs=20` etc).
- Asegúrate de tener **"Distributed Mode"** activo (o no marcar "Force Local").

### 😴 El Worker deja de trabajar (Status DEAD después de un tiempo)
**Causa:** macOS "Sleep Mode" o "App Nap" corta la conexión WiFi y pausa procesos en background.
**Solución:**
- Configura la Mac Worker para no dormir: *System Settings -> Energy Saver -> "Prevent automatic sleeping when display is off"*.
- O usa una app como **Amphetamine**.
- Si se desconecta, simplemente despiértala y corre `./setup_worker.sh` de nuevo (se reconecta "en caliente").
