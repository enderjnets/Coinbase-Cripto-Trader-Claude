#!/usr/bin/env python3
"""
DOWNLOADER DE DATA CRIPTO - COINGECKO v2.0

API gratuita: https://api.coingecko.com/api/v3
Sin autenticacion requerida.
"""

import os
import json
import csv
import time
from datetime import datetime

OUTPUT_DIR = "data_coingecko"
os.makedirs(OUTPUT_DIR, exist_ok=True)

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days={days}"

SYMBOLS = ["bitcoin", "ethereum", "solana", "ripple", "cardano", "dogecoin"]


def download_coin(coin, days=365):
    """Descarga datos de una criptomoneda"""
    url = COINGECKO_URL.format(coin=coin, days=days)
    
    print(f"\n[{coin}]...", end=" ", flush=True)
    
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        if "prices" not in data:
            print("SIN DATOS")
            return 0
        
        prices = data["prices"]
        print(f"{len(prices)} precios", end=" ")
        
        # Guardar
        filename = f"{OUTPUT_DIR}/{coin}.csv"
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "price", "market_cap", "volume"])
            
            for p in prices:
                ts = datetime.fromtimestamp(p[0]/1000).strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([ts, p[1], data["market_caps"][0] if data.get("market_caps") else "", data["total_volumes"][0] if data.get("total_volumes") else ""])
        
        print(f"💾 {filename}")
        return len(prices)
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 0


def download_all():
    """Descarga todos los simbolos"""
    print("="*60)
    print("COINGECKO API - DATOS DE PRECIOS REALES")
    print("="*60)
    print("Simbolos: BTC, ETH, SOL, XRP, ADA, DOGE")
    print("Periodo: 365 dias")
    print("="*60)
    
    total = 0
    for coin in SYMBOLS:
        total += download_coin(coin)
        time.sleep(1.5)  # Rate limit
    
    print(f"\n{'='*60}")
    print(f"DESCARGA COMPLETA: {total} precios")
    print(f"{'='*60}")


def verify():
    """Verifica archivos"""
    print("\nARCHIVOS DESCARGADOS:")
    print("-"*40)
    
    total = 0
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(".csv"):
            with open(f"{OUTPUT_DIR}/{f}") as file:
                count = sum(1 for _ in file) - 1
                total += count
                print(f"OK {f}: {count:,} precios")
    
    print(f"\nTotal: {total:,} precios")


# MAIN
def main():
    download_all()
    verify()

if __name__ == "__main__":
    main()
