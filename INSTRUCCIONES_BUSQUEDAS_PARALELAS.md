# 🚀 BÚSQUEDAS PARALELAS - MacBook Pro + MacBook Air

**Configurado:** 30 Enero 2026, 17:00 PM

---

## 📋 RESUMEN

Vamos a ejecutar **2 búsquedas simultáneas** en diferentes máquinas con diferentes configuraciones:

| Máquina | Risk Level | Población | Generaciones | Estrategias | Tiempo |
|---------|------------|-----------|--------------|-------------|--------|
| **MacBook PRO** | MEDIUM | 40 | 30 | 1,200 | ~45 min |
| **MacBook AIR** | LOW | 50 | 25 | 1,250 | ~55 min |
| **TOTAL** | - | - | - | **2,450** | ~55 min |

**Ventaja:** 2,450 estrategias evaluadas en ~1 hora (vs 600 en 27 min con búsqueda simple)

---

## ✅ PASO 1: PREPARAR MACBOOK AIR

### 1.1 Copiar proyecto a MacBook Air

**Desde MacBook Pro (ESTA MÁQUINA), ejecuta:**

```bash
# Crear carpeta en MacBook Air
ssh enderj@100.77.179.14 "mkdir -p '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude'"

# Copiar archivos necesarios
scp run_miner_AIR.py \
    strategy_miner.py \
    backtester.py \
    dynamic_strategy.py \
    data/BTC-USD_FIVE_MINUTE.csv \
    enderj@100.77.179.14:"/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/"
```

**O TODO EN UN COMANDO:**
```bash
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

rsync -avz --progress \
  run_miner_AIR.py \
  strategy_miner.py \
  backtester.py \
  dynamic_strategy.py \
  data/ \
  enderj@100.77.179.14:"/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/"
```

---

## 🚀 PASO 2: EJECUTAR BÚSQUEDAS

### 2.1 En MacBook AIR (primero)

**Opción A: Por SSH desde aquí (FÁCIL):**
```bash
ssh enderj@100.77.179.14 "cd '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude' && python3 run_miner_AIR.py 2>&1 | tee miner_AIR_\$(date +%Y%m%d_%H%M%S).log"
```

**Opción B: Conectarte a la AIR y ejecutar:**
```bash
# 1. Conectarse
ssh enderj@100.77.179.14

# 2. Navegar
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

# 3. Ejecutar
python3 run_miner_AIR.py 2>&1 | tee miner_AIR_$(date +%Y%m%d_%H%M%S).log
```

### 2.2 En MacBook PRO (después, desde aquí)

**En una nueva terminal (mientras la AIR corre):**

```bash
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

python3 run_miner_PRO.py 2>&1 | tee miner_PRO_$(date +%Y%m%d_%H%M%S).log
```

---

## 📊 PASO 3: MONITOREAR PROGRESO

### Monitorear MacBook AIR:
```bash
# Ver progreso en tiempo real
ssh enderj@100.77.179.14 "tail -f '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/miner_AIR_*.log'" | grep -E "Gen |PnL"
```

### Monitorear MacBook PRO:
```bash
# Ver últimas líneas del log
tail -f miner_PRO_*.log | grep -E "Gen |PnL"
```

---

## 🏆 PASO 4: ANALIZAR RESULTADOS

**Cuando AMBAS búsquedas terminen:**

```bash
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

# Copiar resultados de MacBook AIR
scp enderj@100.77.179.14:"/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/BEST_STRATEGY_AIR_*.json" .
scp enderj@100.77.179.14:"/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/all_strategies_AIR_*.json" .

# Ejecutar comparador
python3 compare_results.py
```

**El comparador mostrará:**
- ✅ Comparación lado a lado de ambas estrategias
- 🏆 Ganador basado en score compuesto
- 📋 Reglas de la mejor estrategia
- 📈 Comparación con búsqueda anterior
- 💡 Próximos pasos recomendados

---

## 🎯 QUÉ ESPERAR

