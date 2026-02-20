# 🚀 Sistema Híbrido de Trading Implementado

## Resumen Ejecutivo

Se ha implementado un sistema de trading algorítmico de **doble estrategia** basado en la investigación sobre scalping en criptomonedas. El sistema detecta automáticamente las condiciones del mercado y selecciona la estrategia óptima.

---

## 📊 Arquitectura del Sistema

### 1. **Market Regime Detector** (`market_regime_detector.py`)

Detecta si el mercado está en condiciones:

#### **RANGING (Lateral)**
- ADX < 25 (tendencia débil)
- Volatilidad baja
- Rango de precio estrecho
- **→ Activa: Grid Trading**

#### **TRENDING (Tendencial)**
- ADX > 25 (tendencia fuerte)
- Volatilidad alta
- Movimiento direccional claro
- **→ Activa: Momentum Scalping**

**Indicadores utilizados:**
- `ADX (Average Directional Index)` - Fuerza de tendencia
- `ATR/Precio` - Volatilidad relativa
- `High-Low Range %` - Amplitud del rango

---

### 2. **Grid Trading Strategy** (`strategy_grid.py`)

**Para mercados LATERALES/CONSOLIDACIÓN**

#### Mecánica:
- Coloca niveles de compra/venta en una malla geométrica
- Espaciado: **>1.2%** (supera comisiones Maker 0.80%)
- Compra cuando el precio baja a un nivel
- Vende cuando el precio sube a un nivel

#### Ventajas:
✅ **No predice dirección** - Captura volatilidad local
✅ **Órdenes límite (Maker)** - Comisiones 0.40% vs 0.60%
✅ **Múltiples operaciones** - Gana en cada oscilación
✅ **Rebalanceo dinámico** - Sigue al precio si sale del rango

#### Parámetros Optimizables:
- `grid_spacing_pct`: Espaciado entre niveles (default: 1.2%)
- `num_grids`: Cantidad de niveles (default: 10)
- `grid_range_pct`: Rango total de la malla (default: 10%)
- `rebalance_threshold`: Cuándo recentrar la malla (default: 5%)

---

### 3. **Momentum Scalping Strategy** (`strategy_momentum.py`)

**Para mercados TENDENCIALES**

#### Confirmación Multi-Indicador:

**Señal LONG requiere:**
1. ✅ SMA(5) cruza por encima de SMA(12)
2. ✅ Precio > VWAP (filtro institucional)
3. ✅ RSI(4) < 80 (no sobrecomprado)
4. ✅ Bollinger Bands: Squeeze o breakout alcista

**Señal SHORT requiere:**
1. ✅ SMA(5) cruza por debajo de SMA(12)
2. ✅ Precio < VWAP
3. ✅ RSI(4) > 20 (no sobrevendido)
4. ✅ Bollinger Bands: Squeeze o breakout bajista

#### Indicadores de Alta Precisión:
- `SMA(5/12)` - Cruces rápidos para timing
- `VWAP` - Precio institucional de referencia
- `RSI(4)` - Detección de agotamiento inmediato
- `Bollinger Bands (20,2)` - Identificación de breakouts

#### Ventajas:
✅ **Sigue la tendencia** - Opera a favor del momentum
✅ **Confirmación múltiple** - Reduce señales falsas (>2/3 confirmaciones)
✅ **Take Profit dinámico** - Basado en ATR y movimiento mínimo >1.5%
✅ **Stop Loss conservador** - 1.5x ATR para proteger capital

---

## 🎯 Strategy Orchestrator (strategy.py)

**El cerebro del sistema**

### Flujo de Decisión:

```
1. Analizar datos históricos
2. ↓
3. Detectar régimen de mercado (MarketRegimeDetector)
4. ↓
5. ¿RANGING o TRENDING?
6. ↓
7. RANGING          TRENDING
8.    ↓                ↓
9. Grid Trading   Momentum Scalping
10. ↓                ↓
11. Generar señal con parámetros de riesgo
12. ↓
13. Calcular SL/TP basado en ATR
14. ↓
15. Ajustar según risk_level (LOW/MEDIUM/HIGH)
16. ↓
17. Return: {signal, regime, strategy, sl, tp, confidence}
```

---

## 💰 Gestión de Riesgo Integrada

### Position Sizing Dinámico:
```
Position Size = (Balance * Risk%) / (Entry - StopLoss)
```

- Default: **2% del capital por trade**
- Máximo: **20% del capital en una posición**
- Protege contra ruina por drawdowns consecutivos

