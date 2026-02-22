#!/usr/bin/env python3
"""
🚀 Coinbase Advanced Trade - Futuros Trader v2.1
==================================================

Cliente completo para operar futuros en Coinbase Advanced Trade.

Características:
- ✨ Autenticación JWT Ed25519
- 📈 Apalancamiento hasta 10x
- 🔻 Short Selling (venta en corto)
- 💰 Gestión de márgenes
- 📊 Precios en tiempo real
- 🎯 Órdenes: Market, Limit

Uso:
    from coinbase_advanced_trader import CoinbaseAdvancedTrader
    
    trader = CoinbaseAdvancedTrader()
    
    # Consultar precio de contrato
    price = trader.get_ticker("BIT-27FEB26-CDE")
    
    # Consultar balance de futuros
    balance = trader.get_balance()
    
    # Abrir posición larga con apalancamiento
    trader.open_position("BIT-27FEB26-CDE", "long", 1, leverage=5)
    
    # Abrir posición corta (short)
    trader.open_position("BIT-27FEB26-CDE", "short", 1, leverage=3)
    
    # Cerrar posición
    trader.close_position("BIT-27FEB26-CDE")
"""

import os
import json
import time
import base64
import requests
import threading
from typing import Optional, Dict, List, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# ============================================================

# =========================================================# CONFIGURACIÓN===

DEFAULT_KEY_PATH = "/Users/enderj/Downloads/cdp_api_key.json"
PROJECT_KEY_PATH = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/cdp_api_key.json"

API_URL = "https://api.coinbase.com"
SANDBOX_URL = "https://api-sandbox.coinbase.com"

class Endpoints:
    # Autenticados
    ACCOUNTS = "/api/v3/brokerage/accounts"
    CFM_BALANCE = "/api/v3/brokerage/cfm/balance_summary"
    CFM_POSITIONS = "/api/v3/brokerage/cfm/positions"
    CFM_OPEN_ORDERS = "/api/v3/brokerage/cfm/orders/open"
    ORDERS = "/api/v3/brokerage/orders"
    PRODUCTS = "/api/v3/brokerage/products"
    
    # Públicos (sin auth)
    MARKET_PRODUCTS = "/api/v3/brokerage/market/products"
    TICKER = "/api/v3/brokerage/market/products/{product_id}/ticker"
    BEST_BID_ASK = "/api/v3/brokerage/market/best_bid_ask"


class PositionSide(Enum):
    LONG = "long"
    SHORT = "short"


# ============================================================
# AUTENTICACIÓN
# ============================================================

