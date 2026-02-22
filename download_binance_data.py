#!/usr/bin/env python3
"""
DOWNLOADER DE DATA DE BINANCE - API ABIERTA v1.0

Descarga datos OHLCV de Binance SIN necesidad de API Key.

 USO:
    python3 download_binance_data.py --all          # Descarga todo
    python3 download_binance_data.py --product BTCUSDT    # Solo BTC
    python3 download_binance_data.py --verify              # Verificar archivos
"""

import os
import sys
import json
import time
import csv
import urllib.request
from datetime import datetime, timedelta

# Binance API (GRATIS - SIN AUTENTICACION)
BINANCE_URL = "https://api.binance.com/api/v3"
OUTPUT_DIR = "data_binance"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Simbolos disponibles
SYMBOLS = [
    "BTCUSDT",  # Bitcoin
    "ETHUSDT",  # Ethereum
    "SOLUSDT",  # Solana
    "XRPUSDT",  # XRP
    "BNBUSDT",  # BNB
    "ADAUSDT",  # Cardano
    "DOGEUSDT", # Dogecoin
    "MATICUSDT", # Polygon
    "DOTUSDT",  # Polkadot
    "LTCUSDT",  # Litecoin
]

# Intervalos (K-lines)
INTERVALS = [
    ("1m", "1m"),
    ("5m", "5m"),
    ("15m", "15m"),
    ("1h", "1h"),
    ("4h", "4h"),
    ("1d", "1d"),
]


def download_klines(symbol, interval, limit=1000):
    """Descarga velas K-line de Binance"""
    print(f"[{symbol}] [{interval}]...", end=" ", flush=True)
    
    url = f"{BINANCE_URL}/klines?symbol={symbol}&interval={interval}&limit={limit}"
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        if not data or "error" in data:
            print("ERROR")
            return 0
        
        # Binance returns: [timestamp, open, high, low, close, volume, ...]
        candles = data
        
        if not candles:
            print("SIN DATOS")
            return 0
        
        # Guardar CSV
        filename = f"{OUTPUT_DIR}/{symbol}_{interval}.csv"
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
            
            for c in candles[:1000]:  # Binance limita a 1000 velas por peticion
                ts = datetime.fromtimestamp(c[0] / 1000).isoformat()
                writer.writerow([ts, c[1], c[2], c[3], c[4], c[5]])
        
        count = len(candles)
        print(f"OK ({count:,} velas)")
        return count
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 0


def download_all():
    """Descarga todos los simbolos"""
    print("="*60)
    print("DESCARGANDO DATA DE BINANCE (API ABIERTA)")
    print("="*60)
    print(f"Directorio: {OUTPUT_DIR}")
    print("Simbolos: BTC, ETH, SOL, XRP, BNB, ADA, DOGE, MATIC, DOT, LTC")
    print("="*60)
    
    total = 0
    
    for symbol in SYMBOLS:
        for interval, _ in INTERVALS[:3]:  # Solo 1m, 5m, 15m para no tardar mucho
            try:
                count = download_klines(symbol, interval, 1000)
                total += count
            except Exception as e:
                print(f"Error con {symbol}: {e}")
    
    print(f"\n{'='*60}")
    print(f"DESCARGA COMPLETA: {total:,} velas")
    print(f"{'='*60}")
    
    return total


def verify():
    """Verifica archivos descargados"""
    print("\nARCHIVOS DESCARGADOS:")
    print("-"*40)
    
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".csv")] if os.path.exists(OUTPUT_DIR) else []
    total = 0
    
    for filename in sorted(files)[:20]:
        filepath = os.path.join(OUTPUT_DIR, filename)
        try:
            with open(filepath, "r") as f:
                count = sum(1 for _ in f) - 1
                total += count
                print(f"OK {filename}: {count:,} velas")
        except:
            print(f"ERROR {filename}")
    
    print(f"\nTotal: {len(files)} archivos | {total:,} velas")


def download_specific(symbol, interval="5m"):
    """Descarga un simbolo especifico"""
    print(f"\nDescargando {symbol}...")
    download_klines(symbol, interval, 1000)


# Probar conexion primero
def test_connection():
    """Prueba la conexion con Binance"""
    print("PRUEBA DE CONEXION CON BINANCE...")
    try:
        url = f"{BINANCE_URL}/ping"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
        if data == {}:
            print("✅ BINANCE API CONECTADA!")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# MAIN
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Binance data (FREE API)")
    parser.add_argument("--product", "-p", type=str, help="Symbol (BTCUSDT, ETHUSDT, etc)")
    parser.add_argument("--interval", "-i", type=str, default="5m", help="Interval (1m, 5m, 15m, 1h)")
    parser.add_argument("--all", "-a", action="store_true", help="Download all symbols")
    parser.add_argument("--verify", "-v", action="store_true", help="Verify files")
    parser.add_argument("--test", "-t", action="store_true", help="Test connection")
    args = parser.parse_args()
    
    if args.test:
        test_connection()
        return
    
    if args.verify:
        verify()
        return
    
    if args.all:
        download_all()
        return
    
    if args.product:
        download_specific(args.product, args.interval)
        return
    
    # Por defecto: descargar BTCUSDT 5m
    print("\nDESCARGANDO BTCUSDT (5m)...")
    download_klines("BTCUSDT", "5m", 1000)
    
    print("\nVerificar: python3 download_binance_data.py --verify")


if __name__ == "__main__":
    main()
