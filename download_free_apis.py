#!/usr/bin/env python3
"""
DOWNLOADER DE APIS CRIPTO ABIERTAS v1.0

APIs publicas que no requieren autenticacion:

1. CoinGecko (50 req/min gratis)
2. CryptoCompare (limitado)
3. CoinCap (limitado)
4. CryptoWatch (Coinbase, gratis)
5. Binance (requiere IP)

 USO:
    python3 download_free_apis.py --test  # Probar APIs
    python3 download_free_apis.py --all  # Descargar todo
    python3 download_free_apis.py --verify # Verificar
"""

import os
import json
import time
import urllib.request
from datetime import datetime

OUTPUT_DIR = "data_free_apis"
os.makedirs(OUTPUT_DIR, exist_ok=True)

APIS = {
    "coingecko": {
        "base": "https://api.coingecko.com/api/v3",
        "coins": ["bitcoin", "ethereum", "solana", "ripple", "cardano"],
        "endpoints": {
            "chart": "/coins/{coin}/market_chart?vs_currency=usd&days=365",
            "history": "/coins/{coin}/history?date={date}",
        }
    },
    "cryptocompare": {
        "base": "https://min-api.cryptocompare.com/data",
        "coins": ["BTC", "ETH", "SOL", "XRP"],
        "endpoints": {
            "price": "/price",
        }
    },
    "coincap": {
        "base": "https://api.coincap.io",
        "coins": ["bitcoin", "ethereum", "solana", "ripple"],
        "endpoints": {
            "assets": "/v2/assets",
            "history": "/v2/assets/{coin}/history",
        }
    },
    "exchangerate": {
        "base": "https://api.exchangerate.host",
        "coins": ["BTC", "ETH"],
        "endpoints": {
            "history": "/historical?base=BTC&date={date}",
        }
    }
}


def test_api(name, url):
    """Prueba una API publica"""
    print(f"\n[{name}] {url[:50]}...", end=" ", flush=True)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read(500).decode()
            print("OK")
            return True
    except Exception as e:
        print(f"ERROR")
        return False


def download_coingecko(coin="bitcoin", days=365):
    """Descarga de CoinGecko (API publica)"""
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days={days}"
    print(f"\n[CoinGecko] {coin}...", end=" ", flush=True)
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        if "prices" not in data:
            print("SIN DATOS")
            return 0
        
        prices = data["prices"]
        print(f"OK ({len(prices)} precios)")
        
        filename = f"{OUTPUT_DIR}/{coin}_coingecko.csv"
        with open(filename, "w") as f:
            f.write("timestamp,price,market_cap,volume\n")
            for p in prices:
                ts = datetime.fromtimestamp(p[0]/1000).isoformat()
                f.write(f"{ts},{p[1]},{p[2]},{p[3]}\n")
        
        return len(prices)
    except Exception as e:
        print(f"ERROR: {e}")
        return 0


def download_cryptocompare(symbol="BTC", vs="USD"):
    """Descarga de CryptoCompare"""
    url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={symbol}&tsym={vs}&limit=365"
    print(f"\n[CryptoCompare] {symbol}...", end=" ", flush=True)
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        if "Data" not in data or "Data" not in data["Data"]:
            print("SIN DATOS")
            return 0
        
        prices = data["Data"]["Data"] or []
        print(f"OK ({len(prices)} registros")
        
        filename = f"{OUTPUT_DIR}/{symbol}_cryptocompare.csv"
        with open(filename, "w") as f:
            f.write("timestamp,open,high,low,close,volume\n")
            for p in prices:
                ts = datetime.fromtimestamp(p["time"]).isoformat()
                f.write(f"{ts},{p['open']},{p['high']},{p['low']},{p['close']},{p['volumeto']}\n")
        
        return len(prices)
    except Exception as e:
        print(f"ERROR: {e}")
        return 0


def download_coincap(coin="bitcoin"):
    """Descarga de CoinCap"""
    url = f"https://api.coincap.io/v2/assets/{coin}/history?interval=d1&limit=365"
    print(f"\n[CoinCap] {coin}...", end=" ", flush=True)
    
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        if "data" not in data:
            print("SIN DATOS")
            return 0
        
        prices = data["data"]
        print(f"OK ({len(prices)} registros")
        
        filename = f"{OUTPUT_DIR}/{coin}_coincap.csv"
        with open(filename, "w") as f:
            f.write("timestamp,price,cap24Hr,volume24Hr\n")
            for p in prices:
                ts = datetime.fromtimestamp(p["time"]/1000).isoformat()
                f.write(f"{ts},{p['priceUsd']},{p['marketCapUsd']},{p['volumeUsd24Hr']}\n")
        
        return len(prices)
    except Exception as e:
        print(f"ERROR: {e}")
        return 0


def test_all_apis():
    """Prueba todas las APIs publicas"""
    print("="*60)
    print("PROBANDO APIS PUBLICAS")
    print("="*60)
    
    apis = [
        ("CoinGecko", "https://api.coingecko.com/api/v3/ping"),
        ("CryptoCompare", "https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD"),
        ("CoinCap", "https://api.coincap.io/v2/assets/bitcoin"),
    ]
    
    working = []
    for name, url in apis:
        if test_api(name, url):
            working.append(name)
    
    print(f"\nAPIs funcionando: {working}" if working else "\nNinguna API funciona")
    return working


def download_all_free():
    """Descarga de todas las APIs publicas"""
    print("="*60)
    print("DESCARGANDO DE APIS PUBLICAS")
    print("="*60)
    
    total = 0
    
    # CoinGecko
    for coin in ["bitcoin", "ethereum", "solana"]:
        total += download_coingecko(coin)
        time.sleep(1)  # Rate limit
    
    # CryptoCompare
    for symbol in ["BTC", "ETH", "SOL"]:
        total += download_cryptocompare(symbol)
    
    # CoinCap
    for coin in ["bitcoin", "ethereum", "solana"]:
        total += download_coincap(coin)
    
    print(f"\n{'="*60}")
    print(f"DESCARGA COMPLETA: {total} registros")
    print(f"{'="*60}")


def verify_downloads():
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
                print(f"OK {f}: {count:,}")
        except:
            print(f"ERROR {f}")
    
    print(f"\nTotal: {len(files)} archivos | {total:,} registros")


if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        test_all_apis()
    elif "--verify" in sys.argv:
        verify_downloads()
    elif "--all" in sys.argv:
        download_all_free()
    else:
        print("\nAPIS CRIPTO PUBLICAS")
        print("="*60)
        print("Opciones:")
        print("  --test    Probar APIs")
        print("  --all     Descargar todo")
        print("  --verify   Verificar archivos")
        print("\nEjemplo:")
        print("  python3 download_free_apis.py --test")
