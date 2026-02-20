# 🚀 SISTEMA COMPLETO DE TRADING AUTOMATIZADO v1.0

## 📋 Resumen del Sistema

Este es un **sistema completo de trading automatizado** que incluye:

1. 📥 **Descarga de datos** de 30+ activos en 5 timeframes
2. 🧬 **Algoritmo genético** para encontrar estrategias
3. 🧠 **IA entrenada** con los resultados
4. 📈 **Trading automático** con gestión de riesgo
5. 📊 **Dashboard unificado** para monitoreo

## 💰 Configuración

| Parámetro | Valor |
|-----------|-------|
| Capital Inicial | $500 |
| Objetivo Diario | 5% |
| Stop Loss | 5% |
| Take Profit | 10% |
| Risk por Trade | 2% |
| Timeframes | 1m, 5m, 15m, 30m, 1h |
| Activos | Top 30 por liquidez |

## 📁 Archivos del Sistema

### Scripts Principales

| Archivo | Descripción |
|---------|-------------|
| `start_trading_system.command` | 🚀 **INICIO RÁPIDO** - Menú interactivo |
| `master_trading_system.py` | Sistema maestro de trading |
| `download_multi_data.py` | Descarga datos de Coinbase |
| `generate_optimized_wus.py` | Genera Work Units optimizados |
| `ia_trading_agent.py` | Agente de IA para trading |
| `unified_dashboard.py` | Dashboard unificado (Streamlit) |
| `master_orchestrator.py` | Orquestador del sistema |

### Dashboards

| Dashboard | Puerto | Descripción |
|-----------|--------|-------------|
| Admin Panel | 5007 | Panel de administración rápido |
| F1 Dashboard | 5006 | Diseño F1 Racing |
| Streamlit | 8500 | Interfaz principal |
| Coordinator | 5001 | API del coordinator |

## 🎯 Cómo Usar

### Opción 1: Inicio Rápido (Recomendado)

```bash
cd "/Users/enderj/.../Coinbase Cripto Trader Claude"
bash start_trading_system.command
```

Selecciona la opción **1** para ejecutar todo el sistema.

### Opción 2: Manual

```bash
# 1. Descargar datos
python3 download_multi_data.py

# 2. Generar Work Units
python3 generate_optimized_wus.py

# 3. Entrenar IA
python3 ia_trading_agent.py --train

# 4. Trading automático
python3 ia_trading_agent.py --trade
```

### Opción 3: Modo Autónomo

```bash
python3 master_orchestrator.py --mode full
```

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────┐
│              MASTER ORCHESTRATOR                      │
│                  (master_orchestrator.py)              │
└───────────────────────┬─────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌────────┐    ┌────────┐    ┌────────┐
   │ Datos │    │ Work   │    │   IA   │
   │(30+TF)│    │ Units  │    │Trading │
   └────────┘    └────────┘    └────────┘
```

## 📊 Dashboards Disponibles

1. **Admin Panel**: http://localhost:5007
   - Ver estado del sistema
   - Ejecutar comandos
   - Monitoreo de workers

2. **F1 Dashboard**: http://localhost:5006
   - Diseño de carreras F1
   - Métricas en tiempo real
   - Contribución de workers

3. **Streamlit**: http://localhost:8501
   - Interfaz completa
   - Gráficos interactivos
   - Control de parámetros

4. **Coordinator**: http://localhost:5001
   - API REST
   - Estado del cluster
   - Workers conectados

## 🧬 Algoritmo Genético

El sistema usa un algoritmo genético que:

1. **Genera poblaciones** de estrategias aleatorias
2. **Evalúa** cada estrategia con backtesting
3. **Selecciona** las mejores (top 20%)
4. **Cruza** y **Muta** para crear nuevas estrategias
5. **Repite** por 100 generaciones

### Parámetros Genéticos

| Parámetro | Valor |
|-----------|-------|
| Population Size | 100 |
| Generations | 100 |
| Mutation Rate | 15% |
| Crossover Rate | 80% |
| Elite Rate | 10% |

## 🧠 IA de Trading

El agente de IA aprende de los resultados del algoritmo genético y:

1. **Analiza** patrones de entrada/salida
2. **Predice** señales de trading
3. **Gestiona** riesgo automáticamente
4. **Ejecuta** trades con gestión de posición

## 📈 Métricas de Rendimiento

| Métrica | Objetivo |
|----------|----------|
| Win Rate | >60% |
| Profit Factor | >1.5 |
| Sharpe Ratio | >1.0 |
| Max Drawdown | <10% |
| PnL Mensual | +100% |

## ⚠️ Disclaimer

**RIESGO**: El trading de criptomonedas implica riesgo de pérdida. Este sistema es para fines educativos. No invertir más de lo que puedas permitirte perder.

## 📝 Licencia

Uso educativo y de investigación.

---

**Fecha de creación:** 2026-02-10
**Versión:** 1.0
**Autor:** AI Trading Team