def load_coinbase_key(key_path: str = None) -> tuple:
    """Carga credenciales desde archivo JSON."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    
    if key_path is None:
        for path in [DEFAULT_KEY_PATH, PROJECT_KEY_PATH]:
            if os.path.exists(path):
                key_path = path
                break
        else:
            raise FileNotFoundError("No se encontró archivo de credenciales")
    
    with open(key_path, 'r') as f:
        data = json.load(f)
    
    raw = base64.b64decode(data["privateKey"])
    private_key = Ed25519PrivateKey.from_private_bytes(raw[:32])
    
    return data["id"], private_key


def make_jwt(key_id: str, private_key, method: str, path: str, sandbox: bool = False) -> str:
    """Genera JWT para Coinbase API."""
    now = int(time.time())
    
    def b64url(d):
        if isinstance(d, str):
            d = d.encode()
        return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
    
    header = b64url(json.dumps({
        "alg": "EdDSA",
        "kid": key_id,
        "typ": "JWT"
    }, separators=(",", ":")))
    
    base_url = "api.sandbox.coinbase.com" if sandbox else "api.coinbase.com"
    payload = b64url(json.dumps({
        "iss": "cdp",
        "nbf": now,
        "exp": now + 120,
        "sub": key_id,
        "uri": f"{method} {base_url}{path}"
    }, separators=(",", ":")))
    
    msg = f"{header}.{payload}"
    signature = b64url(private_key.sign(msg.encode()))
    
    return f"{msg}.{signature}"


# ============================================================
# CLIENTE PRINCIPAL
# ============================================================

class CoinbaseAdvancedTrader:
    """
    Cliente para operar futuros en Coinbase Advanced Trade.
    
    Uso:
        trader = CoinbaseAdvancedTrader()
        
        # Precio de contrato
        price = trader.get_ticker("BIT-27FEB26-CDE")
        
        # Abrir posición
        trader.open_position("BIT-27FEB26-CDE", "long", 1, leverage=5)
    """
    
    def __init__(self, key_path: str = None, sandbox: bool = False):
        self.sandbox = sandbox
        self.base_url = SANDBOX_URL if sandbox else API_URL
        self.key_id, self.private_key = load_coinbase_key(key_path)
        
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        self.last_request = 0
        self.min_interval = 1.0 / 10
        
        print(f"🚀 Coinbase Advanced Trader v2.1")
        print(f"   📡 Modo: {'SANDBOX' if sandbox else 'PRODUCTION'}")
        print(f"   🔑 Key: {self.key_id[:8]}...")
    
    def _request(self, method: str, endpoint: str, data: dict = None, 
                 params: dict = None, auth: bool = True) -> dict:
        """Solicitud a la API."""
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()
        
        headers = {}
        if auth:
            token = make_jwt(self.key_id, self.private_key, method, endpoint, self.sandbox)
            headers = {"Authorization": f"Bearer {token}"}
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, params=params, timeout=30)
            elif method == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=30)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Método no soportado: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    # ==================== CONSULTAS PÚBLICAS ====================
    
    def get_products(self, product_type: str = "FUTURE", limit: int = 100) -> dict:
        """
        Obtiene productos públicos (futuros, spot, etc).
        
        Args:
            product_type: "FUTURE", "SPOT", "PERPETUAL"
            limit: Máximo de resultados
            
        Returns:
            dict: Lista de productos
        """
        params = {"product_type": product_type, "limit": limit}
        return self._request("GET", Endpoints.MARKET_PRODUCTS, 
                           params=params, auth=False)
    
    def get_ticker(self, product_id: str) -> dict:
        """
        Obtiene precio actual de un producto (público).
        
        Args:
            product_id: Ej: "BIT-27FEB26-CDE", "BTC-USD"
            
        Returns:
            dict: Precio, trades recientes
        """
        endpoint = Endpoints.TICKER.format(product_id=product_id)
        return self._request("GET", endpoint, auth=False)
    
    def get_best_bid_ask(self, product_ids: List[str]) -> dict:
        """Mejor precio bid/ask para productos."""
        params = {"product_ids": product_ids}
        return self._request("GET", Endpoints.BEST_BID_ASK, 
                           params=params, auth=False)
    
    def get_futures_contracts(self, asset: str = None) -> List[dict]:
        """
        Lista contratos de futuros.
        
        Args:
            asset: Filtrar por activo (BTC, ETH, SOL)
            
        Returns:
            List[dict]: Contratos disponibles
        """
        products = self.get_products("FUTURE", 200)
        
        if "error" in products:
            return []
        
        contracts = products.get("products", [])
        
        if asset:
            contracts = [c for c in contracts 
                       if c.get("product_id", "").startswith(asset.upper())]
        
        return contracts
    
    # ==================== CONSULTAS AUTENTICADAS ====================
    
    def get_balance(self) -> dict:
        """Balance de cuenta de futuros CFM."""
        return self._request("GET", Endpoints.CFM_BALANCE)
    
    def get_accounts(self) -> dict:
        """Todas las cuentas/wallets."""
        return self._request("GET", Endpoints.ACCOUNTS)
    
    def get_positions(self) -> dict:
        """Posiciones abiertas de futuros."""
        return self._request("GET", Endpoints.CFM_POSITIONS)
    
    def get_open_orders(self) -> dict:
        """Órdenes abiertas."""
        return self._request("GET", Endpoints.CFM_OPEN_ORDERS)
    
    # ==================== ÓRDENES ====================
    
    def place_order(self,
                   product_id: str,
                   side: str,
                   order_type: str = "market",
                   size: float = 1,
                   price: float = None,
                   time_in_force: str = "GTT",
                   leverage: int = 1,
                   reduce_only: bool = False) -> dict:
        """
        Coloca una orden de futuros.
        
        Args:
            product_id: ID del contrato
            side: "BUY" o "SELL"
            order_type: "market" o "limit"
            size: Número de contratos
            price: Precio límite
            time_in_force: "GTC", "IOC", "FOK", "GTT"
            leverage: Apalancamiento (1-10)
            reduce_only: Solo reducir posición
            
        Returns:
            dict: Resultado de la orden
        """
        order_config = {
            "product_id": product_id,
            "side": side.upper(),
            "order_configuration": {},
            "reduce_only": reduce_only
        }
        
        if order_type.lower() == "market":
            order_config["order_configuration"]["market_order"] = {
                "size": str(size),
                "time_in_force": time_in_force
            }
        elif order_type.lower() == "limit":
            order_config["order_configuration"]["limit_order"] = {
                "size": str(size),
                "limit_price": str(price),
                "time_in_force": time_in_force
            }
        
        if leverage > 1:
            order_config["leverage"] = str(leverage)
        
        return self._request("POST", Endpoints.ORDERS, data=order_config)
    
    def open_position(self,
                     product_id: str,
                     position_side: str,
                     size: float,
                     leverage: int = 1,
                     order_type: str = "market",
                     price: float = None) -> dict:
        """
        Abre posición larga o corta.
        
        Args:
            product_id: ID del contrato
            position_side: "long" o "short"
            size: Contratos
            leverage: Apalancamiento
            order_type: "market" o "limit"
            price: Precio límite
            
        Returns:
            dict: Resultado
        """
        side = "BUY" if position_side.lower() == "long" else "SELL"
        
        return self.place_order(
            product_id=product_id,
            side=side,
            order_type=order_type,
            size=size,
            price=price,
            leverage=leverage,
            reduce_only=False
        )
    
    def close_position(self, product_id: str, size: float = None) -> dict:
        """
        Cierra posición existente.
        
        Args:
            product_id: ID del contrato
            size: Contratos a cerrar (None = todo)
            
        Returns:
            dict: Resultado
        """
        positions = self.get_positions()
        
        current_side = None
        current_size = 0
        
        if "positions" in positions:
            for pos in positions["positions"]:
                if pos.get("product_id") == product_id:
                    current_side = pos.get("side", "")
                    current_size = int(pos.get("size", 0))
                    break
        
        if current_side is None:
            return {"error": "No hay posición abierta"}
        
        side = "SELL" if current_side == "long" else "BUY"
        close_size = size if size else current_size
        
        return self.place_order(
            product_id=product_id,
            side=side,
            order_type="market",
            size=close_size,
            reduce_only=True
        )
    
    def cancel_order(self, order_id: str) -> dict:
        """Cancela una orden."""
        return self._request("DELETE", f"{Endpoints.ORDERS}/{order_id}")
    
    # ==================== HELPERS ====================
    
    def get_margin_info(self) -> dict:
        """Información de margen."""
        balance = self.get_balance()
        
        if "error" in balance:
            return balance
        
        try:
            summary = balance.get("balance_summary", {})
            available = float(summary.get("available_balance", {}).get("value", 0))
            required = float(summary.get("required_margin_balance", {}).get("value", 1))
            
            margin_ratio = available / required if required > 0 else float('inf')
            
            return {
                "available": available,
                "required": required,
                "ratio": margin_ratio,
                "status": "healthy" if margin_ratio >= 1.5 else "warning" if margin_ratio >= 1.0 else "danger"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_position_summary(self) -> dict:
        """Resumen de posiciones."""
        positions = self.get_positions()
        
        if "error" in positions:
            return positions
        
        pos_list = positions.get("positions", [])
        
        summary = {
            "count": len(pos_list),
            "long_pnl": 0.0,
            "short_pnl": 0.0,
            "total_pnl": 0.0,
            "positions": []
        }
        
        for pos in pos_list:
            side = pos.get("side", "")
            pnl = float(pos.get("unrealized_pnl", {}).get("value", 0))
            
            summary["positions"].append({
                "product_id": pos.get("product_id"),
                "side": side,
                "size": pos.get("size"),
                "entry": pos.get("average_entry_price", {}).get("value"),
                "mark": pos.get("mark_price", {}).get("value"),
                "pnl": pnl
            })
            
            if side == "long":
                summary["long_pnl"] += pnl
            else:
                summary["short_pnl"] += pnl
            
            summary["total_pnl"] += pnl
        
        return summary
    
    # ==================== MODO SANDBOX ====================
    
    def set_sandbox_mode(self, sandbox: bool):
        """Cambia modo sandbox/producción."""
        self.sandbox = sandbox
        self.base_url = SANDBOX_URL if sandbox else API_URL


# ============================================================
# EJEMPLO DE USO
# ============================================================

def ejemplo():
    """Ejemplo de uso."""
    import json
    
    print("\n" + "="*60)
    print("🚀 COINBASE ADVANCED TRADER v2.1 - EJEMPLO")
    print("="*60 + "\n")
    
    trader = CoinbaseAdvancedTrader(sandbox=False)
    
    # Contratos BTC
    print("📋 CONTRATOS BTC:")
    contracts = trader.get_futures_contracts("BTC")
    for c in contracts[:3]:
        print(f"   {c.get('product_id')}: ${c.get('price')}")
    
    # Ticker
    print("\n💵 TICKER BIT-27FEB26-CDE:")
    ticker = trader.get_ticker("BIT-27FEB26-CDE")
    trades = ticker.get("trades", [])
    if trades:
        print(f"   Último precio: ${trades[0].get('price')}")
        print(f"   Side: {trades[0].get('side')}")
    
    # Balance
    print("\n📊 BALANCE CFM:")
    balance = trader.get_balance()
    summary = balance.get("balance_summary", {})
    if summary:
        print(f"   Disponible: ${summary.get('available_balance', {}).get('value', 'N/A')}")
        print(f"   Requiere: ${summary.get('required_margin_balance', {}).get('value', 'N/A')}")
    else:
        print("   Sin balance en futuros (null)")
    
    # Posiciones
    print("\n📈 POSICIONES:")
    positions = trader.get_positions()
    pos_list = positions.get("positions", [])
    print(f"   Abiertas: {len(pos_list)}")
    
    # Margen
    print("\n💰 INFO DE MARGEN:")
    margin = trader.get_margin_info()
    print(f"   Ratio: {margin.get('ratio', 'N/A')}")
    print(f"   Estado: {margin.get('status', 'N/A')}")
    
    return 0


if __name__ == "__main__":
    try:
        exit(ejemplo())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)
