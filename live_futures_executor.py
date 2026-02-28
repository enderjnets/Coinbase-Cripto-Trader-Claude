#!/usr/bin/env python3
"""
live_futures_executor.py - Ejecutor de Trading Real para Futuros Coinbase
=========================================================================

Sistema completo para ejecutar operaciones de futuros en Coinbase con:
- Conexión autenticada a Coinbase Futures API
- Envío de órdenes reales (market/limit)
- Gestión de posiciones en tiempo real
- Cálculo de liquidaciones
- WebSocket para datos en vivo
- Integración con risk_manager

NO USAR hasta validar completamente en paper trading.

Autor: Strategy Miner Team
Fecha: Feb 2026
"""

import os
import sys
import json
import time
import asyncio
import base64
import threading
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import requests

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# Import shared auth module
try:
    from coinbase_auth import CoinbaseAuth
    HAS_SHARED_AUTH = True
except ImportError:
    HAS_SHARED_AUTH = False

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# API URLs
COINBASE_API_URL = "https://api.coinbase.com"
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"

# Endpoints
ENDPOINTS = {
    'balance': '/api/v3/brokerage/cfm/balance_summary',
    'positions': '/api/v3/brokerage/cfm/positions',
    'orders': '/api/v3/brokerage/orders',
    'fills': '/api/v3/brokerage/orders/historical/fills',
    'products': '/api/v3/brokerage/products',
    'futures_products': '/api/v3/brokerage/products?product_type=FUTURE',
    'margin_window': '/api/v3/brokerage/cfm/margin_window',
}

# API Key path
API_KEY_PATH = "/Users/enderj/Downloads/cdp_api_key.json"

# Rate limits
RATE_LIMIT_DELAY = 0.1  # 100ms entre requests

# ============================================================================
# PRODUCT MAPPING
# ============================================================================

# Mapeo de códigos internos a product IDs de Coinbase
FUTURES_PRODUCT_MAP = {
    # Perpetuos (Nano contracts)
    'BIP-20DEC30-CDE': 'BIP-USD',   # Bitcoin Perpetual
    'ETP-20DEC30-CDE': 'ETP-USD',   # Ethereum Perpetual
    'SLP-20DEC30-CDE': 'SLP-USD',   # Solana Perpetual
    'XPP-20DEC30-CDE': 'XPP-USD',   # XRP Perpetual
    'ADP-20DEC30-CDE': 'ADP-USD',   # ADA Perpetual
    'DOP-20DEC30-CDE': 'DOP-USD',   # Dogecoin Perpetual
    'LNP-20DEC30-CDE': 'LNP-USD',   # Link Perpetual
    'AVP-20DEC30-CDE': 'AVP-USD',   # Avalanche Perpetual
    'HEP-20DEC30-CDE': 'HEP-USD',   # Hedera Perpetual
    'LCP-20DEC30-CDE': 'LCP-USD',   # Litecoin Perpetual
    'XLP-20DEC30-CDE': 'XLP-USD',   # Stellar Perpetual

    # Dated (contratos con expiración)
    'BIT-27FEB26-CDE': 'BIT-27FEB26',
    'BIT-27MAR26-CDE': 'BIT-27MAR26',
    'ET-27FEB26-CDE': 'ET-27FEB26',
    'ET-27MAR26-CDE': 'ET-27MAR26',
    'SOL-27FEB26-CDE': 'SOL-27FEB26',
    'SOL-27MAR26-CDE': 'SOL-27MAR26',
    'XRP-27FEB26-CDE': 'XRP-27FEB26',
    'ADA-27FEB26-CDE': 'ADA-27FEB26',
    'DOT-27FEB26-CDE': 'DOT-27FEB26',
    'LNK-27FEB26-CDE': 'LNK-27FEB26',
    'BCH-27FEB26-CDE': 'BCH-27FEB26',
    'LC-27FEB26-CDE': 'LC-27FEB26',
    'SUI-27FEB26-CDE': 'SUI-27FEB26',
    'AVA-27FEB26-CDE': 'AVA-27FEB26',
    'DOG-27FEB26-CDE': 'DOG-27FEB26',
    'XLM-27FEB26-CDE': 'XLM-27FEB26',
    'HED-27FEB26-CDE': 'HED-27FEB26',
    'SHB-27FEB26-CDE': 'SHB-27FEB26',
    # Commodities
    'GOL-27MAR26-CDE': 'GOL-27MAR26',
    'NOL-19MAR26-CDE': 'NOL-19MAR26',
    'CU-25FEB26-CDE': 'CU-25FEB26',
    'NGS-24FEB26-CDE': 'NGS-24FEB26',
    'PT-27MAR26-CDE': 'PT-27MAR26',
    'MC-19MAR26-CDE': 'MC-19MAR26',
}

