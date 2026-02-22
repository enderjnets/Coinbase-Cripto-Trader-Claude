# 📋 RESUMEN DEL PROYECTO - COINBASE CRIPTO TRADER

## 📁 Ubicación del Proyecto
```
/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude
```

## 🌐 Dashboard
- **URL:** http://localhost:5001

## 🐙 GitHub
```
https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude
```

## 📊 Estado Actual
- Work Units completadas: ~6,400
- Workers activos: 23
- Mejor estrategia: $1,843 PnL, 12 trades, 75% win rate

## 📂 Archivos Principales
- `coordinator_port5001.py` - Servidor REST
- `strategy_miner.py` - Algoritmo genético
- `coinbase_advanced_trader.py` - Cliente API futuros
- `crypto_worker.py` - Worker ejecutor

## ⚠️ PROBLEMA DEL DASHBOARD

El dashboard muestra PnL inflados (miles de millones) porque hay resultados con bugs en el backtester.

### 🔧 Solución

1. **Limpiar resultados inflados en SQLite:**
```bash
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
sqlite3 coordinator.db "
UPDATE results SET is_canonical = 0;
UPDATE results SET is_canonical = 1 WHERE id IN (
    SELECT id FROM results 
    WHERE pnl > 0 AND pnl < 5000 AND trades >= 10
    ORDER BY pnl DESC LIMIT 10
);"
```

2. **Reiniciar coordinator:**
```bash
pkill -f coordinator_port5001
source ~/coinbase_trader_venv/bin/activate
python coordinator_port5001.py &
```

## 📦 Credenciales API
- **Path:** `/Users/enderj/Downloads/cdp_api_key.json`
- **Key ID:** `f2b19384-cbfd-4e6b-ab21-38a29f53650b`

## 📋 Comandos útiles

Ver estado:
```bash
curl http://localhost:5001/api/status
```

Ver mejores resultados:
```bash
curl http://localhost:5001/api/results
```

Ver workers:
```bash
curl http://localhost:5001/api/workers
```

## 🎯 Objetivos
- Encontrar estrategias rentables para trading de futuros
- Objetivo: 2-5% diario
- Usar apalancamiento hasta 10x
- Trading automático

## 📞 Para otra IA
- Este proyecto es un sistema distribuido de mining de estrategias
- Coordina múltiples workers para ejecutar backtests en paralelo
- Usa algoritmo genético para evolucionar estrategias
- Integración con API de Coinbase Advanced Trade

---

*Actualizado: 23 Feb 2026*
