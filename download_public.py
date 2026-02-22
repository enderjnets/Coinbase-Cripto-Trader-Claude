#!/usr/bin/env python3
"""
DOWNLOADER DE DATA PUBLICA DE COINBASE v1.0

Usa endpoints PUBLICOS que no requieren autenticacion.

 USO:
    python3 download_public.py --list          # Lista productos
    python3 download_public.py --btc           # Descarga BTC
    python3 download_public.py --eth           # Descarga ETH
    python3 download_public.py --all          # Descarga todo
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

# Coinbase Public API (sin autenticacion)
PUBLIC_URLS = {
    "products": "https://api.coinbase.com/api/v3/brokerage/products",
    "btc": "https://api.coinbase.com/api/v3/brokerage/products/BTC-USD",
    "eth": "https://api.coinbase.com/api/v3/brokerage/products/ETH-USD",
    "sol": "https://api.coinbase.com/api/v3/brokerage/products/SOL-USD",
    "xrp": "https://api.coinbase.com/api/v3/brokerage/products/XRP-USD",
}

OUTPUT_DIR = "data_public"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_public(url, name="API"):
    """Obtiene datos de URL publica"""
    print(f"\n[{name}] {url[:60]}...", end=" ", flush=True)
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read().decode()
            return json.loads(data)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}")
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        print(f"ERROR: {e}")
        return {"error": str(e)}


def list_products():
    """Lista productos disponibles"""
    print("\n" + "=" * 60)
    print("PRODUCTOS DISPONIBLES (ENDPOINT PUBLICO)")
    print("=" * 60)
    
    data = fetch_public(PUBLIC_URLS["products"], "List")
    
    if "error" in data:
        print(f"\nError: {data['error']}")
        print("\nNOTA: Los endpoints de futuros requieren autenticacion JWT.")
        print("Se necesita API Key + Private Key para acceso completo.")
        return
    
    products = data.get("products", [])
    print(f"\n{len(products)} productos encontrados:")
    print("-" * 60)
    
    for p in products[:30]:
        pid = p.get("product_id", "")
        quote = p.get("quote_currency_id", "")
        status = p.get("status", "")
        price = p.get("price", "N/A")
        
        print(f"  {pid:25} | {quote:5} | {status:10} | {price}")
    
    if len(products) > 30:
        print(f"  ... ({len(products) - 30} mas)")


def download_product(symbol, output_name):
    """Descarga datos de un producto"""
    url = PUBLIC_URLS.get(symbol)
    if not url:
        print(f"\nSimbolo no encontrado: {symbol}")
        return 0
    
    data = fetch_public(url, symbol)
    
    if "error" in data:
        print(f"Error: {data['error']}")
        return 0
    
    # Extraer datos del producto
    if "price" in data:
        # Es un producto individual
        product = data
        price = product.get("price", "N/A")
        print(f"  Precio: ${price}")
        
        # Guardar info del producto
        filename = f"{OUTPUT_DIR}/{output_name}_info.json"
        with open(filename, "w") as f:
            json.dump(product, f, indent=2)
        print(f"  Info guardada: {filename}")
        
        return 1
    
    return 0


def download_all():
    """Descarga todos los productos"""
    print("\n" + "=" * 60)
    print("DESCARGANDO DATA PUBLICA DE COINBASE")
    print("=" * 60)
    print(f"Directorio: {OUTPUT_DIR}")
    print("=" * 60)
    
    total = 0
    symbols = [("btc", "BTC"), ("eth", "ETH"), ("sol", "SOL"), ("xrp", "XRP")]
    
    for symbol, name in symbols:
        total += download_product(symbol, name)
    
    print(f"\n" + "=" * 60)
    print(f"DESCARGA COMPLETA: {total} archivos")
    print("=" * 60)
    
    print("\nNOTA: Este endpoint da informacion del producto (precio actual).")
    print("Para datos historicos (OHLCV) se requiere API Key + Private Key.")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download public Coinbase data")
    parser.add_argument("--list", "-l", action="store_true", help="List products")
    parser.add_argument("--btc", action="store_true", help="Download BTC info")
    parser.add_argument("--eth", action="store_true", help="Download ETH info")
    parser.add_argument("--sol", action="store_true", help="Download SOL info")
    parser.add_argument("--xrp", action="store_true", help="Download XRP info")
    parser.add_argument("--all", "-a", action="store_true", help="Download all")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("DOWNLOADER DE DATA PUBLICA DE COINBASE")
    print("(Sin autenticacion - solo datos basicos)")
    print("=" * 60)
    
    if args.list:
        list_products()
    elif args.all:
        download_all()
    elif args.btc:
        download_product("btc", "BTC")
    elif args.eth:
        download_product("eth", "ETH")
    elif args.sol:
        download_product("sol", "SOL")
    elif args.xrp:
        download_product("xrp", "XRP")
    else:
        print("\nOpciones:")
        print("  --list    : Lista productos disponibles")
        print("  --btc     : Descarga info de BTC-USD")
        print("  --eth     : Descarga info de ETH-USD")
        print("  --all     : Descarga todos")
        print("\nEjemplo:")
        print("  python3 download_public.py --list")


if __name__ == "__main__":
    main()