# Tamaños de contrato
CONTRACT_SIZES = {
    'BIT': 0.01, 'BIP': 0.01,  # Nano Bitcoin = 0.01 BTC
    'ET': 0.10, 'ETP': 0.10,   # Nano Ethereum = 0.10 ETH
    'SOL': 5.0, 'SLP': 5.0,    # Solana = 5 SOL
    'XRP': 500.0, 'XPP': 500.0, # XRP = 500
    'ADA': 1000.0, 'ADP': 1000.0,
    'DOT': 50.0, 'DOP': 50.0,
    'LNK': 10.0, 'LNP': 10.0,
    'BCH': 1.0, 'LCP': 1.0,
}


# ============================================================================
# DATA CLASSES
# ============================================================================

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Position:
    """Representa una posición de futures abierta."""
    product_id: str
    side: PositionSide
    size: int  # Número de contratos
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    leverage: int
    margin: float
    liquidation_price: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class Order:
    """Representa una orden."""
    order_id: str
    product_id: str
    side: OrderSide
    order_type: OrderType
    size: int
    price: Optional[float]
    status: str
    created_at: datetime
    filled_size: int = 0
    avg_fill_price: float = 0.0


# ============================================================================
# JWT AUTHENTICATION
# ============================================================================

class CoinbaseAuth:
    """Autenticación JWT Ed25519 para Coinbase."""

    def __init__(self, api_key_path: str = API_KEY_PATH):
        self.api_key, self.private_key = self._load_key(api_key_path)
        self._token_cache = None
        self._token_uri = None
        self._token_expires = 0

    def _load_key(self, path: str) -> Tuple[str, Ed25519PrivateKey]:
        """Carga la clave API desde archivo JSON."""
        with open(path, 'r') as f:
            data = json.load(f)

        key_id = data['id']
        private_key_b64 = data['privateKey']

        # Decodificar base64
        raw = base64.b64decode(private_key_b64)

        # Los primeros 32 bytes son la seed para Ed25519
        seed = raw[:32]
        private_key = Ed25519PrivateKey.from_private_bytes(seed)

        return key_id, private_key

    def generate_jwt(self, method: str, path: str) -> str:
        """Genera JWT para autenticación."""
        now = int(time.time())

        # URI sin https://
        uri = f"{method} api.coinbase.com{path}"

        # Header
        header = {
            "alg": "EdDSA",
            "kid": self.api_key,
            "typ": "JWT",
            "nonce": now
        }

        # Payload
        payload = {
            "iss": "cdp",
            "nbf": now,
            "exp": now + 120,
            "sub": self.api_key,
            "uri": uri
        }

        # Encode
        def b64url(data):
            if isinstance(data, str):
                data = data.encode()
            return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

        header_b64 = b64url(json.dumps(header, separators=(',', ':')))
        payload_b64 = b64url(json.dumps(payload, separators=(',', ':')))

        # Sign
        message = f"{header_b64}.{payload_b64}".encode()
        signature = self.private_key.sign(message)
        signature_b64 = b64url(signature)

        return f"{message.decode()}.{signature_b64}"

    def get_headers(self, method: str, path: str) -> Dict[str, str]:
        """Obtiene headers con autenticación."""
        return {
            "Authorization": f"Bearer {self.generate_jwt(method, path)}",
            "Content-Type": "application/json"
        }


# ============================================================================
# LIVE FUTURES EXECUTOR
# ============================================================================

