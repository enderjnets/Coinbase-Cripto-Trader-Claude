#!/usr/bin/env python3
"""
DOWNLOADER DE DATA DE FUTUROS - SOLO STDLIB
Genera archivos CSV compatibles con el sistema de trading.

 USO:
    python3 download_futures_csv.py --all
    python3 download_futures_csv.py --product BTC-USD --days 90
"""

import os
import sys
import time
import json
import csv
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from urllib.parse import urlencode

# Configuracion
API_URL = "https://api.coinbase.com"
OUTPUT_DIR = "data_futures_csv"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Granularity (segundos)
GRANULARITY = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}

# API Key
def load_api_key():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    if k == "COINBASE_API_KEY":
                        return v
    return os.getenv("COINBASE_API_KEY")

API_KEY = load_api_key()


class CoinbaseClient:
    """Cliente HTTP para API de Coinbase"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.last_request = 0
    
    def request(self, endpoint, params=None):
        # Rate limiting
        elapsed = time.time() - self.last_request
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        self.last_request = time.time()
        
        url = f"{API_URL}{endpoint}"
        if params:
            url += "?" + urlencode(params)
        
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_candles(self, product, start, end, gran):
        params = {"start": str(start), "end": str(end), "granularity": gran}
        return self.request(f"/api/v3/brokerage/products/{product}/candles", params)


def download_csv(client, product, gran_name, days=90):
    """Descarga y guarda como CSV"""
    print(f"\n[{product}] [{gran_name}] [{days}d]...", end=" ", flush=True)
    
    gran_sec = GRANULARITY.get(gran_name, 300)
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    
    data = client.get_candles(product, start_ts, end_ts, gran_sec)
    
    if "error" in data:
        print(f"ERROR ({data['error']})")
        return 0
    
    candles = data.get("candles", [])
    if not candles:
        print("SIN DATOS")
        return 0
    
    # Ordenar por timestamp
    candles.sort(key=lambda x: x[0])
    
    # Guardar CSV
    filename = f"{OUTPUT_DIR}/{product}_{gran_name}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        
        for c in candles:
            ts = datetime.fromtimestamp(c[0]).isoformat()
            writer.writerow([ts, c[3], c[2], c[1], c[4], c[5]])
    
    count = len(candles)
    print(f"OK ({count:,} velas)")
    return count


def download_all(client, products, gran_name, days):
    """Descarga todos los productos"""
    print("="*60)
    print("DESCARGANDO DATA DE FUTUROS")
    print("="*60)
    print(f"Directorio: {OUTPUT_DIR}")
    print(f"Periodo: {days} dias")
    print(f"Timeframe: {gran_name}")
    print("="*60)
    
    total = 0
    for product in products:
        try:
            total += download_csv(client, product, gran_name, days)
        except Exception as e:
            print(f"ERROR: {e}")
    
    print(f"\n{'='*60}")
    print(f"DESCARGA COMPLETA: {total:,} velas")
    print(f"{'='*60}")
    
    return total


def list_products(client):
    """Lista productos"""
    print("\nPRODUCTOS DISPONIBLES:")
    print("-"*50)
    
    data = client.request("/api/v3/brokerage/products")
    if "error" in data:
        print(f"Error: {data['error']}")
        return
    
    products = data.get("products", [])
    count = 0
    for p in products:
        if p.get("status") == "online":
            print(f"  {p.get('product_id', ''):20} | {p.get('quote_currency_id', '')}")
            count += 1
            if count >= 20:
                print("  ... (mas)")
                break
    
    print(f"\nTotal: {count} productos")


def verify_files():
    """Verifica archivos"""
    print("\n" + "="*60)
    print("ARCHIVOS DESCARGADOS")
    print("="*60)
    
    if not os.path.exists(OUTPUT_DIR):
        print(f"No existe: {OUTPUT_DIR}")
        return
    
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".csv")]
    total = 0
    
    for filename in sorted(files):
        filepath = os.path.join(OUTPUT_DIR, filename)
        try:
            with open(filepath, "r") as f:
                count = sum(1 for _ in f) - 1
                total += count
                print(f"OK {filename}: {count:,} velas")
        except Exception as e:
            print(f"ERROR {filename}: {e}")
    
    print(f"\nTotal: {len(files)} archivos | {total:,} velas")
    print("="*60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Coinbase Futures data")
    parser.add_argument("--product", "-p", type=str, help="Product ID")
    parser.add_argument("--granularity", "-g", type=str, default="5m", help="Timeframe: 1m, 5m, 15m")
    parser.add_argument("--days", "-d", type=int, default=90, help="Days")
    parser.add_argument("--all", "-a", action="store_true", help="Download all")
    parser.add_argument("--verify", "-v", action="store_true", help="Verify")
    parser.add_argument("--list", "-l", action="store_true", help="List products")
    
    args = parser.parse_args()
    
    # Verificar API Key
    if not API_KEY:
        print("\n" + "="*60)
        print("ERROR: COINBASE_API_KEY no configurada")
        print("="*60)
        print("\nAgregar al archivo .env:")
        print("   COINBASE_API_KEY=069e2e6b-537d-463d-a42f-470e36eb94ed")
        return
    
    client = CoinbaseClient(API_KEY)
    
    if args.list:
        list_products(client)
        return
    
    if args.verify:
        verify_files()
        return
    
    # Productos por defecto
    products = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"]
    
    if args.all:
        download_all(client, products, args.granularity, args.days)
    elif args.product:
        download_csv(client, args.product, args.granularity, args.days)
    else:
        print("\nDescargando BTC-USD (5m, 90 dias)...")
        download_csv(client, "BTC-USD", "5m", 90)
    
    print("\nVerificar: python3 download_futures_csv.py --verify")
    print("Copiar a data/: cp data_futures_csv/*.csv data/")


if __name__ == "__main__":
    main()
