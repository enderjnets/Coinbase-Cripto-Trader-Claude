#!/usr/bin/env python3
"""
🎮 Simulador de Trading de Futuros - Con Datos Reales
=====================================================

Simulador que usa precios EN TIEMPO REAL de Coinbase API.
Practica trading con datos reales, sin arriesgar dinero.

Uso:
    python futures_simulator.py
    python futures_simulator.py --interactive
    python futures_simulator.py --open LONG 1 BIT-27FEB26-CDE 5
"""

import os
import sys
import json
import time
import requests
import threading
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, field

# ============================================================
# CONFIGURACIÓN
# ============================================================

API_URL = "https://api.coinbase.com"
DEFAULT_KEY_PATH = "/Users/enderj/Downloads/cdp_api_key.json"
PROJECT_KEY_PATH = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/cdp_api_key.json"


# ============================================================
# AUTENTICACIÓN (para endpoints privados si es necesario)
# ============================================================

def load_coinbase_key(key_path: str = None) -> tuple:
    """Carga credenciales de Coinbase."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    import base64
    import json
    
    if key_path is None:
        for path in [DEFAULT_KEY_PATH, PROJECT_KEY_PATH]:
            if os.path.exists(path):
                key_path = path
                break
        else:
            # Usar valores por defecto si no hay archivo
            return None, None
    
    try:
        with open(key_path, 'r') as f:
            data = json.load(f)
        
        raw = base64.b64decode(data["privateKey"])
        private_key = Ed25519PrivateKey.from_private_bytes(raw[:32])
        
        return data["id"], private_key
    except:
        return None, None


def make_jwt(key_id, private_key, method: str, path: str) -> str:
    """Genera JWT para Coinbase."""
    import base64
    import json
    
    if not key_id or not private_key:
        return None
    
    now = int(time.time())
    
    def b64url(d):
        if isinstance(d, str):
            d = d.encode()
        return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
    
    header = b64url(json.dumps({"alg": "EdDSA", "kid": key_id, "typ": "JWT"}, separators=(",", ":")))
    
    payload = b64url(json.dumps({
        "iss": "cdp",
        "nbf": now,
        "exp": now + 120,
        "sub": key_id,
        "uri": f"{method} api.coinbase.com{path}"
    }, separators=(",", ":")))
    
    msg = f"{header}.{payload}"
    signature = b64url(private_key.sign(msg.encode()))
    
    return f"{msg}.{signature}"


# ============================================================
# PRECIOS REALES
# ============================================================

class PriceFetcher:
    """Obtiene precios en tiempo real de Coinbase."""
    
    def __init__(self):
        self.key_id, self.private_key = load_coinbase_key()
        self.prices_cache = {}
        self.last_update = {}
        self.cache_ttl = 5  # segundos
        
        # Productos a monitorear
        self.products = [
            # Bitcoin
            "BIT-27FEB26-CDE", "BIT-27MAR26-CDE", "BIT-24APR26-CDE", "BIP-20DEC30-CDE",
            # Ethereum  
            "ET-27FEB26-CDE", "ET-27MAR26-CDE", "ET-24APR26-CDE", "ETP-20DEC30-CDE",
            # Solana
            "SOL-27FEB26-CDE", "SOL-27MAR26-CDE", "SLP-20DEC30-CDE", "SLR-25FEB26-CDE",
            # XRP
            "XRP-27FEB26-CDE", "XPP-20DEC30-CDE",
            # Materias primas
            "GOL-27MAR26-CDE", "NOL-19MAR26-CDE", "NGS-24FEB26-CDE", "CU-25FEB26-CDE",
            "PT-27MAR26-CDE", "MC-19MAR26-CDE",
            # Spot para referencia
            "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"
        ]
        
        # Inicializar precios
        self._fetch_all_prices()
    
    def _fetch_all_prices(self):
        """Obtiene todos los precios de una vez."""
        # Obtener lista de productos públicos
        try:
            url = f"{API_URL}/api/v3/brokerage/market/products"
            params = {"product_type": "FUTURE", "limit": 100}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for product in data.get("products", []):
                    pid = product.get("product_id")
                    price = product.get("price")
                    
                    if pid and price:
                        try:
                            self.prices_cache[pid] = float(price)
                            self.last_update[pid] = time.time()
                        except:
                            pass
        except Exception as e:
            print(f"⚠️ Error obteniendo productos: {e}")
        
        # Obtener precios spot
        spot_products = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"]
        for pid in spot_products:
            try:
                url = f"{API_URL}/api/v3/brokerage/products/{pid}/ticker"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    trades = data.get("trades", [])
                    if trades:
                        self.prices_cache[pid] = float(trades[0].get("price", 0))
                        self.last_update[pid] = time.time()
            except:
                pass
    
    def get_price(self, product_id: str, force_update: bool = False) -> float:
        """
        Obtiene precio de un producto.
        
        Args:
            product_id: ID del contrato
            force_update: Forzar actualización
            
        Returns:
            float: Precio actual
        """
        # Verificar cache
        if not force_update and product_id in self.prices_cache:
            cache_age = time.time() - self.last_update.get(product_id, 0)
            if cache_age < self.cache_ttl:
                return self.prices_cache[product_id]
        
        # Actualizar precio específico
        try:
            url = f"{API_URL}/api/v3/brokerage/market/products/{product_id}/ticker"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                trades = data.get("trades", [])
                if trades:
                    price = float(trades[0].get("price", 0))
                    if price > 0:
                        self.prices_cache[product_id] = price
                        self.last_update[product_id] = time.time()
                        return price
        except:
            pass
        
        # Devolver cache si falla
        return self.prices_cache.get(product_id, 0)
    
    def get_all_prices(self) -> dict:
        """Obtiene todos los precios."""
        self._fetch_all_prices()
        return self.prices_cache.copy()
    
    def get_ticker(self, product_id: str) -> dict:
        """Obtiene información de ticker."""
        price = self.get_price(product_id)
        
        # Calcular bid/ask
        spread = price * 0.0005 if price > 0 else 0
        
        return {
            "product_id": product_id,
            "price": price,
            "best_bid": price - spread if price > 0 else 0,
            "best_ask": price + spread if price > 0 else 0,
            "last_update": datetime.now().isoformat()
        }
    
    def list_contracts(self, asset: str = None) -> List[dict]:
        """Lista contratos disponibles."""
        contracts = []
        
        for product_id, price in self.prices_cache.items():
            if asset and not product_id.startswith(asset.upper()):
                continue
            
            # Determinar tipo
            if product_id in ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"]:
                continue  # Skip spot
            
            contracts.append({
                "product_id": product_id,
                "price": price,
                "type": "future"
            })
        
        return contracts
    
    def start_live_updates(self, callback, interval: float = 5.0):
        """Inicia actualizaciones en vivo en background."""
        def update_loop():
            while True:
                try:
                    self._fetch_all_prices()
                    callback(self.prices_cache)
                except:
                    pass
                time.sleep(interval)
        
        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()
        
        return thread


# ============================================================
# SIMULADOR
# ============================================================

CONTRACT_SIZES = {
    "BIT": 0.01,      # Nano Bitcoin
    "BIP": 0.01,     # Perpetuo
    "ET": 0.10,      # Nano Ether
    "ETP": 0.10,     # Perpetuo
    "SOL": 5.0,      # Nano Solana
    "SLP": 5.0,      # Perpetuo
    "SLR": 5.0,      # Perpetuo
    "XRP": 500.0,    # Nano XRP
    "XPP": 500.0,    # Perpetuo
    "GOL": 1.0,      # Oro
    "NOL": 100.0,    # Petróleo
    "NGS": 1000.0,   # Gas natural
    "CU": 100.0,     # Cobre
    "PT": 10.0,      # Platino
    "MC": 1.0,       # Micro S&P
}


@dataclass
class Position:
    product_id: str
    side: str
    size: int
    entry_price: float
    leverage: int
    opened_at: str
    
    def unrealized_pnl(self, current_price: float) -> float:
        if self.side == "long":
            pnl = (current_price - self.entry_price) * self.size * CONTRACT_SIZES.get(
                self.product_id.split("-")[0], 1
            )
        else:
            pnl = (self.entry_price - current_price) * self.size * CONTRACT_SIZES.get(
                self.product_id.split("-")[0], 1
            )
        
        return pnl * self.leverage


@dataclass
class Order:
    order_id: str
    product_id: str
    side: str
    order_type: str
    size: int
    price: Optional[float]
    leverage: int
    status: str
    filled_at: Optional[float] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class FuturesSimulator:
    """
    Simulador de trading con datos reales.
    
    Uso:
        sim = FuturesSimulator()
        sim.open_position("BIT-27FEB26-CDE", "long", 1, 5)
        sim.get_balance()
    """
    
    def __init__(self, initial_balance: float = 100000.0, use_live_prices: bool = True):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.order_count = 0
        self.trade_history = []
        
        # Obtener precios reales
        self.price_fetcher = PriceFetcher() if use_live_prices else None
        
        print(f"\n{'='*60}")
        print(f"🎮 SIMULADOR DE FUTUROS - DATOS REALES")
        print(f"{'='*60}")
        print(f"   💰 Balance inicial: ${initial_balance:,.2f}")
        print(f"   📡 Precios: {'EN TIEMPO REAL' if use_live_prices else 'ESTÁTICOS'}")
        print(f"   🕐 Iniciado: {datetime.now().strftime('%H:%M:%S')}")
        
        # Mostrar precios actuales
        if use_live_prices:
            print(f"\n📊 PRECIOS ACTUALES:")
            for prefix in ["BIT", "BIP", "ETP", "SLP"]:
                price = self.price_fetcher.get_price(f"{prefix}-20DEC30-CDE")
                if price:
                    print(f"   {prefix}: ${price:,.2f}")
        
        print(f"{'='*60}\n")
    
    def get_price(self, product_id: str) -> float:
        """Obtiene precio actual."""
        if self.price_fetcher:
            return self.price_fetcher.get_price(product_id)
        return 0.0
    
    def get_ticker(self, product_id: str) -> dict:
        """Obtiene ticker."""
        if self.price_fetcher:
            return self.price_fetcher.get_ticker(product_id)
        return {"product_id": product_id, "price": 0, "best_bid": 0, "best_ask": 0}
    
    def calculate_margin(self, product_id: str, size: int, leverage: int) -> float:
        """Calcula margen requerido."""
        price = self.get_price(product_id)
        if price == 0:
            price = 1000  # Default
        
        prefix = product_id.split("-")[0]
        contract_size = CONTRACT_SIZES.get(prefix, 1)
        
        margin = (price * contract_size * size) / leverage
        return margin
    
    def open_position(self,
                     product_id: str,
                     side: str,
                     size: int,
                     leverage: int = 1,
                     order_type: str = "market") -> dict:
        """Abre una posición."""
        self.order_count += 1
        order_id = f"SIM_{self.order_count:06d}"
        
        entry_price = self.get_price(product_id)
        
        if entry_price == 0:
            return {
                "success": False,
                "error": f"No se pudo obtener precio para {product_id}"
            }
        
        required_margin = self.calculate_margin(product_id, size, leverage)
        
        if required_margin > self.balance:
            return {
                "success": False,
                "error": f"Margen insuficiente. Requiere: ${required_margin:.2f}, Disponible: ${self.balance:.2f}"
            }
        
        if leverage > 10:
            return {"success": False, "error": "Apalancamiento máximo: 10x"}
        
        position = Position(
            product_id=product_id,
            side=side,
            size=size,
            entry_price=entry_price,
            leverage=leverage,
            opened_at=datetime.now().isoformat()
        )
        
        self.balance -= required_margin
        self.positions[product_id] = position
        
        order = Order(
            order_id=order_id,
            product_id=product_id,
            side=side,
            order_type=order_type,
            size=size,
            price=entry_price,
            leverage=leverage,
            status="filled",
            filled_at=entry_price
        )
        self.orders.append(order)
        
        side_emoji = "🟢" if side == "long" else "🔴"
        action = "COMPRADO" if side == "long" else "VENDIDO"
        
        print(f"\n{side_emoji} ORDEN EJECUTADA:")
        print(f"   Producto: {product_id}")
        print(f"   {action}: {size} contrato(s) {side}")
        print(f"   Precio: ${entry_price:,.2f}")
        print(f"   Apalancamiento: {leverage}x")
        print(f"   Margen usado: ${required_margin:,.2f}")
        
        prefix = product_id.split("-")[0]
        contract_size = CONTRACT_SIZES.get(prefix, 1)
        total_value = entry_price * contract_size * size * leverage
        print(f"   Valor total: ${total_value:,.2f}")
        
        return {
            "success": True,
            "order_id": order_id,
            "product_id": product_id,
            "side": side,
            "size": size,
            "entry_price": entry_price,
            "leverage": leverage,
            "margin_used": required_margin,
            "total_value": total_value
        }
    
    def close_position(self, product_id: str, size: int = None) -> dict:
        """Cierra una posición."""
        if product_id not in self.positions:
            return {"success": False, "error": "No hay posición abierta"}
        
        position = self.positions[product_id]
        
        close_size = size if size else position.size
        
        if close_size > position.size:
            return {"success": False, "error": f"Tamaño excedido. Posición: {position.size}"}
        
        current_price = self.get_price(product_id)
        pnl = position.unrealized_pnl(current_price)
        
        margin_released = self.calculate_margin(
            product_id, close_size, position.leverage
        )
        
        if close_size == position.size:
            del self.positions[product_id]
        else:
            position.size -= close_size
        
        self.balance += margin_released + pnl
        
        side_emoji = "🔴" if position.side == "long" else "🟢"
        
        print(f"\n{side_emoji} POSICIÓN CERRADA:")
        print(f"   Producto: {product_id}")
        print(f"   Tamaño: {close_size}")
        print(f"   Entry: ${position.entry_price:,.2f}")
        print(f"   Exit: ${current_price:,.2f}")
        print(f"   PnL: ${pnl:,.2f}")
        print(f"   Margen liberado: ${margin_released:,.2f}")
        
        return {
            "success": True,
            "product_id": product_id,
            "closed_size": close_size,
            "entry_price": position.entry_price,
            "exit_price": current_price,
            "pnl": pnl,
            "margin_released": margin_released
        }
    
    def get_balance(self) -> dict:
        """Obtiene balance."""
        total_margin = sum(
            self.calculate_margin(p.product_id, p.size, p.leverage)
            for p in self.positions.values()
        )
        
        unrealized_pnl = sum(
            p.unrealized_pnl(self.get_price(p.product_id))
            for p in self.positions.values()
        )
        
        return {
            "available_balance": self.balance,
            "margin_used": total_margin,
            "unrealized_pnl": unrealized_pnl,
            "equity": self.balance + total_margin + unrealized_pnl
        }
    
    def get_positions(self) -> dict:
        """Obtiene posiciones."""
        positions = []
        
        for product_id, position in self.positions.items():
            current_price = self.get_price(product_id)
            unrealized_pnl = position.unrealized_pnl(current_price)
            
            positions.append({
                "product_id": product_id,
                "side": position.side,
                "size": position.size,
                "entry_price": position.entry_price,
                "current_price": current_price,
                "leverage": position.leverage,
                "unrealized_pnl": unrealized_pnl,
                "margin": self.calculate_margin(product_id, position.size, position.leverage)
            })
        
        return {"positions": positions}
    
    def get_position_summary(self) -> dict:
        """Resumen de posiciones."""
        positions = self.get_positions()["positions"]
        
        long_pnl = sum(p["unrealized_pnl"] for p in positions if p["side"] == "long")
        short_pnl = sum(p["unrealized_pnl"] for p in positions if p["side"] == "short")
        
        return {
            "count": len(positions),
            "long_pnl": long_pnl,
            "short_pnl": short_pnl,
            "total_pnl": long_pnl + short_pnl
        }
    
    def list_contracts(self, asset: str = None) -> List[dict]:
        """Lista contratos."""
        if self.price_fetcher:
            return self.price_fetcher.list_contracts(asset)
        return []
    
    def refresh_prices(self):
        """Actualiza precios desde API."""
        if self.price_fetcher:
            self.price_fetcher._fetch_all_prices()
    
    def print_status(self):
        """Imprime estado."""
        self.refresh_prices()
        balance = self.get_balance()
        positions = self.get_positions()["positions"]
        summary = self.get_position_summary()
        
        print("\n" + "="*60)
        print("📊 ESTADO DEL SIMULADOR")
        print("="*60)
        
        print(f"\n💰 BALANCE:")
        print(f"   Disponible: ${balance['available_balance']:,.2f}")
        print(f"   Margen usado: ${balance['margin_used']:,.2f}")
        print(f"   PnL no realizado: ${balance['unrealized_pnl']:,.2f}")
        print(f"   Equity: ${balance['equity']:,.2f}")
        
        print(f"\n📈 POSICIONES ({len(positions)}):")
        if positions:
            for pos in positions:
                side_emoji = "🟢" if pos["side"] == "long" else "🔴"
                print(f"   {side_emoji} {pos['product_id']}: {pos['side']} {pos['size']}")
                print(f"      Entry: ${pos['entry_price']:,.2f} → Current: ${pos['current_price']:,.2f}")
                print(f"      PnL: ${pos['unrealized_pnl']:,.2f} ({pos['leverage']}x)")
        else:
            print("   Sin posiciones")
        
        print(f"\n📊 RESUMEN:")
        print(f"   PnL Largos: ${summary['long_pnl']:,.2f}")
        print(f"   PnL Cortos: ${summary['short_pnl']:,.2f}")
        print(f"   PnL Total: ${summary['total_pnl']:,.2f}")
        
        # PnL total
        total_pnl = balance["equity"] - self.initial_balance
        pnl_percent = (total_pnl / self.initial_balance) * 100
        
        print(f"\n📈 ESTADÍSTICAS:")
        print(f"   Inicio: ${self.initial_balance:,.2f}")
        print(f"   Actual: ${balance['equity']:,.2f}")
        print(f"   PnL: ${total_pnl:,.2f} ({pnl_percent:+.2f}%)")
        print(f"   Trades: {len(self.orders)}")
        
        print("="*60)


# ============================================================
# INTERACTIVE MODE
# ============================================================

def interactive_mode():
    """Modo interactivo."""
    sim = FuturesSimulator()
    
    print("\n🎮 MODO INTERACTIVO:")
    print("   contracts [asset] - Ver contratos")
    print("   price <product>   - Ver precio")
    print("   open <side> <size> <product> [leverage] - Abrir posición")
    print("   close <product>  - Cerrar posición")
    print("   positions        - Ver posiciones")
    print("   status           - Estado completo")
    print("   refresh          - Actualizar precios")
    print("   quit             - Salir\n")
    
    while True:
        try:
            cmd = input(">>> ").strip().lower()
            
            if not cmd or cmd == "quit" or cmd == "exit":
                print("\n👋 Saliendo...")
                sim.print_status()
                break
            
            elif cmd == "help":
                print("\n📋 COMANDOS:")
                print("   contracts [asset] - Ver contratos")
                print("   price <product>  - Ver precio")
                print("   open <side> <size> <product> [leverage]")
                print("   close <product>")
                print("   positions")
                print("   status")
                print("   refresh")
            
            elif cmd == "refresh":
                sim.refresh_prices()
                print("✅ Precios actualizados")
            
            elif cmd == "contracts":
                contracts = sim.list_contracts()
                print(f"\n📋 CONTRATOS ({len(contracts)}):")
                for c in contracts[:15]:
                    print(f"   {c['product_id']}: ${c['price']:,.2f}")
            
            elif cmd.startswith("contracts "):
                asset = cmd.split()[1].upper()
                contracts = sim.list_contracts(asset)
                print(f"\n📋 CONTRATOS {asset}:")
                for c in contracts:
                    print(f"   {c['product_id']}: ${c['price']:,.2f}")
            
            elif cmd.startswith("price "):
                product = cmd.split()[1].upper()
                ticker = sim.get_ticker(product)
                print(f"\n💵 {product}:")
                print(f"   Precio: ${ticker['price']:,.2f}")
                print(f"   Bid: ${ticker['best_bid']:,.2f}")
                print(f"   Ask: ${ticker['best_ask']:,.2f}")
            
            elif cmd == "positions" or cmd == "pos":
                positions = sim.get_positions()["positions"]
                if not positions:
                    print("\n📭 Sin posiciones")
                else:
                    for pos in positions:
                        side = "🟢 LONG" if pos["side"] == "long" else "🔴 SHORT"
                        print(f"\n{side} {pos['product_id']}: {pos['size']}")
                        print(f"   Entry: ${pos['entry_price']:,.2f}")
                        print(f"   Current: ${pos['current_price']:,.2f}")
                        print(f"   PnL: ${pos['unrealized_pnl']:,.2f}")
            
            elif cmd == "status" or cmd == "s":
                sim.print_status()
            
            elif cmd.startswith("open "):
                parts = cmd.split()
                if len(parts) < 4:
                    print("Uso: open <long/short> <size> <product> [leverage]")
                    continue
                
                side = parts[1]
                size = int(parts[2])
                product = parts[3].upper()
                leverage = int(parts[4]) if len(parts) > 4 else 1
                
                result = sim.open_position(product, side, size, leverage)
                if not result["success"]:
                    print(f"❌ Error: {result['error']}")
            
            elif cmd.startswith("close "):
                product = cmd.split()[1].upper()
                result = sim.close_position(product)
                if not result["success"]:
                    print(f"❌ Error: {result['error']}")
            
            else:
                print(f"❓ Comando: '{cmd}' - Escribe 'help'")
        
        except KeyboardInterrupt:
            print("\n👋")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


# ============================================================
# MAIN
# ============================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Simulador de Futuros - Datos Reales")
    parser.add_argument("--balance", type=float, default=100000, help="Balance inicial")
    parser.add_argument("--interactive", "-i", action="store_true", help="Modo interactivo")
    parser.add_argument("--open", nargs=4, metavar=("SIDE", "SIZE", "PRODUCT", "LEVERAGE"),
                       help="Abrir posición")
    parser.add_argument("--close", type=str, help="Cerrar posición")
    parser.add_argument("--positions", action="store_true", help="Ver posiciones")
    parser.add_argument("--contracts", action="store_true", help="Listar contratos")
    parser.add_argument("--price", type=str, help="Ver precio de producto")
    parser.add_argument("--static", action="store_true", help="Usar precios estáticos (no API)")
    
    args = parser.parse_args()
    
    # Crear simulador
    use_live = not args.static
    sim = FuturesSimulator(initial_balance=args.balance, use_live_prices=use_live)
    
    if args.interactive:
        interactive_mode()
    
    elif args.price:
        ticker = sim.get_ticker(args.price.upper())
        print(f"\n💵 {args.price.upper()}:")
        print(f"   Precio: ${ticker['price']:,.2f}")
    
    elif args.contracts:
        contracts = sim.list_contracts()
        print(f"\n📋 CONTRATOS ({len(contracts)}):")
        for c in contracts[:15]:
            print(f"   {c['product_id']}: ${c['price']:,.2f}")
    
    elif args.open:
        side, size, product, leverage = args.open
        size = int(size)
        leverage = int(leverage)
        sim.open_position(product.upper(), side.lower(), size, leverage)
    
    elif args.close:
        sim.close_position(args.close.upper())
    
    elif args.positions:
        positions = sim.get_positions()["positions"]
        print(f"\n📈 POSICIONES: {len(positions)}")
        for pos in positions:
            print(f"   {pos['product_id']}: {pos['side']} {pos['size']} @ ${pos['entry_price']:,.2f}")
    
    else:
        sim.print_status()


if __name__ == "__main__":
    main()
