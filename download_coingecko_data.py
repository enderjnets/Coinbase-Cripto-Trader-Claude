#!/usr/bin/env python3
"""
DOWNLOADER DE DATOS COINGECKO v1.0
API gratuita - Sin autenticacion

 USO:
    python3 download_coingecko_data.py --all
    python3 download_coingecko_data.py --verify
"""

import os
import json
import urllib.request
import csv
import time
from datetime import datetime

OUTPUT_DIR = "data_coingecko_free"
os.makedirs(OUTPUT_DIR, exist_ok=True)

COINS = ["bitcoin", "ethereum", "solana", "ripple", "cardano", "dogecoin"]
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_coin(coin, days=90):
    """Descarga datos de una cryptomoneda"""
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days={days}"
    print(f"[{coin}]...", end=" ")
    
    try:
        r = urllib.request.urlopen(url, timeout=30)
        data = json.loads(r.read().decode())
        prices = data.get("prices", [])
        print(f"OK ({len(prices)} precios)")
        
        filename = f"{OUTPUT_DIR}/{coin}.csv"
        with open(filename, "w") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "price", "market_cap", "volume"])
            for p in prices:
                ts = datetime.fromtimestamp(p[0]/1000).strftime("%Y-%m-%d %H:%M")
                writer.writerow([ts, p[1], p[2], p[3]])
        
        print(f"  Guardado: {filename}")
        return len(prices)
    except Exception as e:
        print(f"ERROR: {e}")
        return 0

def download_all():
    """Descarga todos los coins"""
    print("="*60)
    print("COINGECKO - DATOS REALES (GRATIS)")
    print("="*60)
    print(f"Directorio: {OUTPUT_DIR}")
    print("="*60)
    
    total = 0
    for coin in COINS:
        total += download_coin(coin)
        time.sleep(1)  # Rate limit
    
    print(f"\n{'="*60}")
    print(f"DESCARGA COMPLETA: {total} precios")
    print(f"{'="*60}")
    return total

def verify():
    """Verifica archivos descargados"""
    print("\n" + "="*60)
    print("ARCHIVOS DESCARGADOS")
    print("="*60)
    
    if not os.path.exists(OUTPUT_DIR):
        print(f"No existe: {OUTPUT_DIR}")
        return
    
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".csv")]
    total = 0
    
    for f in sorted(files):
        path = os.path.join(OUTPUT_DIR, f)
        try:
            with open(path, "r") as file:
                count = sum(1 for _ in file) - 1
                total += count
                print(f"OK {f}: {count:,} precios")
        except Exception as e:
            print(f"ERROR {f}: {e}")
    
    print(f"\nTotal: {len(files)} archivos | {total:,} precios")

# Main
def main():
    import sys
    if "--verify" in sys.argv:
        verify()
    else:
        download_all()
        verify()

if __name__ == "__main__":
    main()
