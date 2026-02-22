# 🚀 Coinbase Advanced Trade - Módulo de Futuros

## Resumen

Este módulo permite operar futuros en Coinbase Advanced Trade con:
- ✅ **Apalancamiento** hasta 10x
- ✅ **Short Selling** (venta en corto)
- ✅ **Contratos Nano** (menor capital requerido)
- ✅ **Acceso a materias primas** (oro, petróleo, gas)

---

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `coinbase_advanced_trader.py` | Cliente principal de trading |
| `futures_dashboard.py` | Dashboard CLI para operaciones |
| `coinbase_futures_client.py` | Cliente legacy (v1) |

---

## Uso Básico

### Inicializar el cliente

```python
from coinbase_advanced_trader import CoinbaseAdvancedTrader

# Production
trader = CoinbaseAdvancedTrader(sandbox=False)

# Sandbox (pruebas)
trader = CoinbaseAdvancedTrader(sandbox=True)
```

### Consultar precios

```python
# Precio de contrato específico
ticker = trader.get_ticker("BIT-27FEB26-CDE")
print(ticker["trades"][0]["price"])  # $67690

# Mejor bid/ask
bid_ask = trader.get_best_bid_ask(["BTC-USD", "BIT-27FEB26-CDE"])

# Lista de contratos
contracts = trader.get_futures_contracts("BTC")
```

### Consultar cuenta

```python
# Balance de futuros
balance = trader.get_balance()
print(balance["balance_summary"]["available_balance"])

# Posiciones
positions = trader.get_positions()

# Resumen
summary = trader.get_position_summary()
print(f"PnL total: ${summary['total_pnl']}")
```

### Abrir posición

```python
# Largo (compra) con apalancamiento
trader.open_position(
    product_id="BIT-27FEB26-CDE",
    position_side="long",    # "long" o "short"
    size=1,                   # contratos
    leverage=5,              # 1-10x
    order_type="market"      # "market" o "limit"
)

# Corto (venta)
trader.open_position(
    product_id="ET-27FEB26-CDE",
    position_side="short",
    size=2,
    leverage=3
)
```

### Cerrar posición

```python
# Cerrar todo
trader.close_position("BIT-27FEB26-CDE")

# Cerrar parcial
trader.close_position("BIT-27FEB26-CDE", size=1)
```

---

## Dashboard CLI

### Ver resumen de cuenta

```bash
python futures_dashboard.py
```

### Ver precio de contrato

```bash
python futures_dashboard.py --price BIT-27FEB26-CDE
```

### Listar contratos

```bash
# Todos
python futures_dashboard.py --contracts

# Solo Bitcoin
python futures_dashboard.py --contracts --asset BIT

# Solo Ethereum
python futures_dashboard.py --contracts --asset ET
```

### Ver balance

```bash
python futures_dashboard.py --balance
```

### Ver posiciones

```bash
python futures_dashboard.py --positions
```

### Abrir posición

```bash
# Largo 1 contrato BIT con 5x leverage
python futures_dashboard.py --open LONG 1 BIT-27FEB26-CDE 5

# Corto 2 contratos ET con 3x leverage
python futures_dashboard.py --open SHORT 2 ET-27FEB26-CDE 3
```

### Cerrar posición

```bash
python futures_dashboard.py --close BIT-27FEB26-CDE
```

---

## Contratos Disponibles

### Bitcoin
| Símbolo | Contrato | Precio |
|---------|----------|--------|
| BIT | BIT-27FEB26-CDE | ~$67,690 |
| BIT | BIT-27MAR26-CDE | ~$68,170 |
| BIP | BIP-20DEC30-CDE | ~$67,630 (perpetuo) |

### Ethereum
| Símbolo | Contrato | Precio |
|---------|----------|--------|
| ET | ET-27FEB26-CDE | ~$1,958 |
| ETP | ETP-20DEC30-CDE | ~$1,958.5 (perpetuo) |

### Solana
| Símbolo | Contrato | Precio |
|---------|----------|--------|
| SOL | SOL-27FEB26-CDE | ~$84.45 |
| SLP | SLP-20DEC30-CDE | ~$84.26 (perpetuo) |

### Materias Primas
| Activo | Contrato | Precio |
|--------|----------|--------|
| Oro | GOL-27MAR26-CDE | ~$5,130 |
| WTI | NOL-19MAR26-CDE | - |
| Gas | NGS-24FEB26-CDE | - |

---

## Apalancamiento

| Leverage | Margin Requerido | Riesgo |
|----------|------------------|--------|
| 1x | 100% | Bajo |
| 2x | 50% | Medio |
| 5x | 20% | Alto |
| 10x | 10% | Muy Alto |

**⚠️ Advertencia**: El apalancamiento aumenta tanto ganancias como pérdidas.

---

## Short Selling

Para operar en corto (bear):

```python
# Vender (short)
trader.open_position(
    product_id="BIT-27FEB26-CDE",
    position_side="short",
    size=1,
    leverage=5
)

# Cerrar = comprar para cubrir
trader.close_position("BIT-27FEB26-CDE")
```

### Cash and Carry

1. Comprar spot (BTC)
2. Vender futuro (BIT-XXX-CDE)
3. Al vencimiento: recibir diferencia

---

## Gestión de Margen

### Ratio de Margen

```
Margin Ratio = Available Balance / Required Margin
```

- **> 1.5**: Saludable
- **1.0 - 1.5**: Advertencia
- **< 1.0**: Riesgo de liquidación

### Ventanas de Margen

| Ventana | Horario (ET) | Requisitos |
|---------|--------------|-------------|
| Intraday | 8:00 AM - 4:00 PM | Menor |
| Overnight | 4:00 PM + | Mayor |

---

## Autenticación

El cliente usa **JWT con Ed25519**:

1. Carga credenciales desde `/Users/enderj/Downloads/cdp_api_key.json`
2. Genera token JWT que expira en 120 segundos
3. Firma con clave privada Ed25519

### Archivo de credenciales

```json
{
  "id": "f2b19384-cbfd-4e6b-ab21-38a29f53650b",
  "privateKey": "8eT+gzVAvHVr..."
}
```

---

## Dependencias

```bash
pip install cryptography requests
```

Activar venv:
```bash
source ~/coinbase_trader_venv/bin/activate
```

---

## Estado de la Cuenta

- **BTC Wallet**: 0.012496 BTC
- **SOL Wallet**: 0.102893 SOL  
- **USDC Wallet**: $15.02
- **CFM Balance**: Sin fondos ($0)
- **Posiciones**: Ninguna abierta

---

## Próximos Pasos

1. ✅ Cliente básico implementado
2. ✅ Dashboard CLI implementado
3. ⏳ Integrar con el sistema de estrategias
4. ⏳ Sistema de trading automático
5. ⏳ Gestión de riesgos (stop-loss, take-profit)

---

*Última actualización: 2026-02-21*
