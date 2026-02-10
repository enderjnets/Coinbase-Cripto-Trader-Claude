# 🤖 Coinbase Cripto Trader Claude

Sistema de trading algorítmico distribuido para Coinbase con optimización automática de estrategias.

## 📊 Características

- **Trading Automatizado**: Estrategias dinámicas para criptomonedas en Coinbase
- **Sistema Distribuido**: Arquitectura Ray para parallelización en múltiples workers
- **Optimización Bayesiana**: Encuentra los mejores parámetros automáticamente
- **Interfaz Web**: Monitoreo y control vía Streamlit

## 🚀 Inicio Rápido

```bash
# Clonar el repositorio
git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git
cd Coinbase-Cripto-Trader-Claude

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.template .env
# Edita .env con tus API keys de Coinbase

# Iniciar el coordinator
python coordinator.py

# En workers separados:
python crypto_worker.py --coordinator http://TU_IP:5001
```

## 📁 Estructura del Proyecto

```
├── coordinator.py          # Servidor central que distribuye trabajo
├── crypto_worker.py        # Worker que ejecuta trades
├── strategy_miner.py       # Busca y evalúa estrategias
├── optimizer.py            # Optimización Bayesiana
├── interface.py            # Interfaz web Streamlit
├── strategies/             # Módulos de estrategias de trading
│   ├── dynamic_strategy.py
│   ├── strategy_grid.py
│   └── strategy_momentum.py
└── requirements.txt        # Dependencias Python
```

## 🔧 Configuración

### Variables de Entorno (.env)

```env
COINBASE_API_KEY=tu_api_key
COINBASE_API_SECRET=tu_api_secret
COINBASE_API_PASSPHRASE=tu_passphrase
```

## 📈 Estrategias Disponibles

- **Dynamic Strategy**: Adaptación automática al régimen de mercado
- **Grid Trading**: Compra/venta en niveles predefinidos
- **Momentum**: Sigue tendencias alcistas
- **Penny Basket**: Diversificación en criptomonedas pequeñas

## 🖥️ Workers

El sistema puede ejecutarse en múltiples máquinas:

```bash
# MacBook Pro
python crypto_worker.py --coordinator http://IP_PRO:5001 --name "MacBook Pro"

# MacBook Air
python crypto_worker.py --coordinator http://IP_AIR:5001 --name "MacBook Air"

# VPS/Server
python crypto_worker.py --coordinator http://TU_VPS:5001 --name "VPS"
```

## 📜 Licencia

MIT License - Uso bajo tu propio riesgo. Trading de criptomonedas conlleva riesgos.

## ⚠️ Disclaimer

ESTE SOFTWARE ES PARA FINES EDUCATIVOS. NO GARANTIZA GANANCIAS. 
Opera con dinero real bajo tu propio riesgo.
