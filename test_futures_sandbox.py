#!/usr/bin/env python3
"""
🧪 Coinbase Futures Sandbox Test Script v1.0

Este script prueba la configuración de la API de Futuros
en modo SANDBOX (pruebas sin dinero real).

Modo Sandbox:
- URL: api-sandbox.coinbase.com
- Sin dinero real - operaciones simuladas
- Respuestas realistas pero ficticias

Uso: python3 test_futures_sandbox.py
"""

import os
import sys
import json
from datetime import datetime

# ============================================================
# CONFIGURACIÓN
# ============================================================

SANDBOX_URL = "https://api-sandbox.coinbase.com"
PRODUCTION_URL = "https://api.coinbase.com"

# Verificar .env
def load_config():
    """Carga configuración desde .env"""
    config = {}
    
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    
    return config

# ============================================================
# CLASES DE SIMULACIÓN (SANDBOX)
# ============================================================

class SandboxFuturesClient:
    """
    Cliente de simulación para testing en Sandbox.
    Genera respuestas realistas sin necesidad de API keys.
    """
    
    def __init__(self, sandbox=True):
        self.sandbox = sandbox
        self.url = SANDBOX_URL if sandbox else PRODUCTION_URL
        self.positions = []
        self.orders = []
        
        # Datos simulados realistas
        self.simulated_balance = {
            "available_balance": {"value": "100000.00", "currency": "USD"},
            "total_balance": {"value": "100000.00", "currency": "USD"},
            "initial_margin_required": {"value": "5000.00", "currency": "USD"},
            "maintenance_margin_required": {"value": "2500.00", "currency": "USD"}
        }
        
        self.simulated_positions = [
            {
                "product_id": "BTC-USD",
                "size": "5",
                "side": "long",
                "average_entry_price": {"value": "100000.00"},
                "mark_price": {"value": "102500.00"},
                "unrealized_pnl": {"value": "12500.00"},
                "liquidation_price": {"value": "85000.00"}
            }
        ]
        
        print(f"\n{'='*60}")
        print(f"🧪 MODO SANDBOX: {'ACTIVADO' if sandbox else 'DESACTIVADO'}")
        print(f"{'='*60}")
        print(f"URL: {self.url}")
        print(f"Balance simulado: ${self.simulated_balance['available_balance']['value']}")
        print(f"Posiciones simuladas: {len(self.simulated_positions)}")
    
    def get_balance_summary(self):
        """Simula consulta de balance"""
        print("\n📊 [SANDBOX] Consultando balance...")
        
        response = {
            "type": "futures_balance_summary",
            "time": datetime.now().isoformat(),
            "available_balance": self.simulated_balance["available_balance"],
            "total_balance": self.simulated_balance["total_balance"],
            "initial_margin_required": self.simulated_balance["initial_margin_required"],
            "maintenance_margin_required": self.simulated_balance["maintenance_margin_required"],
            "margin_ratio": round(100000 / 5000, 2),
            "status": "active"
        }
        
        print(f"   ✅ Balance: ${response['available_balance']['value']}")
        print(f"   ✅ Ratio de margen: {response['margin_ratio']}")
        
        return response
    
    def get_positions(self):
        """Simula consulta de posiciones"""
        print("\n📈 [SANDBOX] Consultando posiciones...")
        
        response = {
            "type": "futures_positions",
            "time": datetime.now().isoformat(),
            "positions": self.simulated_positions
        }
        
        for pos in self.simulated_positions:
            size = pos["size"]
            side = pos["side"]
            entry = pos["average_entry_price"]["value"]
            mark = pos["mark_price"]["value"]
            pnl = pos["unrealized_pnl"]["value"]
            
            print(f"   ✅ {pos['product_id']}: {side.upper()} {size} contratos")
            print(f"      Entry: ${entry} | Mark: ${mark} | PnL: ${pnl}")
        
        return response
    
    def place_order(self, product_id, side, order_type, size, price=None):
        """Simula colocación de orden"""
        print(f"\n🚀 [SANDBOX] Colocando orden...")
        print(f"   Producto: {product_id}")
        print(f"   Side: {side.upper()}")
        print(f"   Tipo: {order_type.upper()}")
        print(f"   Tamaño: {size} contratos")
        if price:
            print(f"   Precio: ${price}")
        
        # Generar respuesta simulada
        order_id = f"SANDBOX_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        response = {
            "type": "order",
            "order_id": order_id,
            "product_id": product_id,
            "side": side.upper(),
            "order_type": order_type.upper(),
            "size": str(size),
            "price": str(price) if price else None,
            "status": "filled",
            "filled_at": datetime.now().isoformat(),
            "fill_price": price or 102500.00,
            "message": "[SANDBOX] Orden ejecutada exitosamente (simulada)"
        }
        
        print(f"   ✅ Orden ID: {order_id}")
        print(f"   ✅ Estado: {response['status']}")
        
        self.orders.append(response)
        
        return response
    
    def calculate_margin_ratio(self):
        """Calcula ratio de margen simulado"""
        available = float(self.simulated_balance["available_balance"]["value"])
        required = float(self.simulated_balance["initial_margin_required"]["value"])
        return round(available / required, 2)
    
    def get_margin_window(self):
        """Simula consulta de ventana de margen"""
        hour = datetime.now().hour
        
        if 8 <= hour < 16:  # 8 AM - 4 PM ET
            window = "intraday"
        else:
            window = "overnight"
        
        return {
            "margin_window": window,
            "message": f"[SANDBOX] Ventana de margen: {window}"
        }
    
    def simulate_trading_day(self):
        """Simula un día completo de trading"""
        print(f"\n{'='*60}")
        print(f"📅 SIMULACIÓN DE DÍA DE TRADING")
        print(f"{'='*60}")
        
        # 1. Verificar balance
        balance = self.get_balance_summary()
        
        # 2. Verificar posiciones
        positions = self.get_positions()
        
        # 3. Verificar ventana de margen
        margin = self.get_margin_window()
        print(f"\n   💡 Ventana de margen: {margin['margin_window']}")
        
        # 4. Calcular ratio
        ratio = self.calculate_margin_ratio()
        print(f"\n   📊 Ratio de margen: {ratio}")
        
        if ratio >= 1.5:
            print("   ✅ Salud de cuenta: Excelente")
        elif ratio >= 1.2:
            print("   ⚡ Salud de cuenta: Buena")
        elif ratio >= 1.0:
            print("   ⚠️ Salud de cuenta: Aceptable")
        else:
            print("   🚨 ALERTA: Riesgo de liquidación!")
        
        # 5. Simular algunas órdenes
        print(f"\n{'='*60}")
        print(f"📝 SIMULANDO ÓRDENES DE EJEMPLO")
        print(f"{'='*60}")
        
        # Orden de ejemplo 1: Compra de Nano Bitcoin
        self.place_order(
            product_id="BIT-USD",
            side="BUY",
            order_type="limit",
            size=10,
            price=101000.00
        )
        
        # Orden de ejemplo 2: Venta de Nano Ether
        self.place_order(
            product_id="ETP-USD",
            side="SELL",
            order_type="market",
            size=20
        )
        
        # Resumen final
        print(f"\n{'='*60}")
        print(f"📋 RESUMEN DE SIMULACIÓN")
        print(f"{'='*60}")
        print(f"   Órdenes ejecutadas: {len(self.orders)}")
        print(f"   Balance disponible: ${balance['available_balance']['value']}")
        print(f"   Ratio de margen: {ratio}")
        print(f"\n   💡 Nota: Esta es una simulación.")
        print(f"      Para trading real, necesitas configurar")
        print(f"      COINBASE_SANDBOX=false y tu Private Key real.")
        print(f"{'='*60}")


