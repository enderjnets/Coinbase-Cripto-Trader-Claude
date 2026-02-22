#!/usr/bin/env python3
"""
📊 Dashboard de Trading de Futuros - Coinbase Advanced Trade
=============================================================

Panel de control para operar futuros con apalancamiento y shorts.

Uso:
    python futures_dashboard.py
    
Opciones:
    --price BTC     Ver precio de contrato BTC
    --contracts     Listar todos los contratos
    --balance       Ver balance de futuros
    --positions     Ver posiciones abiertas
    --open LONG 1 BIT-27FEB26-CDE 5    Abrir posición
    --close BIT-27FEB26-CDE            Cerrar posición
"""

import sys
import argparse
import json
from coinbase_advanced_trader import CoinbaseAdvancedTrader


def main():
    parser = argparse.ArgumentParser(description="Dashboard de Futuros Coinbase")
    parser.add_argument("--sandbox", action="store_true", help="Usar sandbox")
    parser.add_argument("--price", type=str, help="Ver precio de producto")
    parser.add_argument("--contracts", action="store_true", help="Listar contratos")
    parser.add_argument("--asset", type=str, help="Filtrar contratos por activo")
    parser.add_argument("--balance", action="store_true", help="Ver balance")
    parser.add_argument("--positions", action="store_true", help="Ver posiciones")
    parser.add_argument("--open", nargs=4, metavar=("SIDE", "SIZE", "PRODUCT", "LEVERAGE"),
                       help="Abrir posición: LONG/SHARE SIZE LEVERAGE PRODUCT")
    parser.add_argument("--close", type=str, help="Cerrar posición: PRODUCT")
    parser.add_argument("--orders", action="store_true", help="Ver órdenes abiertas")
    
    args = parser.parse_args()
    
    trader = CoinbaseAdvancedTrader(sandbox=args.sandbox)
    
    # Ver precio
    if args.price:
        print(f"\n💵 Precio de {args.price}:")
        ticker = trader.get_ticker(args.price)
        trades = ticker.get("trades", [])
        if trades:
            t = trades[0]
            print(f"   Precio: ${t.get('price')}")
            print(f"   Tamaño: {t.get('size')}")
            print(f"   Side: {t.get('side')}")
            print(f"   Tiempo: {t.get('time')}")
        else:
            print("   Sin datos de trades")
    
    # Listar contratos
    elif args.contracts:
        print("\n📋 CONTRATOS DE FUTUROS:")
        asset = args.asset if args.asset else None
        contracts = trader.get_futures_contracts(asset)
        
        if asset:
            print(f"   {asset}: {len(contracts)} contratos")
        else:
            print(f"   Total: {len(contracts)} contratos")
        
        # Agrupar por activo
        by_asset = {}
        for c in contracts:
            pid = c.get("product_id", "")
            prefix = pid.split("-")[0]
            if prefix not in by_asset:
                by_asset[prefix] = []
            by_asset[prefix].append(c)
        
        for prefix, list in by_asset.items():
            print(f"\n   {prefix} ({len(list)} contratos):")
            for c in list[:5]:
                print(f"      {c.get('product_id')}: ${c.get('price')}")
    
    # Ver balance
    elif args.balance:
        print("\n📊 BALANCE DE FUTUROS:")
        balance = trader.get_balance()
        summary = balance.get("balance_summary", {})
        
        if summary:
            print(f"   Disponible: ${summary.get('available_balance', {}).get('value', 'N/A')}")
            print(f"   Total: ${summary.get('total_balance', {}).get('value', 'N/A')}")
            print(f"   Margen requerido: ${summary.get('required_margin_balance', {}).get('value', 'N/A')}")
            print(f"   Margen mantenimiento: ${summary.get('maintenance_margin_balance', {}).get('value', 'N/A')}")
        else:
            print("   Sin balance en futuros (null)")
        
        # Info de margen
        margin = trader.get_margin_info()
        print(f"\n   Ratio de margen: {margin.get('ratio', 'N/A')}")
        print(f"   Estado: {margin.get('status', 'N/A')}")
    
    # Ver posiciones
    elif args.positions:
        print("\n📈 POSICIONES ABIERTAS:")
        summary = trader.get_position_summary()
        
        print(f"   Total posiciones: {summary.get('count', 0)}")
        print(f"   PnL largo: ${summary.get('long_pnl', 0):.2f}")
        print(f"   PnL corto: ${summary.get('short_pnl', 0):.2f}")
        print(f"   PnL total: ${summary.get('total_pnl', 0):.2f}")
        
        for pos in summary.get("positions", []):
            print(f"\n   {pos.get('product_id')}:")
            print(f"      Side: {pos.get('side')}")
            print(f"      Tamaño: {pos.get('size')}")
            print(f"      Entry: ${pos.get('entry')}")
            print(f"      Mark: ${pos.get('mark')}")
            print(f"      PnL: ${pos.get('pnl'):.2f}")
    
    # Ver órdenes abiertas
    elif args.orders:
        print("\n📝 ÓRDENES ABIERTAS:")
        orders = trader.get_open_orders()
        order_list = orders.get("orders", [])
        
        if order_list:
            for o in order_list:
                print(f"   {o.get('order_id')}: {o.get('side')} {o.get('size')} {o.get('product_id')} @ {o.get('limit_price', 'MARKET')} ({o.get('status')})")
        else:
            print("   Sin órdenes abiertas")
    
    # Abrir posición
    elif args.open:
        side, size, product, leverage = args.open
        size = float(size)
        leverage = int(leverage)
        
        print(f"\n🚀 ABIENDO POSICIÓN:")
        print(f"   Producto: {product}")
        print(f"   Side: {side}")
        print(f"   Tamaño: {size}")
        print(f"   Apalancamiento: {leverage}x")
        
        result = trader.open_position(product, side, size, leverage)
        
        print(f"\n   Resultado:")
        print(json.dumps(result, indent=4))
    
    # Cerrar posición
    elif args.close:
        product = args.close
        
        print(f"\n🔻 CERRANDO POSICIÓN: {product}")
        result = trader.close_position(product)
        
        print(f"\n   Resultado:")
        print(json.dumps(result, indent=4))
    
    else:
        # Mostrar resumen por defecto
        print("\n" + "="*60)
        print("📊 RESUMEN DE CUENTA")
        print("="*60)
        
        # Balance
        balance = trader.get_balance()
        summary = balance.get("balance_summary", {})
        
        print("\n📊 Balance:")
        if summary:
            print(f"   Disponible: ${summary.get('available_balance', {}).get('value', 'N/A')}")
            print(f"   Total: ${summary.get('total_balance', {}).get('value', 'N/A')}")
        else:
            print("   Sin balance en futuros")
        
        # Posiciones
        pos_summary = trader.get_position_summary()
        print(f"\n📈 Posiciones: {pos_summary.get('count', 0)}")
        print(f"   PnL Total: ${pos_summary.get('total_pnl', 0):.2f}")
        
        # Contratos populares
        print("\n📋 Contratos Populares:")
        for prefix in ["BIT", "BIP", "ETP", "SOL"]:
            contracts = trader.get_futures_contracts(prefix)
            if contracts:
                c = contracts[0]
                print(f"   {prefix}: {c.get('product_id')} @ ${c.get('price')}")
        
        print("\n" + "="*60)
        print("💡 Usa --help para ver todas las opciones")
        print("="*60)


if __name__ == "__main__":
    main()
