#!/usr/bin/env python3
"""
DOWNLOADER DE DATA CRIPTO - APIS PUBLICAS v1.0

Descarga data de APIs publicas que NO requieren autenticacion.

 FUENTES:
 - Binance API (gratis, publica)
 - CoinGecko API (gratis, publica)
 - CryptoCompare API (gratis, publica)

 USO:
    python3 download_crypto_data.py --all          # Descarga todo
    python3 download_crypto_data.py --product BTC  # Solo BTC
    python3 download_crypto_data.py --days 90    # 90 dias
    python3 download_crypto_data.py --verify      # Verificar archivos
    python3 download_crypto_data.py --copy       # Copiar a data/
"""

import os
import sys
import json
import time
import csv
from datetime import datetime, timedelta
from urllib.request import urlopen
from urllib.error import URLError

# Configuracion
OUTPUT_DIR = "data_crypto_csv"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# APIs publicas
APIS = {
    "BTC": {
        "binance": "https://api.binance.com/api/v3/klines",
        "coingecko": "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
    },
    "ETH": {
        "binance": "https://api.binance.com/api/v3/klines",
        "coingecko": "https://api.coingecko.com/api/v3/coins/ethereum/market_chart",
    },
    "SOL": {
        "coingecko": "https://api.coingecko.com/api/v3/coins/solana/market_chart",
    },
}

# Intervalos de Binance (m=mins, h=hours, d=days)
BINANCE_INTERVALS = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

# Periodos maximos por intervalo
MAX_DAYS = {
    "1m": 1,
    "5m": 7,
    "15m": 30,
    "1h": 90,
    "4h": 180,
    "1d": 365,
}


def download_binance(symbol="BTCUSDT", interval="1h", days=90):
    """Descarga de Binance API (publica)"""
    print(f"\n[{symbol}] [{interval}] [{days}d]...", end=" ", flush=True)
    
    # Limitar dias segun intervalo
    max_d = MAX_DAYS.get(interval, 90)
    if days > max_d:
        days = max_d
    
    # Calcular timestamps
    end_ts = int(datetime.now().timestamp() * 1000)
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    
    url = f"{APIS['BTC']['binance']}?symbol={symbol}&interval={interval}&startTime={start_ts}&endTime={end_ts}&limit=1000"
    
    try:
        with urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        if not data or "error" in data:
            print("SIN DATOS")
            return 0
        
        # Guardar CSV
        filename = f"{OUTPUT_DIR}/{symbol}_{interval}.csv"
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
            
            for candle in data:
                ts = datetime.fromtimestamp(candle[0] / 1000).isoformat()
                writer.writerow([
                    ts,
                    candle[1],  # open
                    candle[2],  # high
                    candle[3],  # low
                    candle[4],  # close
                    candle[5],  # volume
                ])
        
        count = len(data)
        print(f"OK ({count:,} velas)")
        return count
        
    except URLError as e:
        print(f"ERROR (URL): {e}")
        return 0
    except json.JSONDecodeError:
        print("ERROR (JSON)")
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        return 0


def download_coingecko(coin="bitcoin", vs_currency="usd", days=90):
    """Descarga de CoinGecko API (publica)"""
    print(f"\n[{coin}] [{vs_currency}] [{days}d]...", end=" ", flush=True)
    
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency={vs_currency}&days={days}&interval=daily"
    
    try:
        with urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        if "prices" not in data or not data["prices"]:
            print("SIN DATOS")
            return 0
        
        prices = data["prices"]
        market_caps = {m[0]: m[1] for m in data.get("market_caps", [])}
        volumes = {v[0]: v[1] for v in data.get("total_volumes", [])}
        
        # Guardar CSV
        filename = f"{OUTPUT_DIR}/{coin}_{vs_currency}.csv"
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
            
            for price_data in prices:
                ts = datetime.fromtimestamp(price_data[0] / 1000).isoformat()
                price = price_data[1]
                
                # Alto/bajo del dia (simplificado)
                writer.writerow([
                    ts,
                    price,  # open
                    price * 1.02,  # high (aprox)
                    price * 0.98,  # low (aprox)
                    price,  # close
                    volumes.get(price_data[0], 0),
                ])
        
        count = len(prices)
        print(f"OK ({count} dias)")
        return count
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 0


def download_all_crypto(days=90):
    """Descarga todos los simbolos disponibles"""
    print("="*60)
    print("DESCARGANDO DATA DE APIS PUBLICAS")
    print("="*60)
    print(f"Directorio: {OUTPUT_DIR}")
    print(f"Periodo: {days} dias")
    print("="*60)
    
    total = 0
    
    # Binance (mas datos, mejor calidad)
    symbols = [
        ("BTCUSDT", "1h", 90),
        ("ETHUSDT", "1h", 90),
        ("SOLUSDT", "1h", 90),
        ("XRPUSDT", "1h", 90),
    ]
    
    for symbol, interval, d in symbols:
        total += download_binance(symbol, interval, min(days, d))
        time.sleep(0.5)  # Rate limiting
    
    print(f"\n{'='*60}")
    print(f"DESCARGA COMPLETA: {total:,} registros")
    print(f"{'='*60}")
    
    return total


def verify_files():
    """Verifica archivos descargados"""
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
                lines = f.readlines()
                count = len([l for l in lines if l.strip() and "," in l and "timestamp" not in l])
                total += count
                print(f"OK {filename}: {count:,} registros")
        except Exception as e:
            print(f"ERROR {filename}: {e}")
    
    print(f"\nTotal: {len(files)} archivos | {total:,} registros")
    print("="*60)


def copy_to_data():
    """Copia archivos a data/"""
    print("\n" + "="*60)
    print("COPIANDO A DATA/")
    print("="*60)
    
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    
    copied = 0
    for filename in os.listdir(OUTPUT_DIR):
        if filename.endswith(".csv"):
            src = os.path.join(OUTPUT_DIR, filename)
            dst = os.path.join(data_dir, filename)
            
            with open(src, "r") as f:
                content = f.read()
            
            with open(dst, "w") as f:
                f.write(content)
            
            copied += 1
            print(f"OK {filename}")
    
    print(f"\n{copied} archivos copiados a {data_dir}/")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download crypto data from public APIs")
    parser.add_argument("--product", "-p", type=str, help="Symbol (BTCUSDT, ETHUSDT, etc)")
    parser.add_argument("--days", "-d", type=int, default=90, help="Days")
    parser.add_argument("--all", "-a", action="store_true", help="Download all")
    parser.add_argument("--verify", "-v", action="store_true", help="Verify")
    parser.add_argument("--copy", "-c", action="store_true", help="Copy to data/")
    
    args = parser.parse_args()
    
    if args.verify:
        verify_files()
        return
    
    if args.copy:
        copy_to_data()
        return
    
    if args.all:
        download_all_crypto(args.days)
    elif args.product:
        download_binance(args.product, "1h", args.days)
    else:
        print("\nDescargando BTCUSDT (1h, 90 dias)...")
        download_binance("BTCUSDT", "1h", 90)
    
    print("\nVerificar: python3 download_crypto_data.py --verify")
    print("Copiar:   python3 download_crypto_data.py --copy")


if __name__ == "__main__":
    main()
