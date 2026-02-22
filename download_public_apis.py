#!/usr/bin/env python3
"""
DOWNLOADER DE DATA CRIPTO - APIs PUBLICAS v1.0

Prueba diferentes APIs publicas para descargar datos.

APIs probadas:
1. Binance (gratis, publica)
2. CryptoGecko (gratis, publica)
3. Yahoo Finance (gratis)
4. CoinCap (gratis)
5. Coinbase (requiere auth)
6. Kaggle (dataset)
"""

import os
import sys
import json
import time
import csv
from datetime import datetime
from urllib.request import urlopen

OUTPUT_DIR = "data_public_apis"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# APIs publicas
APIS = {
    "coingecko": "https://api.coingecko.com/api/v3",
    "coincap": "https://api.coincap.io/v2",
    "yahoo": "https://query1.finance.yahoo.com",
    "cryptocompare": "https://min-api.cryptocompare.com",
}

# Simbolos
SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]


def test_api(name, url):
    """Prueba una API"""
    print(f"\n{name}: {url}")
    try:
        with urlopen(url, timeout=10) as response:
            data = response.read(500).decode()
            print(f"  ✅ Conectado ({len(data)} bytes)")
            return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def download_coingecko(coin="bitcoin", days=90):
    """Descarga de CoinGecko API (gratis)"""
    print(f"\n[COINGECKO] {coin}...")
    
    # API publica sin auth
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days={days}"
    
    try:
        with urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        if "prices" in data:
            prices = data["prices"]
            print(f"  ✅ {len(prices)} precios")
            
            # Guardar
            filename = f"{OUTPUT_DIR}/{coin}_prices.csv"
            with open(filename, "w") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "price", "market_cap", "volume"])
                for p in prices:
                    ts = datetime.fromtimestamp(p[0]/1000).isoformat()
                    writer.writerow([ts, p[1], p[2], p[3] if len(p) > 3 else 0])
            
            print(f"  💾 {filename}")
            return len(prices)
        else:
            print("  ❌ Sin datos")
            return 0
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return 0


def download_all_coingecko():
    """Descarga todos los simbolos"""
    print("="*60)
    print("COINGECKO API (GRATIS)")
    print("="*60)
    
    coins = ["bitcoin", "ethereum", "solana", "ripple"]
    
    total = 0
    for coin in coins:
        total += download_coingecko(coin)
        time.sleep(1)  # Rate limit
    
    print(f"\nTotal: {total} precios")
    return total


def test_apis():
    """Prueba todas las APIs"""
    print("="*60)
    print("PROBANDO APIs PUBLICAS")
    print("="*60)
    
    tests = [
        ("CoinGecko", "https://api.coingecko.com/api/v3/ping"),
        ("CoinCap", "https://api.coincap.io/v2/assets/bitcoin"),
        ("CryptoCompare", "https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD"),
    ]
    
    for name, url in tests:
        test_api(name, url)
    
    print("\n" + "="*60)
    print("COINMARKETCAP (alternativa)")
    print("="*60)
    print("Ve: https://api.coinmarketcap.com/v1/cryptocurrency/listings/latest")
    
    print("\n" + "="*60)
    print("KAGGLE DATASETS")
    print("="*60)
    print("https://www.kaggle.com/datasets")
    print("https://www.kaggle.com/datasets/yamakseco/cryptocurrency-historical-data")


def download_coinmarketcap():
    """Como descargar de CoinMarketCap"""
    print("\n[COINMARKETCAP]")
    print("API: https://api.coinmarketcap.com/v1/cryptocurrency/listings/latest")
    print("Requiere API Key gratis (10k requests/dia")
    print("\nVe: https://coinmarketcap.com/api/")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download crypto data from public APIs")
    parser.add_argument("--test", "-t", action="store_true", help="Test APIs")
    parser.add_argument("--all", "-a", action="store_true", help="Download all")
    parser.add_argument("--product", "-p", type=str, help="Coin name")
    
    args = parser.parse_args()
    
    if args.test:
        test_apis()
        return
    
    if args.all:
        download_all_coingecko()
        return
    
    if args.product:
        download_coingecko(args.product.lower())
        return
    
    # Test
    test_apis()


if __name__ == "__main__":
    main()
