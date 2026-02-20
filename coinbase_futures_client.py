#!/usr/bin/env python3
"""
🔐 Coinbase Futures API Client v1.0
Cliente para interactuar con la API de Futuros de Coinbase Advanced Trade

Características:
- Autenticación JWT con Ed25519
- Gestión de posiciones CFM
- WebSockets para datos en tiempo real
- Gestión de márgenes y límites

Documentación:
https://docs.coinbase.com/advanced-trade/
"""

import os
import time
import json
import hmac
import hashlib
import requests
import websocket
import threading
from typing import Optional, Dict, List, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# ============================================================
# CONFIGURACIÓN
# ============================================================

class CoinbaseConfig:
    """Configuración del cliente de Coinbase"""
    
    # URLs
    API_URL = "https://api.coinbase.com"
    SANDBOX_URL = "https://api-sandbox.coinbase.com"
    WS_URL = "wss://ws-feed.exchange.coinbase.com"
    WS_SANDBOX_URL = "wss://ws-feed-sandbox.exchange.coinbase.com"
    
    # Endpoints CFM (US Derivatives)
    CFM_BALANCE = "/api/v3/brokerage/cfm/balance_summary"
    CFM_POSITIONS = "/api/v3/brokerage/cfm/positions"
    CFM_SWEEPS = "/api/v3/brokerage/cfm/sweeps/schedule"
    CFM_MARGIN_WINDOW = "/api/v3/brokerage/cfm/margin_window"
    
    # Endpoints INTX (Perpetuals)
    INTX_POSITIONS = "/api/v3/brokerage/intx/positions"
    INTX_MULTI_COLLATERAL = "/api/v3/brokerage/intx/multi_asset_collateral"
    
    # Endpoints generales
    ORDERS = "/api/v3/brokerage/orders"
    PRODUCTS = "/api/v3/brokerage/products"
    
    # Límites de API
    RATE_LIMIT_PUBLIC = 10  # requests/second
    RATE_LIMIT_PRIVATE = 15
    RATE_LIMIT_FILLS = 10
    
    @classmethod
    def get_api_url(cls, sandbox=False):
        return cls.SANDBOX_URL if sandbox else cls.API_URL
    
    @classmethod
    def get_ws_url(cls, sandbox=False):
        return cls.WS_SANDBOX_URL if sandbox else cls.WS_URL


# ============================================================
# AUTENTICACIÓN JWT
# ============================================================

