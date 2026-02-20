# 🔐 Coinbase Futures API Client

Cliente Python para integrar la API de Futuros de Coinbase Advanced Trade con el sistema de trading distribuido.

## 📋 Características

- ✅ Autenticación JWT con Ed25519
- ✅ Gestión de posiciones CFM (US Derivatives)
- ✅ WebSockets para datos en tiempo real
- ✅ Gestión de márgenes y alertas
- ✅ Soporte para contratos Nano (BIT, ETP, SLP, XPP)
- ✅ Modo Sandbox para pruebas

## 🚀 Instalación

```bash
# Instalar dependencias
pip install requests websocket-client cryptography

# Opcional: Para ed25519 (puede requerir cryptography>=41.0.0)
pip install cryptography
```

## ⚙️ Configuración

### Variables de Entorno

```bash
# API Credentials (producción)
export COINBASE_API_KEY="tu_api_key_name"
export COINBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."

# Opcional: Modo sandbox
export COINBASE_SANDBOX="true"
```

### Generar Claves API

1. Ve a https://portal.coinbase.com/portal/api-keys
2. Crea una nueva API Key con permisos para:
   - `view`
   - `trade`
   - `wallet`
3. Copia la Private Key (incluye los `\n` para el formato PEM)

## 📖 Uso Básico

```python
from coinbase_futures_client import CoinbaseFuturesClient

# Cliente para producción
client = CoinbaseFuturesClient(
    api_key=API_KEY,
    private_key=PRIVATE_KEY,
    sandbox=False  # False = producción
)

# O para pruebas con sandbox
client = CoinbaseFuturesClient(
    api_key=API_KEY,
    private_key=PRIVATE_KEY,
    sandbox=True
)

# Verificar balance
balance = client.get_balance_summary()
print(balance)

# Obtener posiciones
positions = client.get_positions()
print(positions)

# Colocar orden
result = client.place_order(
    product_id="BIT-USD",  # Nano Bitcoin
    side="BUY",
    order_type="limit",
    size=5,  # 5 contratos (0.05 BTC)
    price=100000.00
)

# Verificar ratio de margen
margin_ratio = client.calculate_margin_ratio()
print(f"Margin Ratio: {margin_ratio:.2f}")
```

## 📊 Contratos Nano Disponibles

| Contrato | Símbolo | Tamaño | Tick | Valor Tick |
|----------|----------|--------|------|------------|
| Nano Bitcoin | BIT-USD | 0.01 BTC | $0.05 | $0.05 |
| Nano Ether | ETP-USD | 0.10 ETH | $0.50 | $0.05 |
| Nano Solana | SLP-USD | 5 SOL | $0.01 | $0.05 |
| Nano XRP | XPP-USD | 500 XRP | $0.0001 | $0.05 |

## 🌐 WebSocket para Datos en Tiempo Real

```python
from coinbase_futures_client import CoinbaseWebSocketClient

def on_balance_update(data):
    print(f"Balance actualizado: {data}")

def on_order_update(data):
    print(f"Estado de orden: {data}")

# Crear cliente WebSocket
ws_client = CoinbaseWebSocketClient(
    api_key=API_KEY,
    private_key=PRIVATE_KEY
)

# Registrar callbacks
ws_client.register_callback("futures_balance_summary", on_balance_update)
ws_client.register_callback("user", on_order_update)

# Conectar y suscribirse
ws_client.connect()
ws_client.subscribe("futures_balance_summary", ["BIT-USD", "ETP-USD"])

# ...tu lógica aquí...

# Cerrar conexión
ws_client.close()
```

## ⚠️ Gestión de Márgenes

### Verificar Ventana de Margen

```python
# Verificar si estamos en horario intradiario (más apalancamiento)
if client.is_margin_intraday():
    print("✅ Margen intradiario activo (8AM - 4PM ET)")
    print("   Puedes usar más apalancamiento")
else:
    print("⚠️ Margen nocturno activo (4PM ET en adelante)")
    print("   Requisitos de margen más altos")
```

### Calcular Ratio de Margen

```python
ratio = client.calculate_margin_ratio()

if ratio >= 1.5:
    print("✅ Salud de cuenta: Excelente")
elif ratio >= 1.2:
    print("⚡ Salud de cuenta: Buena")
elif ratio >= 1.0:
    print("⚠️ Salud de cuenta: Aceptable - Vigila tu margen")
else:
    print("🚨 ALERTA: Ratio de margen bajo - Riesgo de liquidación!")
```

## 🔄 Transferencias entre Cuentas

```python
# Transferir fondos de spot (CBI) a futuros (CFM)
client.schedule_sweep("IN", "10000")  # $10,000

# Transferir de futuros a spot
client.schedule_sweep("OUT", "5000")  # $5,000
```

## 📈 Integración con el Sistema de Trading

### Ejemplo: Hedging Automático

```python
class FuturesHedger:
    def __init__(self, client):
        self.client = client
    
    def hedge_long_position(self, btc_amount: float):
        """Crea posición corta en futuros para hedging"""
        # Convertir BTC a contratos Nano (0.01 BTC por contrato)
        contracts = int(btc_amount / 0.01)
        
        if contracts > 0:
            result = self.client.place_order(
                product_id="BIT-USD",
                side="SELL",
                order_type="market",
                size=contracts
            )
            return result
        return None
    
    def check_margin_health(self) -> str:
        """Verifica salud del margen y alerta si es necesario"""
        ratio = self.client.calculate_margin_ratio()
        
        if ratio < 1.1:
            return f"🚨 ALERTA: Margen crítico ({ratio:.2f})"
        elif ratio < 1.3:
            return f"⚠️ Advertencia: Margen bajo ({ratio:.2f})"
        else:
            return f"✅ Salud ok ({ratio:.2f})"
```

## 📚 Documentación Adicional

Ver `COINBASE_FUTURES_API_RESEARCH.md` para:
- Arquitectura institucional detallada
- Comparación futuros vs perpetuos
- Protocolos de autenticación
- Límites de API
- Estrategias de integración

## 🐛 Solución de Problemas

### Error de Autenticación
```
❌ Error: "Invalid JWT"
```
Solución: Verificar que la Private Key tenga los `\n` escapados correctamente.

### Error de Rate Limit
```
❌ Error: "Rate limit exceeded"
```
Solución: Implementar delays entre solicitudes (mínimo 0.1s para endpoints privados).

### Error de Conexión WebSocket
```
❌ Error: "Connection timeout"
```
Solución: Verificar firewall y reconnect automático.

## 📝 Licencia

MIT License - Ver LICENSE para más detalles.

---

Desarrollado para integración con el sistema de trading distribuido de Coinbase Cripto Trader Claude.
