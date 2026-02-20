#!/usr/bin/env python3
"""
DOWNLOADER DE DATA HISTORICA DE COINBASE FUTUROS v2.0

 USO:
    python3 download_futures_data.py --list    # Lista productos
    python3 download_futures_data.py --all     # Descarga todo
    python3 download_futures_data.py --verify  # Verifica datos
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

# ============================================================
# CONFIGURACION
# ============================================================

API_URL = "https://api.coinbase.com"
OUTPUT_DIR = "data_futures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Cargar API Key
def load_api_key():
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if key == 'COINBASE_API_KEY':
                        return value
    return os.getenv('COINBASE_API_KEY')

API_KEY = load_api_key()

GRANULARITY_MAP = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}
PRODUCTS = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "BTC-PERP", "ETH-PERP"]
GRANULARITIES = ["1m", "5m", "15m"]


# ============================================================
# CLIENTE DE API
# ============================================================

class CoinbaseAPIClient:
    def __init__(self, api_key):
        self.base_url = API_URL
        self.api_key = api_key
        self.last_request = 0
    
    def _request(self, endpoint, params=None):
        elapsed = time.time() - self.last_request
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        self.last_request = time.time()
        
        url = f"{self.base_url}{endpoint}"
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
    
    def get_products(self):
        return self._request("/api/v3/brokerage/products")
    
    def get_candles(self, product_id, start, end, granularity):
        params = {"start": str(start), "end": str(end), "granularity": granularity}
        return self._request(f"/api/v3/brokerage/products/{product_id}/candles", params)


# ============================================================
# FUNCIONES
# ============================================================

def download_product(client, product, granularity, days=90):
    print(f"[{product}] [{granularity}]...", end=" ", flush=True)
    
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    gran_sec = GRANULARITY_MAP.get(granularity, 300)
    
    data = client.get_candles(product, start_ts, end_ts, gran_sec)
    
    if "error" in data:
        print(f"ERROR ({data['error']})")
        return 0
    
    candles = data.get("candles", [])
    if not candles:
        print("SIN DATOS")
        return 0
    
    candles.sort(key=lambda x: x[0])
    
    filename = f"{OUTPUT_DIR}/{product}_{granularity}.csv"
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'low', 'high', 'open', 'close', 'volume'])
        for c in candles:
            ts = datetime.fromtimestamp(c[0]).isoformat()
            writer.writerow([ts, c[1], c[2], c[3], c[4], c[5]])
    
    print(f"OK ({len(candles):,} velas)")
    return len(candles)


def download_all(client, products=None, granularities=None, days=90):
    if products is None:
        products = PRODUCTS
    if granularities is None:
        granularities = GRANULARITIES
    
    print("="*60)
    print("DESCARGANDO DATA DE FUTUROS DE COINBASE")
    print("="*60)
    print(f"Directorio: {OUTPUT_DIR}")
    print(f"Periodo: {days} dias")
    print("="*60)
    
    total = 0
    for product in products:
        for gran in granularities:
            try:
                count = download_product(client, product, gran, days)
                total += count
            except Exception as e:
                print(f"ERROR: {e}")
    
    print(f"\n{'='*60}")
    print(f"DESCARGA COMPLETA: {total:,} velas")
    print(f"{'='*60}")


def list_products(client):
    print("\nPRODUCTOS DISPONIBLES:")
    print("-"*50)
    
    data = client.get_products()
    if "error" in data:
        print(f"Error: {data['error']}")
        print("\nNOTA: API Key requerida para futuros")
        return
    
    products = data.get("products", [])
    for p in products[:15]:
        if p.get("status") == "online":
            print(f"  {p.get('product_id', ''):20} | {p.get('quote_currency_id', '')}")
    print(f"\n... ({len(products)} productos)")


def verify_data():
    print("\n" + "="*60)
    print("ARCHIVOS DESCARGADOS")
    print("="*60)
    
    if not os.path.exists(OUTPUT_DIR):
        print(f"No existe: {OUTPUT_DIR}")
        return
    
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.csv')]
    total = 0
    
    for filename in sorted(files):
        filepath = os.path.join(OUTPUT_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                count = sum(1 for _ in f) - 1
                total += count
                print(f"OK {filename}: {count:,} velas")
        except Exception as e:
            print(f"ERROR {filename}: {e}")
    
    print(f"\nTotal: {len(files)} archivos | {total:,} velas")


# ============================================================
# MAIN
# ============================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Coinbase Futures data")
    parser.add_argument("--product", "-p", type=str)
    parser.add_argument("--granularity", "-g", type=str, default="5m")
    parser.add_argument("--days", "-d", type=int, default=90)
    parser.add_argument("--all", "-a", action="store_true")
    parser.add_argument("--verify", "-v", action="store_true")
    parser.add_argument("--list", "-l", action="store_true")
    args = parser.parse_args()
    
    if not API_KEY:
        print("\n" + "="*60)
        print("ERROR: COINBASE_API_KEY no configurada")
        print("="*60)
        print("\nConfigurar en .env:")
        print("   COINBASE_API_KEY=069e2e6b-537d-463d-a42f-470e36eb94ed")
        return
    
    client = CoinbaseAPIClient(API_KEY)
    
    if args.list:
        list_products(client)
    elif args.verify:
        verify_data()
    elif args.all:
        download_all(client, days=args.days)
    elif args.product:
        download_product(client, args.product, args.granularity, args.days)
    else:
        print("\nDescargando BTC-USD (5m, 90 dias)...")
        download_product(client, "BTC-USD", "5m", 90)


if __name__ == "__main__":
    main()
