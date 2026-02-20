# 🚀 CÓMO CONFIGURAR EL WORKER (MacBook Pro)

## ⚡ OPCIÓN 1: Script Automático (RECOMENDADO)

### Paso 1: Copia el script al Worker

En **ESTA MÁQUINA (Head)**, ejecuta:

```bash
# Si el worker está accesible por red (misma carpeta de Google Drive):
# Ya está copiado automáticamente

# Si necesitas enviarlo por AirDrop o USB:
# El archivo está en: WORKER_AUTO_SETUP.sh
```

### Paso 2: Ejecuta en el Worker

En **TU MACBOOK PRO (Worker)**, abre Terminal y ejecuta:

```bash
# Navegar al proyecto (ajusta la ruta si es diferente)
cd "/Users/TU_USUARIO/Library/CloudStorage/GoogleDrive-XXX/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

# Dar permisos de ejecución
chmod +x WORKER_AUTO_SETUP.sh

# Ejecutar
./WORKER_AUTO_SETUP.sh
```

**El script hará TODO automáticamente:**
1. ✅ Detectar el proyecto
2. ✅ Detener Ray antiguo
3. ✅ Obtener IP del Head Node
4. ✅ Verificar conectividad
5. ✅ Instalar dependencias
6. ✅ Iniciar worker
7. ✅ Verificar conexión

---

## 🔧 OPCIÓN 2: Manual (Si el script falla)

### Paso 1: Navegar al proyecto

```bash
cd "/Users/TU_USUARIO/Library/CloudStorage/GoogleDrive-XXX/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
```

### Paso 2: Detener Ray antiguo

```bash
.venv/bin/ray stop --force
pkill -f "ray::"
```

### Paso 3: Iniciar Worker

```bash
# Configurar IP del Head (usa la IP de esta máquina)
export RAY_ADDRESS="10.0.0.239:6379"

# Iniciar worker
.venv/bin/ray start --address=10.0.0.239:6379 --num-cpus=$(sysctl -n hw.ncpu)
```

### Paso 4: Verificar

```bash
.venv/bin/ray status
```

Deberías ver:
```
Active:
 2 node_xxxxx
 2 node_yyyyy

Resources:
 0.0/22.0 CPU  ← ¡22 CPUs!
```

---

## 🔍 VERIFICAR EN EL HEAD (Esta máquina)

Después de configurar el worker, verifica aquí:

```bash
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

.venv/bin/ray status
```

Deberías ver **2 nodos activos** y **22 CPUs totales**.

---

## ⚡ EJECUTAR STRATEGY MINER CON 22 CPUS

Una vez el worker esté conectado, ejecuta:

```python
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

.venv/bin/python3 << 'EOF'
import pandas as pd
from strategy_miner import StrategyMiner

# Cargar datos
df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")
print(f"Dataset: {len(df)} velas")

# Configurar miner (CORRECTO)
miner = StrategyMiner(
    df=df,
    population_size=100,  # 100 estrategias
    generations=50,       # 50 generaciones
    risk_level="LOW",
    force_local=False     # ¡USAR RAY!
)

# Ejecutar
def progress(msg_type, data):
    if msg_type == "START_GEN":
        print(f"\n🧬 Generación {data}/50")
    elif msg_type == "BEST_GEN":
        print(f"   🏆 Mejor PnL: ${data.get('pnl', 0):.2f}")

best_genome, best_pnl = miner.run(progress_callback=progress)

print(f"\n\n{'='*80}")
print(f"🏆 RESULTADO FINAL: ${best_pnl:.2f}")
print(f"{'='*80}")
EOF
```

---

## 📊 MONITOREAR EN TIEMPO REAL

Abre el dashboard de Ray en tu navegador:

```
http://10.0.0.239:8265
```

Verás:
- 📈 CPUs en uso (debería llegar a ~22/22)
- 🔄 Tareas en ejecución
- ⏱️ Tiempo por tarea
- 📊 Distribución entre nodos

---

## ⚠️ TROUBLESHOOTING

### "No se puede conectar al Head"
- Verifica que ambas máquinas estén en la misma red WiFi
- Ping: `ping 10.0.0.239`
- Firewall desactivado

### "Version mismatch"
- Ambas máquinas deben usar Python 3.9.6
- Reinstalar Ray: `.venv/bin/pip install --force-reinstall "ray[default]==2.51.2"`

### "Worker se desconecta"
- macOS está durmiendo la máquina
- System Settings → Energy → "Prevent automatic sleeping"
- O usa Amphetamine (app gratuita)

### "Solo usa 10 CPUs en vez de 22"
- Worker no está conectado
- Ejecutar `ray status` en ambas máquinas
- Verificar que aparezcan 2 nodos

---

## ✅ SEÑALES DE ÉXITO

### En el Worker:
```
Ray runtime started.
Connected to Ray cluster.
```

### En el Head:
```
Active:
 2 node_xxxxx
Resources:
 0.0/22.0 CPU
```

### Durante Miner:
```
🧬 Generación 5/50
   🏆 Mejor PnL: $234.50

[Ray Dashboard muestra CPUs al 90-100%]
```

---

## 🎯 EXPECTATIVAS DE TIEMPO

Con 22 CPUs distribuidos:

| Configuración | Tiempo Estimado |
|---------------|----------------|
| Pop:50, Gen:20 | 5-10 minutos |
| Pop:100, Gen:50 | 20-30 minutos |
| Pop:200, Gen:100 | 60-90 minutos |

Sin distribución (solo Head, 10 CPUs):
- ×2.2 más lento

---

## 💡 PRÓXIMO PASO

1. ✅ Configura el worker con el script automático
2. ✅ Verifica conexión con `ray status`
3. ✅ Ejecuta Strategy Miner con configuración correcta
4. ⏳ Espera pacientemente mientras evoluciona
5. 🎉 Disfruta de estrategias rentables con PnL positivo

---

**¿Dudas?** Revisa `SOLUCION_PNL_NEGATIVO.md` para más detalles.