### MacBook PRO (MEDIUM risk):
- **Objetivo:** Estrategias con balance riesgo/retorno
- **SL/TP:** Moderados (2-5% SL, 4-10% TP)
- **Trades esperados:** 2-10
- **PnL objetivo:** $100-500

### MacBook AIR (LOW risk):
- **Objetivo:** Estrategias conservadoras
- **SL/TP:** Pequeños (1-3% SL, 2-6% TP)
- **Trades esperados:** 5-20
- **PnL objetivo:** $50-300 pero más consistente

**¿Cuál será mejor?** ¡Eso es lo que vamos a descubrir! 🎉

---

## ⏱️ TIMELINE ESPERADO

```
T+0 min:  Iniciar MacBook AIR
T+1 min:  Iniciar MacBook PRO
T+45 min: MacBook PRO termina (probablemente)
T+55 min: MacBook AIR termina
T+56 min: Copiar resultados de AIR
T+57 min: Ejecutar compare_results.py
T+58 min: ¡Ver ganador! 🏆
```

---

## 🔧 TROUBLESHOOTING

### Problema: "No such file or directory"
**Solución:** Verificar que copiaste todos los archivos necesarios
```bash
ssh enderj@100.77.179.14 "ls -la '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/'"
```

### Problema: "ModuleNotFoundError"
**Solución:** Instalar dependencias en MacBook AIR
```bash
ssh enderj@100.77.179.14 "pip3 install pandas numpy"
```

### Problema: MacBook AIR se desconecta
**Solución:** Usar screen o tmux
```bash
ssh enderj@100.77.179.14
screen -S miner
cd "..."
python3 run_miner_AIR.py
# Presiona Ctrl+A+D para desconectar
# Reconectar: screen -r miner
```

---

## 📁 ARCHIVOS GENERADOS

Al terminar, tendrás:

```
BEST_STRATEGY_PRO_[timestamp].json    # Mejor de MacBook PRO
BEST_STRATEGY_AIR_[timestamp].json    # Mejor de MacBook AIR
all_strategies_PRO_[timestamp].json   # Histórico PRO
all_strategies_AIR_[timestamp].json   # Histórico AIR
miner_PRO_[timestamp].log             # Log PRO
miner_AIR_[timestamp].log             # Log AIR (en AIR)
```

---

## 💡 TIPS IMPORTANTES

1. **Ejecuta AIR primero:** Tarda más, así que iníciala primero

2. **No cierres las terminales:** Mantén ambas abiertas mientras corren

3. **Puedes hacer otras cosas:** Las búsquedas corren en segundo plano

4. **Copia los resultados:** No olvides traer los archivos de la AIR con scp

5. **Compara SIEMPRE:** El script compare_results.py es clave para entender qué funcionó mejor

---

## 🎉 VENTAJAS DE ESTE ENFOQUE

✅ **Sin problemas de Ray:** Modo secuencial 100% estable
✅ **Máximo throughput:** 2,450 estrategias en ~1 hora
✅ **Diversidad:** Explora MEDIUM y LOW risk simultáneamente
✅ **Simplicidad:** No requiere configuración de cluster
✅ **Confiabilidad:** Ambas máquinas trabajan independientemente

---

## ❓ PREGUNTAS FRECUENTES

**Q: ¿Por qué no usar el cluster?**
A: Ray no soporta multi-nodo en macOS de forma confiable. Esto es más simple y estable.

**Q: ¿Puedo ejecutar solo una búsqueda?**
A: Sí, solo ejecuta run_miner_PRO.py o run_miner_AIR.py

**Q: ¿Qué pasa si una termina antes?**
A: Espera a que ambas terminen para compararlas. O analiza la que terminó primero.

**Q: ¿Puedo cambiar las configuraciones?**
A: Sí, edita run_miner_PRO.py o run_miner_AIR.py antes de ejecutar

---

**¿Listo para empezar?**

Cuando quieras, dime **"ejecutar búsquedas"** y te guío paso a paso.