### Stop Loss / Take Profit:
- **SL**: 1.5x ATR (conservador)
- **TP**: 3.0x ATR (ratio 2:1 mínimo)
- Ajustes automáticos según risk_level:
  - **LOW**: SL más cerca, TP más conservador
  - **MEDIUM**: Balance
  - **HIGH**: SL más lejos, TP más agresivo

---

## 🔧 Parámetros Optimizables del Sistema

### Market Regime Detection:
- `adx_period`: 14
- `adx_threshold`: 25
- `volatility_window`: 20

### Grid Trading:
- `grid_spacing_pct`: 1.2%
- `num_grids`: 10
- `grid_range_pct`: 10.0%
- `rebalance_threshold`: 5.0%

### Momentum Scalping:
- `sma_fast`: 5
- `sma_slow`: 12
- `rsi_period`: 4
- `rsi_overbought`: 80
- `rsi_oversold`: 20
- `bb_period`: 20
- `bb_std`: 2.0
- `min_move_pct`: 1.5%

### Risk Management:
- `risk_per_trade_pct`: 2.0%
- `max_position_size_pct`: 20.0%
- `sl_multiplier`: 1.5
- `tp_multiplier`: 3.0

---

## 📈 Ventajas Sobre la Estrategia Anterior

| Aspecto | Estrategia Vieja | Nueva Estrategia |
|---------|------------------|------------------|
| **Tipo de órdenes** | Market (Taker 0.60%) | Limit (Maker 0.40%) |
| **Costo ida/vuelta** | 1.20% | 0.80% |
| **Adaptabilidad** | Una sola estrategia | Dual (Grid + Momentum) |
| **Detección de mercado** | Solo tendencia 1H | Régimen dinámico ADX |
| **Indicadores** | Breakout + RSI | 6+ indicadores confirmatorios |
| **Gestión de riesgo** | Fija | Dinámica (ATR-based) |
| **Movimiento mínimo** | No definido | >1.5% para rentabilidad |

---

## 🧪 Testing Recomendado

### Fase 1: Backtesting
1. Descargar datos de 30 días (5min candles)
2. Ejecutar backtest con parámetros default
3. **Métricas objetivo:**
   - Win Rate: >45%
   - Total PnL: >0 (rentable)
   - Trades: >50 (suficiente actividad)
   - ROI: >5%

### Fase 2: Optimización
**Parámetros clave a optimizar:**
- `grid_spacing_pct` (1.0% - 2.0%)
- `sma_fast/slow` (3-7 / 10-15)
- `rsi_period` (3-7)
- `min_move_pct` (1.2% - 2.0%)

### Fase 3: Forward Testing
- Paper trading en vivo
- Monitorear cambios de régimen
- Validar que las estrategias se activen correctamente

---

## 📊 Métricas de Rendimiento Esperadas

### Grid Trading (Mercados Laterales):
- **Trades/día**: 10-30
- **Win Rate**: 60-70% (muchas pequeñas ganancias)
- **Avg Trade**: 0.5-1.5% (después de comisiones)

### Momentum Scalping (Mercados Tendenciales):
- **Trades/día**: 5-15
- **Win Rate**: 40-55% (ratio R:R favorece)
- **Avg Win**: 2-4%
- **Avg Loss**: 1-1.5%

---

## 🚀 Próximos Pasos

1. ✅ **Implementación completada**
2. ⏳ **Probar backtest con nuevas estrategias**
3. ⏳ **Optimizar parámetros para BTC/ETH**
4. ⏳ **Validar en diferentes condiciones de mercado**
5. ⏳ **Calibrar para volumen suficiente (alcanzar tiers menores de comisión)**

---

## 📝 Notas Importantes

⚠️ **CRÍTICO**: El sistema está diseñado para **órdenes MAKER** (límite). En trading en vivo, asegurar que se use la bandera `post_only=True` en Coinbase Advanced Trade.

⚠️ **Comisiones**: Los parámetros están calibrados para:
- Tier inicial: Maker 0.40%, Taker 0.60%
- A medida que aumenta el volumen, las estrategias se vuelven MÁS rentables

⚠️ **Backtesting vs Live**: El backtest asume fills perfectos en precios límite. En vivo, puede haber slippage y órdenes no ejecutadas.

---

## 🎓 Referencias de la Investigación

Basado en:
- Market Making con lógica Post-Only
- Grid Trading geométrico para cripto
- Scalping de Momentum con confirmación multi-indicador
- Gestión de riesgo de position sizing (2% rule)
- Análisis de microestructura de mercado de Coinbase

**Fuente**: "Arquitectura de Trading Algorítmico de Alta Frecuencia en Mercados de Criptoactivos"