class JWTAuthenticator:
    """Generador de tokens JWT para autenticación Coinbase"""
    
    def __init__(self, api_key: str, private_key: str, sandbox: bool = False):
        self.api_key = api_key
        self.private_key = private_key
        self.sandbox = sandbox
        self._cached_token = None
        self._token_expires = 0
    
    def generate_token(self) -> str:
        """Genera un JWT token válido para Coinbase API"""
        
        # Verificar si tenemos un token válido
        if self._cached_token and time.time() < self._token_expires - 10:
            return self._cached_token
        
        # Timestamps
        now = int(time.time())
        exp = now + 120  # Max 120 segundos
        
        # Headers JWT
        headers = {
            "alg": "EdDSA",  # Usar Ed25519
            "typ": "JWT"
        }
        
        # Payload JWT
        # Nota: La URI debe incluir método + host + path
        payload = {
            "iss": "cdp",
            "nbf": now,
            "exp": exp,
            "sub": self.api_key,
            "uri": f"GET {CoinbaseConfig.get_api_url(self.sandbox).replace('https://', '')}/api/v3/brokerage/cfm/balance_summary"
        }
        
        # Codificar header y payload
        header_b64 = self._base64url_encode(json.dumps(headers))
        payload_b64 = self._base64url_encode(json.dumps(payload))
        
        # Crear mensaje a firmar
        message = f"{header_b64}.{payload_b64}"
        
        # Firmar con clave privada Ed25519
        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519
            from cryptography.hazmat.primitives import serialization
            
            # Cargar clave privada
            key = serialization.load_pem_private_key(
                self.private_key.encode(),
                password=None
            )
            
            # Firmar mensaje
            signature = key.sign(message.encode())
            signature_b64 = self._base64url_encode(signature)
            
            # Token JWT completo
            token = f"{message}.{signature_b64}"
            
            # Cachear token
            self._cached_token = token
            self._token_expires = exp
            
            return token
            
        except ImportError:
            # Fallback para cuando cryptography no está instalado
            print("⚠️ cryptography library required for Ed25519 signing")
            print("   Install with: pip install cryptography")
            return ""
    
    def _base64url_encode(self, data: str or bytes) -> str:
        """Codifica en base64url sin padding"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        import base64
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


# ============================================================
# CLIENTE REST DE FUTUROS
# ============================================================

class CoinbaseFuturesClient:
    """Cliente para interactuar con la API de Futuros de Coinbase"""
    
    def __init__(self, api_key: str, private_key: str, sandbox: bool = False):
        self.config = CoinbaseConfig
        self.auth = JWTAuthenticator(api_key, private_key, sandbox)
        self.sandbox = sandbox
        self.base_url = self.config.get_api_url(sandbox)
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_interval = 1.0 / self.config.RATE_LIMIT_PRIVATE
    
    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Realiza una solicitud autenticada a la API"""
        
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
        
        # Generar token JWT
        token = self.auth.generate_token()
        
        # Headers con autorización
        headers = {"Authorization": f"Bearer {token}"}
        
        # URL completa
        url = f"{self.base_url}{endpoint}"
        
        # Realizar solicitud
        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=30)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error en solicitud API: {e}")
            return {"error": str(e)}
    
    # ========== GESTIÓN DE CUENTA ==========
    
    def get_balance_summary(self) -> dict:
        """Obtiene resumen de balance de futuros"""
        return self._request("GET", self.config.CFM_BALANCE)
    
    def get_positions(self) -> dict:
        """Obtiene todas las posiciones abiertas"""
        return self._request("GET", self.config.CFM_POSITIONS)
    
    def get_margin_window(self) -> dict:
        """Verifica ventana de margen actual (intradiario/overnight)"""
        return self._request("GET", self.config.CFM_MARGIN_WINDOW)
    
    def schedule_sweep(self, direction: str, amount: str) -> dict:
        """
        Programa transferencia de fondos entre cuentas
        
        Args:
            direction: "IN" o "OUT"
            amount: Cantidad en USD
        """
        data = {
            "direction": direction.upper(),
            "amount": amount
        }
        return self._request("POST", self.config.CFM_SWEEPS, data)
    
    # ========== ÓRDENES ==========
    
    def place_order(self, 
                   product_id: str,
                   side: str,
                   order_type: str,
                   size: int,
                   price: float = None,
                   time_in_force: str = "GTC",
                   reduce_only: bool = False) -> dict:
        """
        Coloca una orden de futuros
        
        Args:
            product_id: ID del producto (ej. "BIT-USD" para Nano Bitcoin)
            side: "BUY" o "SELL"
            order_type: "market" o "limit"
            size: Número de contratos (entero)
            price: Precio para órdenes limit
            time_in_force: GTC, IOC, FOK, GTT
            reduce_only: Solo reducir posición existente
        """
        order_configuration = {
            "product_id": product_id,
            "side": side.upper(),
            "order_configuration": {
                order_type.lower() + "_order": {
                    "size": str(size),
                    "time_in_force": time_in_force
                }
            },
            "reduce_only": reduce_only
        }
        
        if price and order_type.lower() == "limit":
            order_configuration["order_configuration"]["limit_order"]["limit_price"] = str(price)
        
        return self._request("POST", self.config.ORDERS, order_configuration)
    
    def cancel_order(self, order_id: str) -> dict:
        """Cancela una orden"""
        return self._request("DELETE", f"{self.config.ORDERS}/{order_id}")
    
    # ========== PRODUCTOS ==========
    
    def get_products(self) -> dict:
        """Obtiene lista de productos disponibles"""
        return self._request("GET", self.config.PRODUCTS)
    
    def get_product(self, product_id: str) -> dict:
        """Obtiene detalles de un producto específico"""
        return self._request("GET", f"{self.config.PRODUCTS}/{product_id}")
    
    # ========== HELPERS ==========
    
    def calculate_margin_ratio(self) -> float:
        """Calcula ratio de margen de la cuenta"""
        balance = self.get_balance_summary()
        
        if "error" in balance:
            return 0.0
        
        try:
            available = float(balance.get("available_balance", {}).get("value", 0))
            required = float(balance.get("required_margin", {}).get("value", 1))
            
            if required == 0:
                return float('inf')
            
            return available / required
            
        except (KeyError, ValueError):
            return 0.0
    
    def get_open_positions_summary(self) -> dict:
        """Obtiene resumen de posiciones abiertas"""
        positions = self.get_positions()
        
        if "error" in positions:
            return {"error": positions["error"]}
        
        try:
            pos_list = positions.get("positions", [])
            
            summary = {
                "total_positions": len(pos_list),
                "long_count": 0,
                "short_count": 0,
                "total_pnl": 0.0,
                "positions": []
            }
            
            for pos in pos_list:
                side = pos.get("side", "")
                size = int(pos.get("size", 0))
                pnl = float(pos.get("unrealized_pnl", {}).get("value", 0))
                
                summary["positions"].append({
                    "product_id": pos.get("product_id"),
                    "side": side,
                    "size": size,
                    "entry_price": float(pos.get("average_entry_price", {}).get("value", 0)),
                    "mark_price": float(pos.get("mark_price", {}).get("value", 0)),
                    "unrealized_pnl": pnl
                })
                
                if side == "long":
                    summary["long_count"] += 1
                else:
                    summary["short_count"] += 1
                
                summary["total_pnl"] += pnl
            
            return summary
            
        except (KeyError, ValueError) as e:
            return {"error": f"Error parsing positions: {e}"}
    
    def is_margin_intraday(self) -> bool:
        """Verifica si estamos en ventana de margen intradiario"""
        margin = self.get_margin_window()
        
        if "error" in margin:
            return True  # Asumir intradiario por defecto
        
        try:
            window = margin.get("margin_window", "")
            return window == "intraday"
        except (KeyError, AttributeError):
            return True


