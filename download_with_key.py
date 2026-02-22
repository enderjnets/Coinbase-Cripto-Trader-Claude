#!/usr/bin/env python3
"""
DOWNLOADER DE DATA DE COINBASE CON API KEY PUBLICA v1.0

Usa la API Key publica para acceder a endpoints publicos de Coinbase.

 USO:
    python3 download_with_key.py --list
    python3 download_with_key.py --product BTC-USD --days 90
    python3 download_with_key.py --all
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from urllib.parse import urlencode

# Cargar API Key
def load_api_key():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    if key == "COINBASE_API_KEY":
                        return value
    return os.getenv("COINBASE_API_KEY", "uf35tE3T8PoOhCKNgrjqPr2kT0QvXyD3")

API_KEY = load_api_key()

# URLs de Coinbase
API_URL = "https://api.coinbase.com"
OUTPUT_DIR = "data_with_api"
os.makedirs(OUTPUT_DIR, exist_ok=True)

GRANULARITY = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
}

PRODUCTS = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
    "XRP-USD",
    "BTC-PERP",
    "ETH-PERP",
]

GRANULARITIES = ["1m", "5m", "15m", "1h"]


class CoinbaseDownloader:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = API_URL
        self.last_request = 0
    
    def request(self, endpoint, params=None):
        # Rate limiting
        elapsed = time.time() - self.last_request
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        self.last_request = time.time()
        
        url = f"{self.base_url}{endpoint}"
        if params:
            url += "?" + urlencode(params)
        
        headers = {
            "Accept": "application/json",
            "CB-ACCESS-KEY": self.api_key,
        }
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read().decode()
                return json.loads(data)
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def list_products(self):
        print("\nPRODUCTOS DISPONIBLES:")
        print("-" * 50)
        
        data = self.request("/api/v3/brokerage/products")
        
        if "error" in data:
            print(f"Error: {data['error']}")
            return
        
        products = data.get("products", [])
        count = 0
        
        for p in products[:20]:
            if p.get("status") == "online":
                print(f"  {p.get('product_id', ''):20} | {p.get('quote_currency_id', '')} | {p.get('status', '')}")
                count += 1
        
        print(f"\nTotal: {count} productos")
        print("\nNOTA: Para futuros regulados se requiere Private Key para JWT")
    
    def download_candles(self, product, granularity, days=90):
        print(f"\n[{product}] [{granularity}] [{days}d]...", end=" ", flush=True)
        
        gran_sec = GRANULARITY.get(granularity, 300)
        end_ts = int(datetime.now().timestamp())
        start_ts = int((datetime.now() - timedelta(days=days)).timestamp())
        
        endpoint = f"/api/v3/brokerage/products/{product}/candles"
        params = {
            "start": str(start_ts),
            "end": str(end_ts),
            "granularity": gran_sec
        }
        
        data = self.request(endpoint, params)
        
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
        filename = f"{OUTPUT_DIR}/{product}_{granularity}.csv"
        with open(filename, "w", newline="") as f:
            import csv
            writer = csv.writer(f)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
            
            for c in candles:
                ts = datetime.fromtimestamp(c[0]).isoformat()
                writer.writerow([ts, c[3], c[2], c[1], c[4], c[5]])
        
        count = len(candles)
        print(f"OK ({count:,} velas)")
        return count
    
    def download_all(self, products=None, granularities=None, days=90):
        if products is None:
            products = PRODUCTS
        if granularities is None:
            granularities = GRANULARITIES
        
        print("=" * 60)
        print("DESCARGANDO DATA DE COINBASE")
        print("=" * 60)
        print(f"Directorio: {OUTPUT_DIR}")
        print(f"Periodo: {days} dias")
        print("=" * 60)
        
        total = 0
        for product in products:
            for gran in granularities:
                try:
                    total += self.download_candles(product, gran, days)
                except Exception as e:
                    print(f"Error: {e}")
        
        print(f"\n{'=' * 60}")
        print(f"DESCARGA COMPLETA: {total:,} velas")
        print(f"{'=' * 60}")
        
        return total


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Coinbase data")
    parser.add_argument("--product", "-p", type=str, help="Product ID")
    parser.add_argument("--granularity", "-g", type=str, default="5m", help="Timeframe")
    parser.add_argument("--days", "-d", type=int, default=90, help="Days")
    parser.add_argument("--all", "-a", action="store_true", help="Download all")
    parser.add_argument("--list", "-l", action="store_true", help="List products")
    parser.add_argument("--verify", "-v", action="store_true", help="Verify files")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("DOWNLOADER DE DATA DE COINBASE")
    print(f"API Key: {API_KEY[:8]}...")
    print("=" * 60)
    
    downloader = CoinbaseDownloader(API_KEY)
    
    if args.list:
        downloader.list_products()
        return
    
    if args.verify:
        print("\nARCHIVOS DESCARGADOS:")
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
            except:
                print(f"ERROR {filename}")
        print(f"\nTotal: {len(files)} archivos | {total:,} velas")
        return
    
    if args.all:
        downloader.download_all(days=args.days)
    elif args.product:
        downloader.download_candles(args.product, args.granularity, args.days)
    else:
        print("\nDescargando BTC-USD (5m, 90 dias)...")
        downloader.download_candles("BTC-USD", "5m", 90)
    
    print("\nVerificar: python3 download_with_key.py --verify")


if __name__ == "__main__":
    main()