# ============================================================
# PRUEBA DE INTEGRACIÓN CON CLIENTE REAL
# ============================================================

def test_real_client():
    """Prueba el cliente real si hay credenciales"""
    print("\n" + "="*60)
    print("🔐 PRUEBA DE CLIENTE REAL")
    print("="*60)
    
    config = load_config()
    
    api_key = config.get('COINBASE_API_KEY', os.getenv('COINBASE_API_KEY'))
    private_key = config.get('COINBASE_PRIVATE_KEY', os.getenv('COINBASE_PRIVATE_KEY'))
    sandbox = config.get('COINBASE_SANDBOX', os.getenv('COINBASE_SANDBOX', 'true'))
    
    print(f"\n📋 Configuración detectada:")
    print(f"   API Key: {api_key[:8] if api_key else 'No configurada'}...")
    print(f"   Private Key: {'Configurada' if private_key and private_key != 'tu_private_key_aqui' else 'No configurada'}")
    print(f"   Sandbox: {sandbox}")
    
    if api_key and private_key and private_key != 'tu_private_key_aqui':
        print(f"\n   ✅ Credenciales detectadas!")
        print(f"   🚀 Probando conexión con cliente real...")
        
        try:
            from coinbase_futures_client import CoinbaseFuturesClient
            client = CoinbaseFuturesClient(
                api_key=api_key,
                private_key=private_key,
                sandbox=(sandbox.lower() == 'true')
            )
            
            # Probar conexión
            balance = client.get_balance_summary()
            print(f"   ✅ Conexión exitosa!")
            print(f"   💰 Balance: {balance}")
            
            return True
            
        except ImportError as e:
            print(f"   ⚠️  Error importando cliente: {e}")
            print(f"   📦 Instala dependencias: pip install requests cryptography")
            return False
        except Exception as e:
            print(f"   ❌ Error conectando: {e}")
            return False
    else:
        print(f"\n   ⚠️  Credenciales incompletas.")
        print(f"   📝 Para usar cliente real, configura:")
        print(f"   1. COINBASE_API_KEY=069e2e6b-537d-463d-a42f-470e36eb94ed")
        print(f"   2. COINBASE_PRIVATE_KEY=tu_clave_privada_pem")
        return False


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "="*60)
    print("🧪 COINBASE FUTURES SANDBOX TEST")
    print("="*60)
    print()
    print("Este script simula operaciones de futuros sin dinero real.")
    print("Para pruebas, usa datos realistas pero ficticios.")
    print()
    
    # Cargar configuración
    config = load_config()
    sandbox_mode = config.get('COINBASE_SANDBOX', 'true')
    
    # Crear cliente sandbox
    client = SandboxFuturesClient(sandbox=(sandbox_mode.lower() == 'true'))
    
    # Ejecutar simulación de día de trading
    client.simulate_trading_day()
    
    # Intentar probar cliente real
    print("\n" + "="*60)
    print("🔍 PRUEBA ADICIONAL: CLIENTE REAL")
    print("="*60)
    test_real_client()
    
    print("\n" + "="*60)
    print("💡 PARA CONFIGURAR CLIENTE REAL:")
    print("="*60)
    print("""
    1. Obtén tu Private Key de:
       https://portal.coinbase.com/portal/api-keys
    
    2. Edita el archivo .env:
       COINBASE_API_KEY=069e2e6b-537d-463d-a42f-470e36eb94ed
       COINBASE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\\nTU_CLAVE\\n-----END PRIVATE KEY-----
       COINBASE_SANDBOX=false
    
    3. Instala dependencias:
       pip install requests cryptography websocket-client
    
    4. Ejecuta:
       python3 coinbase_futures_client.py
    """)
    
    return 0

if __name__ == "__main__":
    exit(main())
