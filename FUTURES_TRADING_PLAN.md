# Coinbase Futures Trading - Plan de Implementación

## Resumen

Sistema completo de trading de futuros en Coinbase con flujo:
```
Mining (estrategias) → Paper Trading (validación) → Live Trading (ejecución real)
```

---

## Fase 3A: Infraestructura de Futuros ✅ IMPLEMENTADO

### Objetivo
Backtesting y paper trading para futuros con soporte de:
- Long y Short positions
- Leverage 1x-10x
- Funding rates (perpetuos)
- Liquidaciones automáticas

### Archivos Implementados

| Archivo | Propósito | Líneas |
|---------|-----------|--------|
| `numba_futures_backtester.py` | Backtester JIT para futuros con Numba | ~1045 |
| `paper_futures_trader.py` | Paper trading en tiempo real via WebSocket | ~800 |

### Características

**numba_futures_backtester.py:**
- Evaluación de poblaciones de genomes futures
- Pre-computación de 24 indicadores (RSI, SMA, EMA, VOLSMA x 6 períodos)
- Simulación de liquidaciones
- Funding rates horarios para perpetuos
- Safety limits para prevenir valores absurdos

**paper_futures_trader.py:**
- Conexión a Coinbase WebSocket (`wss://ws-feed.exchange.coinbase.com`)
- Evaluación de señales en tiempo real
- Gestión de posiciones Long/Short
- Trailing stops automáticos
- Registro de trades en SQLite

### Uso
```bash
# Paper trading standalone
python paper_futures_trader.py --contract BIT-27FEB26-CDE --capital 10000 --leverage 5 --direction BOTH

# Backtest de población
from numba_futures_backtester import numba_evaluate_futures_population
results = numba_evaluate_futures_population(df, population, is_perpetual=True)
```

---

## Fase 3B: Gestión de Riesgo y Ejecución ✅ IMPLEMENTADO

### Objetivo
Protección de capital y ejecución de órdenes reales con Coinbase API.

### Archivos Implementados

| Archivo | Propósito | Líneas |
|---------|-----------|--------|
| `risk_manager_live.py` | Sistema de gestión de riesgo | ~770 |
| `live_futures_executor.py` | Ejecutor de órdenes reales | ~910 |

### Características

**risk_manager_live.py:**
- Límites de pérdida: 3% diario, 7% semanal, 15% mensual
- Circuit breakers por volatilidad (5% en 5min)
- Máximo 5 posiciones simultáneas
- Leverage máximo 5x
- Cooldown de 30min después de pérdida grande
- Cooldown de 2h después de liquidación
- Tracking de trades en SQLite

**live_futures_executor.py:**
- Autenticación JWT Ed25519 con Coinbase
- Envío de órdenes market/limit
- Gestión de posiciones en tiempo real
- Cálculo de precios de liquidación
- WebSocket para datos en vivo
- Modo `dry_run=True` para pruebas

### Uso
```python
from live_futures_executor import LiveFuturesExecutor, PositionSide
from risk_manager_live import RiskManager, RiskConfig

# Inicializar
executor = LiveFuturesExecutor(dry_run=True)  # dry_run para pruebas
risk_manager = RiskManager(initial_balance=10000)

# Verificar si podemos abrir posición
can_open, reason = risk_manager.can_open_position(
    product_id="BIP-20DEC30-CDE",
    side="LONG",
    leverage=5,
    margin_usd=500,
    current_positions=executor.positions
)

if can_open:
    result = executor.open_position(
        product_id="BIP-20DEC30-CDE",
        side=PositionSide.LONG,
        leverage=5,
        margin_usd=500
    )
```

---

## Fase 3C: Orquestación ✅ IMPLEMENTADO

### Objetivo
Coordinar todo el flujo: mining → validación → activación → monitoreo.

### Archivo Implementado

| Archivo | Propósito | Líneas |
|---------|-----------|--------|
| `futures_orchestrator.py` | Orquestador principal del sistema | ~724 |

