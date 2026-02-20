# 📊 Integración de API de Futuros de Coinbase - Investigación

## 📋 Resumen Ejecutivo

Este documento detalla la investigación sobre la API de Futuros de Coinbase Advanced Trade para expandir el sistema de trading distribuido desde Spot hacia derivados regulados.

---

## 🏛️ Arquitectura Institucional

### Entidades de Coinbase para Derivados

| Entidad | Mercado | Regulación | Custodia |
|---------|---------|------------|----------|
| **CFM** (Coinbase Financial Markets) | EE.UU. | CFTC/NFA | Futuros regulados |
| **CBI** (Coinbase Inc.) | EE.UU. | - | Spot (no regulado) |
| **INTX** (International Exchange) | Internacional | Jurisdicciones globales | Perpetuos |

### Segregación de Cuentas
- **Saldos de futuros** → CFM (bajo protección CFTC)
- **Saldos de spot** → CBI (sin protección CFTC)
- Transferencias automáticas a las 5:00 PM ET para cumplir requisitos de margen

---

## 🔄 Tipos de Contratos

### Futuros (US Derivatives)
| Característica | Detalle |
|----------------|---------|
| Vencimiento | Fecha fija (ej. Feb 2026, Mar 2026) |
| Liquidación | Efectivo al vencimiento |
| Activos | Cripto + Materias Primas (Oro, Plata, Petróleo) |
| Entidad | CFM (regulado CFTC) |

### Perpetuos (International Exchange)
| Característica | Detalle |
|----------------|---------|
| Vencimiento | Sin fecha (continuo) |
| Mecanismo | Funding Rate |
| Activos | Principalmente cripto (BTC, ETH, SOL, XRP) |
| Entidad | INTX |

---

## 📦 Contratos Nano Disponibles

| Contrato | Tamaño | Símbolo | Tick | Valor Tick |
|----------|---------|----------|-------|------------|
| Nano Bitcoin (BIT) | 0.01 BTC | BIT | $0.05 | $0.05 |
| Nano Ether (ETP) | 0.10 ETH | ETP | $0.50 | $0.05 |
| Nano Solana (SLP) | 5 SOL | SLP | $0.01 | $0.05 |
| Nano XRP (XPP) | 500 XRP | XPP | $0.0001 | $0.05 |

---

## 🔐 Protocolos de Autenticación

### Sistema de JWT (JSON Web Tokens)

```python
# Estructura del JWT
{
    "iss": "cdp",                                    # Issuer
    "nbf": 1234567890,                               # Not Before
    "exp": 1234569010,                               # Expiration (max 120s)
    "sub": "api-key-name",                           # Subject
    "uri": "GET api.coinbase.com/..."               # Endpoint
}
```

### Algoritmos de Firma Soportados
| Algoritmo | Recomendación | Uso |
|-----------|---------------|-----|
| **Ed25519** | ✅ Preferido | Alta frecuencia, baja latencia |
| ECDSA (ES256) | ⚠️ Alternativo | Compatibilidad legacy |

### Implementación Recomendada
```python
# Usar Ed25519 para mejor rendimiento
headers = {"alg": "EdDSA"}
# Clave secreta como variable de entorno
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET")
```

---

## 🔗 Endpoints Críticos para CFM

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/cfm/balance_summary` | GET | Saldos y margen disponible |
| `/cfm/positions` | GET | Posiciones abiertas |
| `/cfm/sweeps/schedule` | POST/GET | Programar transferencias de fondos |
| `/cfm/margin_window` | GET | Verificar ventana de margen |

---

## 📡 WebSockets para Datos en Tiempo Real

### Canales para Futuros

| Canal | Tipo | Uso |
|-------|------|-----|
| `futures_balance_summary` | Privado | Actualizaciones de equidad y margen |
| `user` | Privado | Estado de órdenes |
| `heartbeats` | Público | Mantener conexión viva |

### Conexión WebSocket
```python
# Los WebSockets requieren JWT en suscripción inicial
# Timeout de 5 segundos para suscripción válida
# Recomendación: Conexiones separadas por producto (BTC, ETH)
```

---

## 💰 Gestión de Márgenes

### Margen Intradiario vs Nocturno

| Período | Horario (ET) | Requisitos |
|---------|--------------|------------|
| **Intraday** | 8:00 AM - 4:00 PM | Menor (más apalancamiento) |
| **Overnight** | 4:00 PM en adelante | Mayor (menos apalancamiento) |

### Fórmula del Ratio de Margen
```
Margin Ratio = Margin Available / Total Required Margin
```

### Umbral de Liquidación
- **Ratio < 1.0** → Coinbase inicia liquidación automática
- **Acción requerida**: Añadir colateral o cerrar posiciones

---

## ⚠️ Límites de API

| Tipo de Solicitud | Límite | Ráfaga |
|-------------------|---------|---------|
| Endpoints Públicos | 10/seg | 15 |
| Endpoints Privados | 15/seg | 30 |
| Endpoints /fills | 10/seg | 20 |
| WebSockets | 8/seg | 20 ráfaga |

---

## 🛠️ Implementación con SDK de Python

### Componentes del SDK

```python
from coinbase.advanced_trade import AdvancedTradeAPIClient

# Cliente REST
rest_client = AdvancedTradeAPIClient(
    api_key=API_KEY,
    private_key=PRIVATE_KEY
)

# Métodos clave
balance = rest_client.get_futures_balance_summary()
positions = rest_client.list_futures_positions()
```

### Entorno de Pruebas (Sandbox)
```
URL: api-sandbox.coinbase.com
- Respuestas simuladas para testing
- Validación de lógica sin riesgo financiero
```

---

## 🎯 Estrategias Recomendadas para Integración

### 1. Arbitraje de Funding Rate
- Monitorear tasas de financiación en perpetuos
- Posición corta cuando funding > X%
- Cubrir riesgo con spot

### 2. Cash and Carry
- Comprar spot + vender futuros
- Garantizar prima al vencimiento

### 3. Rollover Automatizado
- Detectar proximidad a vencimiento
- Migrar liquidez al siguiente contrato

### 4. Hedging con Nano Contracts
- Cobertura de posiciones spot
- Menor capital requerido (0.01 BTC, 0.1 ETH)

---

## 📋 Plan de Integración con el Sistema Actual

### Fase 1: Infraestructura (1-2 semanas)
- [ ] Crear cliente Coinbase Advanced Trade
- [ ] Implementar autenticación JWT Ed25519
- [ ] Configurar endpoints de CFM
- [ ] Configurar WebSockets para datos en tiempo real

### Fase 2: Funcionalidades Básicas (1 semana)
- [ ] Obtener saldos y posiciones
- [ ] Implementar consulta de margen
- [ ] Programar transfers CBI ↔ CFM
- [ ] Monitoreo de ventanas de margen

### Fase 3: Estrategias (2-3 semanas)
- [ ] Hedging automático de posiciones spot
- [ ] Arbitraje de funding rate
- [ ] Rollover automatizado de contratos

### Fase 4: Optimización (1 semana)
- [ ] Implementar gestión de límites de API
- [ ] Optimizar conexión WebSocket
- [ ] Sistema de alertas de margen

---

## 🔗 Recursos de Referencia

- Documentación: https://docs.coinbase.com/advanced-trade/
- SDK Python: `coinbase-advanced-py`
- Sandbox: api-sandbox.coinbase.com

---

*Documento generado: 19 Febrero 2026*
*Basado en investigación: "Usar API de Futuros de Coinbase.rtf"*