class LiveFuturesExecutor:
    """
    Ejecutor de trading real para futuros en Coinbase.

    Maneja:
    - Conexión autenticada a API
    - Envío y seguimiento de órdenes
    - Gestión de posiciones
    - WebSocket para datos en tiempo real
    """

    def __init__(self, api_key_path: str = API_KEY_PATH, dry_run: bool = True):
        """
        Args:
            api_key_path: Ruta al archivo de API key
            dry_run: Si True, no envía órdenes reales (solo simula)
        """
        if not HAS_CRYPTO:
            raise ImportError("Se requiere cryptography: pip install cryptography")

        self.auth = CoinbaseAuth(api_key_path)
        self.dry_run = dry_run
        self.session = requests.Session()

        # State
        self.positions: Dict[str, Position] = {}
        self.pending_orders: Dict[str, Order] = {}
        self.balance = 0.0
        self.available_margin = 0.0
        self.used_margin = 0.0

        # Rate limiting
        self.last_request_time = 0

        # WebSocket
        self.ws = None
        self.ws_running = False
        self.ws_thread = None

        # Callbacks
        self.on_fill_callback = None
        self.on_position_change_callback = None

        # Load initial state
        self._load_state()

    def _rate_limit(self):
        """Aplica rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

    def _request(self, method: str, path: str, data: dict = None) -> dict:
        """Realiza request autenticado a la API."""
        self._rate_limit()

        url = f"{COINBASE_API_URL}{path}"
        headers = self.auth.get_headers(method, path)

        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=30)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Método no soportado: {method}")

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}", "body": response.text}

        except Exception as e:
            return {"error": str(e)}

    # ========== ACCOUNT METHODS ==========

    def get_balance(self) -> Dict[str, float]:
        """Obtiene balance de la cuenta de futuros."""
        result = self._request("GET", ENDPOINTS['balance'])

        if "error" in result:
            print(f"❌ Error obteniendo balance: {result['error']}")
            return {"balance": 0, "available": 0, "margin_used": 0}

        try:
            balance_info = {
                "balance": float(result.get("total_balance", {}).get("value", 0)),
                "available": float(result.get("available_balance", {}).get("value", 0)),
                "margin_used": float(result.get("margin_used", {}).get("value", 0)),
                "unrealized_pnl": float(result.get("unrealized_pnl", {}).get("value", 0)),
            }

            self.balance = balance_info["balance"]
            self.available_margin = balance_info["available"]
            self.used_margin = balance_info["margin_used"]

            return balance_info

        except (KeyError, TypeError) as e:
            print(f"❌ Error parseando balance: {e}")
            return {"balance": 0, "available": 0, "margin_used": 0}

    def get_positions(self) -> List[Position]:
        """Obtiene todas las posiciones abiertas."""
        result = self._request("GET", ENDPOINTS['positions'])

        if "error" in result:
            print(f"❌ Error obteniendo posiciones: {result['error']}")
            return []

        positions = []
        self.positions.clear()

        for pos_data in result.get("positions", []):
            try:
                product_id = pos_data.get("product_id", "")
                side = PositionSide.LONG if pos_data.get("side") == "long" else PositionSide.SHORT
                size = int(pos_data.get("size", 0))
                entry_price = float(pos_data.get("average_entry_price", {}).get("value", 0))
                mark_price = float(pos_data.get("mark_price", {}).get("value", 0))
                pnl = float(pos_data.get("unrealized_pnl", {}).get("value", 0))

                # Calcular leverage aproximado desde margin
                position_value = size * entry_price * self._get_contract_size(product_id)
                margin = float(pos_data.get("margin_used", {}).get("value", position_value / 10))
                leverage = int(position_value / margin) if margin > 0 else 1

                # Calcular liquidación
                liq_price = self._calculate_liquidation(entry_price, side, leverage)

                position = Position(
                    product_id=product_id,
                    side=side,
                    size=size,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=pnl,
                    leverage=leverage,
                    margin=margin,
                    liquidation_price=liq_price,
                    entry_time=datetime.now()  # No viene en API
                )

                positions.append(position)
                self.positions[product_id] = position

            except Exception as e:
                print(f"⚠️ Error parseando posición: {e}")
                continue

        return positions

    def get_margin_window(self) -> str:
        """Obtiene ventana de margen actual (intraday/overnight)."""
        result = self._request("GET", ENDPOINTS['margin_window'])

        if "error" in result:
            return "intraday"  # Default

        return result.get("margin_window", "intraday")

    # ========== ORDER METHODS ==========

    def place_order(
        self,
        product_id: str,
        side: OrderSide,
        size: int,
        order_type: OrderType = OrderType.MARKET,
        price: float = None,
        reduce_only: bool = False,
        time_in_force: str = "GTC"
    ) -> Dict:
        """
        Coloca una orden de futures.

        Args:
            product_id: ID del producto (ej. "BIT-27FEB26" o "BIP-USD")
            side: BUY o SELL
            size: Número de contratos (entero)
            order_type: MARKET o LIMIT
            price: Precio para órdenes LIMIT
            reduce_only: Solo reducir posición existente
            time_in_force: GTC, IOC, FOK

        Returns:
            Dict con order_id o error
        """
        # Dry run - solo simular
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "order_id": f"DRY-{int(time.time()*1000)}",
                "product_id": product_id,
                "side": side.value,
                "size": size,
                "type": order_type.value,
                "price": price,
                "message": "Orden simulada (dry_run=True)"
            }

        # Construir payload
        order_config = {
            "product_id": product_id,
            "side": side.value,
            "size": str(size),
            "reduce_only": reduce_only
        }

        if order_type == OrderType.LIMIT:
            if not price:
                return {"error": "Precio requerido para órdenes LIMIT"}
            order_config["limit_price"] = str(price)
            order_config["time_in_force"] = time_in_force
            config_key = "limit_limit_gtc"
        else:
            config_key = "market_market_ioc"

        payload = {
            "client_order_id": f"SM-{int(time.time()*1000)}",
            "product_id": product_id,
            "side": side.value,
            "order_configuration": {
                config_key: order_config
            }
        }

        result = self._request("POST", ENDPOINTS['orders'], payload)

        if "error" in result:
            return {"success": False, "error": result["error"]}

        order_id = result.get("order_id", "")
        success = result.get("success", False)

        if success and order_id:
            order = Order(
                order_id=order_id,
                product_id=product_id,
                side=side,
                order_type=order_type,
                size=size,
                price=price,
                status="PENDING",
                created_at=datetime.now()
            )
            self.pending_orders[order_id] = order

        return {
            "success": success,
            "order_id": order_id,
            "response": result
        }

    def cancel_order(self, order_id: str) -> Dict:
        """Cancela una orden pendiente."""
        if self.dry_run:
            return {"success": True, "dry_run": True, "message": "Orden cancelada (simulado)"}

        result = self._request("DELETE", f"{ENDPOINTS['orders']}/{order_id}")

        if "error" in result:
            return {"success": False, "error": result["error"]}

        if order_id in self.pending_orders:
            del self.pending_orders[order_id]

        return {"success": True, "order_id": order_id}

    def get_order_status(self, order_id: str) -> Dict:
        """Obtiene estado de una orden."""
        result = self._request("GET", f"{ENDPOINTS['orders']}/{order_id}")

        if "error" in result:
            return {"error": result["error"]}

        return result

    # ========== POSITION MANAGEMENT ==========

    def open_position(
        self,
        product_id: str,
        side: PositionSide,
        leverage: int,
        margin_usd: float,
        stop_loss_pct: float = 0.03,
        take_profit_pct: float = 0.06
    ) -> Dict:
        """
        Abre una posición de futures.

        Args:
            product_id: ID del producto
            side: LONG o SHORT
            leverage: Apalancamiento (1-10)
            margin_usd: Margen en USD a usar
            stop_loss_pct: Porcentaje de stop loss
            take_profit_pct: Porcentaje de take profit

        Returns:
            Resultado de la operación
        """
        # Verificar margen disponible
        if margin_usd > self.available_margin:
            return {"success": False, "error": f"Margen insuficiente. Disponible: ${self.available_margin:.2f}"}

        # Obtener precio actual
        current_price = self._get_current_price(product_id)
        if not current_price:
            return {"success": False, "error": "No se pudo obtener precio actual"}

        # Calcular tamaño de posición
        contract_size = self._get_contract_size(product_id)
        position_value = margin_usd * leverage
        contracts = int(position_value / (current_price * contract_size))

        if contracts < 1:
            return {"success": False, "error": "Tamaño de posición muy pequeño"}

        # Determinar lado de la orden
        # Para LONG: BUY abre, SELL cierra
        # Para SHORT: SELL abre, BUY cierra
        order_side = OrderSide.BUY if side == PositionSide.LONG else OrderSide.SELL

        # Enviar orden
        result = self.place_order(
            product_id=product_id,
            side=order_side,
            size=contracts,
            order_type=OrderType.MARKET
        )

        if result.get("success"):
            # Calcular precios de SL/TP
            if side == PositionSide.LONG:
                sl_price = current_price * (1 - stop_loss_pct)
                tp_price = current_price * (1 + take_profit_pct)
            else:
                sl_price = current_price * (1 + stop_loss_pct)
                tp_price = current_price * (1 - take_profit_pct)

            result["position_details"] = {
                "side": side.value,
                "contracts": contracts,
                "entry_price": current_price,
                "leverage": leverage,
                "margin": margin_usd,
                "stop_loss": sl_price,
                "take_profit": tp_price,
                "liquidation_price": self._calculate_liquidation(current_price, side, leverage)
            }

        return result

    def close_position(self, product_id: str, reason: str = "manual") -> Dict:
        """Cierra una posición existente."""
        if product_id not in self.positions:
            # Intentar obtener de API
            self.get_positions()
            if product_id not in self.positions:
                return {"success": False, "error": f"No hay posición abierta para {product_id}"}

        position = self.positions[product_id]

        # Orden opuesta para cerrar
        close_side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY

        result = self.place_order(
            product_id=product_id,
            side=close_side,
            size=position.size,
            order_type=OrderType.MARKET,
            reduce_only=True
        )

        if result.get("success"):
            # Remover de tracking local
            del self.positions[product_id]

            result["close_details"] = {
                "product_id": product_id,
                "side_closed": position.side.value,
                "size": position.size,
                "pnl": position.unrealized_pnl,
                "reason": reason
            }

        return result

    def close_all_positions(self, reason: str = "emergency") -> List[Dict]:
        """Cierra todas las posiciones."""
        results = []

        # Refrescar posiciones
        self.get_positions()

        for product_id in list(self.positions.keys()):
            result = self.close_position(product_id, reason)
            results.append(result)

        return results

    # ========== HELPERS ==========

    def _get_contract_size(self, product_id: str) -> float:
        """Obtiene tamaño de contrato para un producto."""
        prefix = product_id.split("-")[0]
        return CONTRACT_SIZES.get(prefix, 1.0)

    def _get_current_price(self, product_id: str) -> Optional[float]:
        """Obtiene precio actual de un producto."""
        # Mapear a product ID de Coinbase
        cb_product = FUTURES_PRODUCT_MAP.get(product_id, product_id)

        result = self._request("GET", f"/api/v3/brokerage/products/{cb_product}")

        if "error" in result:
            # Intentar con el product_id directamente
            result = self._request("GET", f"/api/v3/brokerage/products/{product_id}")

        if "error" in result:
            return None

        try:
            return float(result.get("price", 0))
        except (KeyError, TypeError, ValueError):
            return None

    def _calculate_liquidation(self, entry_price: float, side: PositionSide, leverage: int) -> float:
        """Calcula precio de liquidación."""
        maintenance_margin = 0.05  # 5%

        if side == PositionSide.LONG:
            # Long se liquida cuando precio baja
            return entry_price * (1 - (1/leverage) + maintenance_margin)
        else:
            # Short se liquida cuando precio sube
            return entry_price * (1 + (1/leverage) - maintenance_margin)

    def _load_state(self):
        """Carga estado inicial."""
        self.get_balance()
        self.get_positions()

    def _save_state(self):
        """Guarda estado en archivo."""
        state = {
            "balance": self.balance,
            "available_margin": self.available_margin,
            "used_margin": self.used_margin,
            "positions": {
                pid: {
                    "side": p.side.value,
                    "size": p.size,
                    "entry_price": p.entry_price,
                    "leverage": p.leverage
                }
                for pid, p in self.positions.items()
            },
            "timestamp": time.time()
        }

        try:
            with open("/tmp/live_futures_state.json", "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error guardando estado: {e}")

    # ========== WEBSOCKET ==========

    def start_websocket(self, products: List[str]):
        """Inicia conexión WebSocket para datos en tiempo real."""
        if not HAS_WEBSOCKETS:
            print("⚠️ websockets no instalado")
            return

        self.ws_running = True
        self.ws_thread = threading.Thread(target=self._ws_loop, args=(products,))
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def _ws_loop(self, products: List[str]):
        """Loop de WebSocket."""
        async def connect():
            async with websockets.connect(COINBASE_WS_URL) as ws:
                self.ws = ws

                # Suscribirse
                subscribe = {
                    "type": "subscribe",
                    "product_ids": products,
                    "channels": ["ticker", "matches"]
                }
                await ws.send(json.dumps(subscribe))

                while self.ws_running:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(message)
                        self._handle_ws_message(data)
                    except asyncio.TimeoutError:
                        # Ping para mantener conexión
                        await ws.ping()
                    except Exception as e:
                        print(f"⚠️ WebSocket error: {e}")
                        break

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(connect())

    def _handle_ws_message(self, data: dict):
        """Maneja mensajes de WebSocket."""
        msg_type = data.get("type")

        if msg_type == "ticker":
            # Actualizar precio
            product_id = data.get("product_id")
            price = float(data.get("price", 0))

            if product_id in self.positions:
                self.positions[product_id].mark_price = price

                # Check stop loss / take profit
                self._check_exit_conditions(product_id, price)

        elif msg_type == "match":
            # Orden ejecutada
            if self.on_fill_callback:
                self.on_fill_callback(data)

    def _check_exit_conditions(self, product_id: str, price: float):
        """Verifica condiciones de salida (SL/TP) para una posición."""
        if product_id not in self.positions:
            return

        pos = self.positions[product_id]

        # Check liquidation
        if pos.side == PositionSide.LONG:
            if price <= pos.liquidation_price:
                print(f"🚨 LIQUIDATION: {product_id} LONG @ ${price:.2f}")
                self.close_position(product_id, "liquidation")
                return

            if pos.stop_loss and price <= pos.stop_loss:
                self.close_position(product_id, "stop_loss")
                return

            if pos.take_profit and price >= pos.take_profit:
                self.close_position(product_id, "take_profit")
                return

        else:  # SHORT
            if price >= pos.liquidation_price:
                print(f"🚨 LIQUIDATION: {product_id} SHORT @ ${price:.2f}")
                self.close_position(product_id, "liquidation")
                return

            if pos.stop_loss and price >= pos.stop_loss:
                self.close_position(product_id, "stop_loss")
                return

            if pos.take_profit and price <= pos.take_profit:
                self.close_position(product_id, "take_profit")
                return

    def stop_websocket(self):
        """Detiene WebSocket."""
        self.ws_running = False
        if self.ws:
            asyncio.run(self.ws.close())

    # ========== STATUS ==========

    def get_status(self) -> Dict:
        """Obtiene estado completo del executor."""
        return {
            "dry_run": self.dry_run,
            "balance": self.balance,
            "available_margin": self.available_margin,
            "used_margin": self.used_margin,
            "margin_utilization": self.used_margin / self.balance if self.balance > 0 else 0,
            "open_positions": len(self.positions),
            "pending_orders": len(self.pending_orders),
            "positions": {
                pid: {
                    "side": p.side.value,
                    "size": p.size,
                    "entry": p.entry_price,
                    "mark": p.mark_price,
                    "pnl": p.unrealized_pnl,
                    "leverage": p.leverage,
                    "liquidation": p.liquidation_price
                }
                for pid, p in self.positions.items()
            },
            "websocket_running": self.ws_running
        }


# ============================================================================
# STANDALONE TEST
# ============================================================================

def test_executor():
    """Prueba el executor en modo dry_run."""
    print("="*70)
    print("🧪 LIVE FUTURES EXECUTOR - TEST MODE")
    print("="*70)

    # Crear executor en modo dry_run
    executor = LiveFuturesExecutor(dry_run=True)

    print(f"\n📊 Estado inicial:")
    status = executor.get_status()
    print(f"   Dry Run: {status['dry_run']}")
    print(f"   Balance: ${status['balance']:.2f}")
    print(f"   Available Margin: ${status['available_margin']:.2f}")

    # Simular apertura de posición
    print(f"\n📈 Abriendo posición LONG en BIP-USD...")
    result = executor.open_position(
        product_id="BIP-20DEC30-CDE",
        side=PositionSide.LONG,
        leverage=5,
        margin_usd=100,
        stop_loss_pct=0.03,
        take_profit_pct=0.06
    )

    print(f"   Resultado: {json.dumps(result, indent=2, default=str)}")

    # Cerrar posición
    print(f"\n📉 Cerrando posición...")
    close_result = executor.close_position("BIP-20DEC30-CDE", reason="manual_test")
    print(f"   Resultado: {json.dumps(close_result, indent=2, default=str)}")

    print("\n✅ Test completado")


if __name__ == "__main__":
    test_executor()
