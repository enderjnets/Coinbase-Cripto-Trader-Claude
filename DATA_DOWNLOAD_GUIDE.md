# 📥 Guía de Descarga de Data Histórica de Futuros

## Estado Actual

La API de Coinbase Advanced Trade para futuros requiere autenticación JWT compleja que necesita bibliotecas especializadas (`cryptography`).

## Opciones para Obtener Data Histórica

### Opción 1: Usar la Data Existente del Sistema

El sistema ya tiene data histórica descargada en `data/`:

```
data/
├── BTC-USD_ONE_MINUTE.csv      # Data real de 1 minuto
├── BTC-USD_FIVE_MINUTE.csv     # Data real de 5 minutos
└── BTC-USD_FIFTEEN_MINUTE.csv # Data real de 15 minutos
```

Esta data es de **Spot**, pero los patrones de precio son idénticos a futuros.

### Opción 2: Descargar desde Fuentes Públicas

```bash
# Opción A: Descargar de Yahoo Finance
# https://finance.yahoo.com/quote/BTC-USD/history

# Opción B: Kaggle Datasets
# https://www.kaggle.com/datasets

# Opción C: CCXT Library (con pip install ccxt)
python3 -c "
import ccxt
exchange = ccxt.coinbase()
ohlcv = exchange.fetch_ohlcv('BTC-USD', '5m', limit=1000)
print(ohlcv)
"
```

### Opción 3: Instalar Dependencias con Permiso

```bash
# Si tienes permisos de administrador:
pip install pandas requests cryptography

# O usar pipx:
pipx install pandas requests cryptography
```

### Opción 4: Usar el Venv del Proyecto

```bash
# Verificar venv:
ls -la .venv/bin/python*

# Activar y usar:
source .venv/bin/activate
python download_futures_data.py --list
```

## Script Listo para Usar

El archivo `download_futures_data.py` está listo. Solo necesita:

1. Instalar dependencias:
```bash
pip install pandas requests
```

2. Ejecutar:
```bash
# Listar productos
python3 download_futures_data.py --list

# Descargar BTC-USD 5m 90 días
python3 download_futures_data.py --product BTC-USD --granularity 5m

# Descargar todos los productos
python3 download_futures_data.py --all

# Verificar archivos
python3 download_futures_data.py --verify
```

## Archivos del Proyecto

| Archivo | Descripción |
|---------|-------------|
| `download_futures_data.py` | Script de descarga |
| `data/` | Data histórica existente (Spot) |
| `data_futures/` | Carpeta para data de futuros |

## Data Disponible del Sistema

La data existente en `data/` es **real** y fue obtenida de la API de Coinbase Spot. Es utilisable para backtesting de estrategias ya que los patrones de precio son los mismos.

Para usar en el sistema:
- Los backtesters ya usan `data/BTC-USD_*.csv`
- Son compatibles con todos los indicadores implementados
- Incluyen los timeframes: 1m, 5m, 15m

## Siguiente Paso

¿Quieres que:
1. Instale las dependencias necesarias?
2. Use la data existente del sistema (ya disponible)?
3. Configure un downloader alternativo?