### Características

**futures_orchestrator.py:**
- Coordina Strategy Miner, Paper Trading, Live Trading, Risk Manager
- Flujo de estados: MINING → BACKTESTED → PAPER_TESTING → VALIDATED → ACTIVE
- Criterios de activación configurables:
  - Mínimo 20 trades
  - Win rate >= 45%
  - Sharpe >= 1.0
  - Max drawdown <= 25%
  - Máximo 3 liquidaciones
- Monitoreo continuo de posiciones
- Desactivación automática por degradación
- Notificaciones Telegram (placeholder)

### Uso
```bash
# CLI
python futures_orchestrator.py --mine --product BIP-20DEC30-CDE
python futures_orchestrator.py --start --dry-run --balance 10000
python futures_orchestrator.py --status
```

---

## Cambios en Archivos Existentes

### coordinator_port5001.py (+117 líneas)
- Soporte para work units de futuros
- Nuevos endpoints para futures

### crypto_worker.py (+36 líneas)
- Soporte para backtesting de futuros
- Detección de tipo de mercado (spot vs futures)

### interface.py (+68 líneas)
- (Ver detalles en diff)

### strategy_miner.py (+112 líneas)
- Soporte para parámetros de futuros (leverage, direction)
- Market type detection
- Integración con numba_futures_backtester

---

## Pendiente (Próximos Pasos)

### Integración con Dashboard ✅ HECHO (Feb 2026)
- [x] Nuevo tab "Futures" en interface.py
- [x] Visualización de posiciones en tiempo real
- [x] Controles para paper/live trading
- [x] Selector de productos perpetual vs dated

### API Endpoints ✅ HECHO (Feb 2026)
- [x] GET /api/futures/products - Lista productos futures
- [x] POST /api/futures/create_work_unit - Crear work unit de futures
- [x] GET /api/futures/status - Status del sistema de futures

### Extensión del Sistema Distribuido (PENDIENTE)
- [ ] Workers con soporte de futures
- [ ] Work units específicas para futuros
- [ ] Cola de productos futures

### Datos ✅ EXISTE (44 archivos)
- [x] Datos OHLCV de contratos futures (data_futures/)
- [ ] Data manager para futures (actualizar data_manager.py)
- [ ] Feed en tiempo real (WebSocket)

### Tests (PENDIENTE)
- [ ] Unit tests para futures backtester
- [ ] Integration tests para orchestrator
- [ ] Validación end-to-end

---

## Productos Soportados

### Perpetuos (Alta liquidez)
| Código | Producto | Contract Size |
|--------|----------|---------------|
| BIP-20DEC30-CDE | Bitcoin Perpetual | 0.01 BTC |
| ETP-20DEC30-CDE | Ethereum Perpetual | 0.10 ETH |
| SLP-20DEC30-CDE | Solana Perpetual | 5 SOL |
| XPP-20DEC30-CDE | XRP Perpetual | 500 XRP |

### Dated (Con vencimiento)
| Código | Producto | Vencimiento |
|--------|----------|-------------|
| BIT-27FEB26-CDE | Nano Bitcoin | Feb 2026 |
| BIT-27MAR26-CDE | Nano Bitcoin | Mar 2026 |
| ET-27FEB26-CDE | Nano Ethereum | Feb 2026 |

---

## Seguridad

### Modo Dry Run
Todos los componentes tienen modo `dry_run=True` para pruebas sin riesgo:

```python
# Executor
executor = LiveFuturesExecutor(dry_run=True)

# Orchestrator
orchestrator = FuturesOrchestrator(dry_run=True, auto_activate=False)
```

### Safety Limits en Backtester
```python
MAX_BALANCE = 1_000_000.0
MAX_POSITION_VALUE = 100_000.0
MAX_PNL = 1_000_000.0
```

---

**Fecha de implementación:** Febrero 2026
**Autor:** Strategy Miner Team
