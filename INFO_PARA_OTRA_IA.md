# 🤖 Coinbase Cripto Trader Claude - Info para IA

## 📦 CLONAR EL REPOSITORIO

```bash
git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git
cd Coinbase-Cripto-Trader-Claude
```

## 📦 INSTALAR DEPENDENCIAS

```bash
pip install -r requirements.txt
```

## ⚙️ CONFIGURAR VARIABLES DE ENTORNO

Crear archivo `.env` con las API keys de Coinbase:

```env
COINBASE_API_KEY=tu_api_key
COINBASE_API_SECRET=tu_api_secret
COINBASE_API_PASSPHRASE=tu_passphrase
```

---

## 🏗️ ESTRUCTURA DEL PROYECTO

### Archivos Principales (Core Trading)

| Archivo | Descripción |
|---------|-------------|
| `coordinator.py` | Servidor central que distribuye trabajo a workers |
| `crypto_worker.py` | Worker que ejecuta trades y backtests |
| `strategy_miner.py` | Busca y evalúa estrategias de trading |
| `optimizer.py` | Optimización Bayesiana de parámetros |
| `strategy.py` | Clase base de estrategias |
| `trading_bot.py` | Bot principal de trading |

### Estrategias de Trading

| Archivo | Descripción |
|---------|-------------|
| `dynamic_strategy.py` | Estrategia adaptativa al régimen de mercado |
| `strategy_grid.py` | Trading en grid (compra/venta en niveles) |
| `strategy_momentum.py` | Sigue tendencias alcistas |
| `penny_basket_strategy.py` | Diversificación en criptomonedas pequeñas |
| `btc_spot_strategy.py` | Estrategia específica para BTC spot |

### Clientes y APIs

| Archivo | Descripción |
|---------|-------------|
| `coinbase_client.py` | Cliente para API de Coinbase |
| `broker_client.py` | Cliente genérico de broker |
| `schwab_client.py` | Cliente para Schwab (opcional) |

### Interfaz y Visualización

| Archivo | Descripción |
|---------|-------------|
| `interface.py` | Interfaz web principal (Streamlit) |
| `workers_tab_improved.py` | Pestaña de workers mejorada |

### Scripts de Inicio y Setup

| Script | Descripción |
|--------|-------------|
| `auto_setup_worker.sh` | Instalación automática de worker |
| `setup_worker.sh` | Setup manual de worker |
| `start_worker.sh` | Iniciar worker |
| `start_head.sh` | Iniciar nodo head (coordinator) |
| `start_ray_head.sh` | Iniciar Ray cluster head |
| `start_ray_fixed.sh` | Iniciar Ray con fixes |
| `start_cluster_head.py` | Iniciar cluster via Python |

### Runners (Ejecutar el sistema)

| Script | Descripción |
|--------|-------------|
| `run_miner_full.py` | Ejecutar miner con todas las estrategias |
| `run_local_stable.py` | Ejecutar versión local estable |
| `run_final_stable.py` | Ejecutar versión final estable |
| `run_optimized_miner.py` | Ejecutar miner optimizado |

### Monitoreo y Diagnóstico

| Script | Descripción |
|--------|-------------|
| `monitor_cpu.sh` | Monitorear uso de CPU |
| `monitor_miner.sh` | Monitorear miner |
| `monitor_progress.sh` | Monitorear progreso |
| `check_cluster.py` | Verificar estado del cluster |
| `check_ray_status.py` | Verificar estado de Ray |
| `check_ray_stability.py` | Verificar estabilidad de Ray |
| `validate_cluster.py` | Validar cluster |
| `auto_repair_cluster.py` | Reparar cluster automáticamente |

### Backtesting y Análisis

| Archivo | Descripción |
|---------|-------------|
| `backtester.py` | Sistema de backtesting |
| `backtest_runner.py` | Runner para backtests |
| `numba_backtester.py` | Backtesting optimizado con Numba |
| `data_manager.py` | Gestor de datos |
| `market_regime_detector.py` | Detectar régimen de mercado |
| `analyze_results.py` | Analizar resultados |
| `compare_results.py` | Comparar resultados |
| `scanner.py` | Escanear oportunidades |

### Utilidades

| Script | Descripción |
|--------|-------------|
| `install.sh` | Instalación principal |
| `install_wrapper.command` | Wrapper para Mac |
| `restart_system.sh` | Reiniciar sistema |
| `kill_all_force.sh` | Forzar cierre de procesos |
| `safe_launcher.py` | Lanzador seguro |
| `beacon.py` | Beacon del sistema |

---

## 🚀 USO BÁSICO

### Como Coordinator (Head Node):

```bash
# Iniciar coordinator
python coordinator.py

# O con scripts
./start_head.sh
./start_ray_head.sh
```

### Como Worker:

```bash
# Conectar a coordinator
python crypto_worker.py --coordinator http://IP_DEL_HEAD:5001

# O con scripts
./start_worker.sh
```

### Interfaz Web:

```bash
python interface.py
# O
streamlit run interface.py
```

---

## 📁 DIRECTORIOS

| Directorio | Contenido |
|------------|-----------|
| `Documentation/` | Documentación del proyecto |
| `data/` | Datos de trading (no subido a Git) |
| `static/` | Archivos estáticos para interfaz |
| `static_payloads/` | Payloads estáticos para workers |

---

## ⚠️ NOTAS IMPORTANTES

1. **API Keys**: Crear `.env` con credenciales de Coinbase
2. **No subir**: `.env`, logs, backups, checkpoints de workers
3. **Ray Cluster**: Sistema distribuido con múltiples nodos
4. **Documentación**: Ver `START_HERE.md` e `INSTRUCCIONES_USUARIO.md`

---

## 🔗 REPOSITORIO

https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude

---

Creado: 2026-02-10