# ============================================================
# WEBSOCKET CLIENT
# ============================================================

class CoinbaseWebSocketClient:
    """Cliente WebSocket para datos en tiempo real"""
    
    def __init__(self, api_key: str, private_key: str, sandbox: bool = False):
        self.auth = JWTAuthenticator(api_key, private_key, sandbox)
        self.sandbox = sandbox
        self.ws_url = CoinbaseConfig.get_ws_url(sandbox)
        self.ws = None
        self.ws_thread = None
        self.running = False
        self.subscriptions = {}
        self.callbacks = {}
    
    def connect(self):
        """Inicia conexión WebSocket"""
        self.running = True
        self.ws_thread = threading.Thread(target=self._run_websocket)
        self.ws_thread.start()
    
    def _run_websocket(self):
        """Ejecuta el loop principal de WebSocket"""
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                self.ws.run_forever(ping_interval=30)
            except Exception as e:
                print(f"WebSocket error: {e}")
                time.sleep(5)
    
    def _on_open(self, ws):
        """Callback cuando se abre la conexión"""
        print("✅ WebSocket conectado")
        
        # Suscribirse a canales configurados
        for channel, products in self.subscriptions.items():
            self.subscribe(channel, products)
    
    def _on_message(self, ws, message):
        """Procesa mensajes recibidos"""
        try:
            data = json.loads(message)
            
            # Ejecutar callback si existe para este tipo de mensaje
            msg_type = data.get("type", "")
            if msg_type in self.callbacks:
                self.callbacks[msg_type](data)
                
        except json.JSONDecodeError:
            print(f"Error decodificando mensaje: {message}")
    
    def _on_error(self, ws, error):
        """Callback de error"""
        print(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Callback cuando se cierra la conexión"""
        print(f"WebSocket cerrado: {close_status_code} - {close_msg}")
    
    def subscribe(self, channel: str, products: List[str]):
        """Suscribe a un canal"""
        if not self.ws or not self.running:
            self.subscriptions[channel] = products
            return
        
        # Generar JWT para suscripción
        token = self.auth.generate_token()
        
        subscribe_msg = {
            "type": "subscribe",
            "product_ids": products,
            "channels": [channel],
            "jwt": token
        }
        
        self.ws.send(json.dumps(subscribe_msg))
        self.subscriptions[channel] = products
    
    def unsubscribe(self, channel: str, products: List[str]):
        """Desuscribe de un canal"""
        if self.ws and self.running:
            unsubscribe_msg = {
                "type": "unsubscribe",
                "product_ids": products,
                "channels": [channel]
            }
            self.ws.send(json.dumps(unsubscribe_msg))
    
    def register_callback(self, message_type: str, callback):
        """Registra callback para tipo de mensaje específico"""
        self.callbacks[message_type] = callback
    
    def close(self):
        """Cierra la conexión WebSocket"""
        self.running = False
        if self.ws:
            self.ws.close()


# ============================================================
# EJEMPLO DE USO
# ============================================================

def ejemplo_uso():
    """Ejemplo de uso del cliente de futuros"""
    
    # Configuración desde variables de entorno
    API_KEY = os.getenv("COINBASE_API_KEY")
    PRIVATE_KEY = os.getenv("COINBASE_PRIVATE_KEY")
    
    if not API_KEY or not PRIVATE_KEY:
        print("❌ Error: Configure COINBASE_API_KEY y COINBASE_PRIVATE_KEY")
        return
    
    # Crear cliente
    client = CoinbaseFuturesClient(API_KEY, PRIVATE_KEY, sandbox=True)
    
    # Verificar balance
    print("\n📊 Resumen de Balance:")
    balance = client.get_balance_summary()
    print(json.dumps(balance, indent=2))
    
    # Verificar margen
    print("\n💰 Ventana de Margen:")
    print(f"Intradiario: {client.is_margin_intraday()}")
    
    # Obtener posiciones
    print("\n📈 Posiciones:")
    positions = client.get_positions()
    print(json.dumps(positions, indent=2))
    
    # Ratio de margen
    print(f"\n📉 Ratio de Margen: {client.calculate_margin_ratio():.2f}")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import os
    
    print("="*60)
    print("🔐 Coinbase Futures API Client v1.0")
    print("="*60)
    
    # Verificar configuración
    if not os.getenv("COINBASE_API_KEY"):
        print("\n⚠️  Configure las variables de entorno:")
        print("   export COINBASE_API_KEY='su_api_key'")
        print("   export COINBASE_PRIVATE_KEY='su_private_key'")
        print("\n💡 Para sandbox, use sandbox=True al crear el cliente")
    else:
        ejemplo_uso()
