# 📋 ESPECIFICACIONES TÉCNICAS
# Sistema de Trading Algorítmico Autónoma
# Coinbase Cripto Trader Claude v1.0
# 2026-02-10

## 📊 ARQUITECTURA DEL SISTEMA

### Componentes Principales
1. **Coordinator Server** (Puerto 5001/5005/5006)
   - API REST para gestión de Work Units
   - Base de datos SQLite distribuida
   - Scheduler de tareas
   - Validación de resultados

2. **Workers Distribuidos** (18+ máquinas)
   - Backtesting distribuido
   - Algoritmo genético paralelizado
   - Checkpoints para recuperación
   - Reporte de progreso en tiempo real

3. **Dashboards**
   - F1 Racing Dashboard (Puerto 5006)
   - Streamlit Interface (Puerto 8501)
   - API RESTful (Puerto 5001/5005)

---

## 🎯 OBJETIVOS DE RENDIMIENTO

### Metas Cuantificables
| Objetivo | Meta | Actual | Progreso |
|----------|-------|---------|----------|
| Doblar capital mensual | +100% | - | 0% |
| Win Rate | >60% | - | - |
| Profit Factor | >1.5 | - | - |
| Max Drawdown | <10% | - | - |
| Sharpe Ratio | >1.0 | - | - |
| Workers activos | 20+ | 23 | ✅ |
| Work Units/día | 1000+ | 26 | 2.6% |
| Tiempo promedio WU | <10s | 6.08s | ✅ |

---

## 🧬 ALGORITMO GENÉTICO

### Parámetros de Evolución
```python
{
    "population_size": 100,
    "generations": 100,
    "mutation_rate": 0.15,
    "crossover_rate": 0.8,
    "elite_rate": 0.1,
    "tournament_size": 5
}
```

### Funciones de Fitness
```python
def calculate_fitness(genome):
    score = genome.pnl + genome.trades * 10 + genome.win_rate * 2
    return score
```

---

## 💰 GESTIÓN DE RIESGO

### Por Trade
| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| Capital base | $500 | Capital inicial |
| Risk/trade | 2% | Máximo riesgo por operación |
| Stop Loss | 5% | Pérdida máxima aceptada |
| Take Profit | 10% | Ganancia objetivo |
| Trailing Stop | 3% | Protección de ganancias |
| Max posiciones | 5 | Diversificación |

### Gestión de Capital
```
Capital disponible = $500
Posición máx = $500 × 0.02 = $10/trade
Stop Loss = Entrada × 0.95
Take Profit = Entrada × 1.10
```

---

## 📊 TIMEFRAMES SOPORTADOS

### Datasets Descargados
| Timeframe | Granularidad | Días | Velas |
|-----------|-------------|-------|-------|
| 1m | 60s | 730 | ~35,000 |
| 5m | 300s | 730 | ~35,000 |
| 15m | 900s | 730 | ~35,000 |
| 30m | 1,800s | 730 | ~35,000 |
| 1h | 3,600s | 730 | ~35,000 |

### Activos Incluidos
1. Bitcoin (BTC-USD) ✅
2. Ethereum (ETH-USD) ✅
3. Solana (SOL-USD) ✅
4. +30+ activos más

---

## 🔧 TECHNOLOGÍAS UTILIZADAS

### Backend
| Tecnología | Versión | Uso |
|------------|----------|-----|
| Python | 3.13/3.14 | Lógica principal |
| Flask | - | API REST |
| SQLite | - | Base de datos |
| Ray | - | Paralelización |
| Numba | JIT | Aceleración |

### Frontend
| Tecnología | Uso |
|------------|-----|
| Streamlit | Dashboard interactivo |
| Plotly | Gráficos |
| Custom CSS | Estilos F1 Racing |
| JavaScript | Frontend |

### Infraestructura
| Componente | Estado |
|------------|--------|
| Tailscale VPN | ✅ Conectado |
| Workers distribuidos | 23 activos |
| Checkpoints | Implementado |
| Fallback mode | ✅ Listo |

---

## 📈 MÉTRICAS DE MONITOREO

### KPIs del Dashboard
```json
{
    "workers": {
        "total": 35,
        "active": 23,
        "inactive": 12
    },
    "work_units": {
        "total": 26,
        "completed": 18,
        "in_progress": 8,
        "pending": 0
    },
    "best_strategy": {
        "pnl": 230.71,
        "win_rate": 0.65,
        "execution_time": 6.08
    }
}
```

### Contribución por Máquina
| Máquina | Workers | WUs | Contribución |
|----------|---------|-----|-------------|
| MacBook Pro | 3 | 38,899 | 57.6% |
| Linux ROG | 10 | 1,572 | 24.6% |
| MacBook Air | 4 | 333 | 16.4% |
| enderj Linux | 4 | 479 | 1.4% |

---

## 🔄 FLUJO DE TRABAJO

### Ciclo de Optimización
```
1. Descargar datos → 2. Generar WUs → 3. Distribuir a workers
   ↓
4. Ejecutar backtests ← 5. Evolucionar genomas
   ↓
6. Guardar mejores → 7. Reiniciar ciclo
```

### Criterios de Parada
- Generaciones completadas: 100
- Convergencia alcanzada
- Tiempo máximo: 24 horas
- Workers disponibles: 20+

---

## 🛡️ TOLERANCIA A FALLOS

### Recuperación Automática
- Checkpoints cada 5 generaciones
- Retry de tareas fallidas (3 intentos)
- Fallback a modo local si Ray falla
- Persistencia en SQLite

### Validación de Resultados
```python
def validate_result(result):
    if result.pnl > -9999:
        return True
    return False
```

---

## 📁 ESTRUCTURA DE ARCHIVOS

```
/Users/enderj/.../
├── coordinator.py              # Coordinator principal
├── coordinator.db           # Base de datos
├── crypto_worker.py         # Worker principal
├── strategy_miner.py       # Algoritmo genético
├── f1_dashboard.py       # Dashboard F1
├── data/                   # CSVs de estrategias
├── worker_daemon.sh        # Reinicio automático
└── autonomous/              # Scripts de mantenimiento
```

---

## 🎯 PRÓXIMAS MEJORAS

1. **IA Auto-trading**
   - LSTM entrenado con resultados genéticos
   - Señales de entrada/salida automáticas
   - Gestión de riesgo adaptativa

2. **Dashboard Predictivo**
   - Proyección de PnL
   - Alertas de rendimiento
   - Optimización de parámetros

3. **Múltiples estrategias**
   - Grid trading
   - Momentum
   - Mean reversion
   - Breakout

---

**Sistema listo para ejecución autónoma.**
**Meta: Doblar cuenta mensualmente (+5% diario)**
