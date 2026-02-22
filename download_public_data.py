#!/usr/bin/env python3
"""
DOWNLOADER DE DATA DE COINBASE - FUENTES PUBLICAS v1.0

Usa Yahoo Finance para descargar data historica de BTC, ETH, SOL.

 USO:
    python3 download_public_data.py --all
    python3 download_public_data.py --product BTC-USD
    python3 download_public_data.py --verify

 NO requiere API Key.
"""

import os
import sys
import time
import csv
from datetime import datetime, timedelta

# Yahoo Finance URLs
YAHOO_URLS = {
    "BTC-USD": "https://query1.finance.yahoo.com/v7/finance/download/BTC-USD",
    "ETH-USD": "https://query1.finance.yahoo.com/v7/finance/download/ETH-USD",
    "SOL-USD": "https://query1.finance.yahoo.com/v7/finance/download/SOL-USD",
    "XRP-USD": "https://query1.finance.yahoo.com/v7/finance/download/XRP-USD",
}

OUTPUT_DIR = "data_futures_csv"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Periodos
PERIODS = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "180d": 180,
    "365d": 365,
}


def download_yahoo_csv(symbol, period="90d"):
    """Descarga data de Yahoo Finance"""
    print(f"\n[{symbol}] [{period}]...", end=" ", flush=True)
    
    url = YAHOO_URLS.get(symbol)
    if not url:
        print(f"SIMBOLO NO SOPORTADO")
        return 0
    
    # Calcular fechas
    days = PERIODS.get(period, 90)
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    
    params = {
        "period1": start_ts,
        "period2": end_ts,
        "interval": "5m" if days <= 7 else "1d",
        "events": "history",
        "includeAdjustedClose": "true"
    }
    
    query = "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{url}?{query}"
    
    try:
        import urllib.request
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read().decode()
        
        lines = content.strip().split("\n")
        
        if "404 Not Found" in content or "No data" in content:
            print("SIN DATOS")
            return 0
        
        # Guardar CSV
        filename = f"{OUTPUT_DIR}/{symbol}_{period}.csv"
        with open(filename, "w", newline="") as f:
            f.write(content)
        
        # Contar velas
        count = len([l for l in lines if "," in l and "Date" not in l])
        print(f"OK ({count:,} velas)")
        return count
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 0


def download_all_products(period="90d"):
    """Descarga todos los productos"""
    print("="*60)
    print("DESCARGANDO DATA DE YAHOO FINANCE")
    print("="*60)
    print(f"Directorio: {OUTPUT_DIR}")
    print(f"Periodo: {period}")
    print("="*60)
    
    total = 0
    for symbol in YAHOO_URLS.keys():
        try:
            total += download_yahoo_csv(symbol, period)
        except Exception as e:
            print(f"ERROR: {e}")
    
    print(f"\n{'='*60}")
    print(f"DESCARGA COMPLETA: {total:,} velas")
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
                count = len([l for l in lines if l.strip() and "," in l and "Date" not in l])
                total += count
                print(f"OK {filename}: {count:,} velas")
        except Exception as e:
            print(f"ERROR {filename}: {e}")
    
    print(f"\nTotal: {len(files)} archivos | {total:,} velas")
    print("="*60)


def copy_to_data_folder():
    """Copia archivos a la carpeta data/"""
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
            
            # Copiar contenido
            with open(src, "r") as f:
                content = f.read()
            
            with open(dst, "w") as f:
                f.write(content)
            
            copied += 1
            print(f"OK {filename}")
    
    print(f"\n{copied} archivos copiados a {data_dir}/")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download public market data")
    parser.add_argument("--product", "-p", type=str, help="Product symbol")
    parser.add_argument("--period", "-d", type=str, default="90d", 
                       help="Period: 7d, 30d, 90d, 180d, 365d")
    parser.add_argument("--all", "-a", action="store_true", help="Download all")
    parser.add_argument("--verify", "-v", action="store_true", help="Verify")
    parser.add_argument("--copy", "-c", action="store_true", help="Copy to data/")
    
    args = parser.parse_args()
    
    if args.verify:
        verify_files()
        return
    
    if args.copy:
        copy_to_data_folder()
        return
    
    if args.all:
        download_all_products(args.period)
    elif args.product:
        download_yahoo_csv(args.product, args.period)
    else:
        print("\nDescargando BTC-USD (90 dias)...")
        download_yahoo_csv("BTC-USD", "90d")
    
    print("\nVerificar: python3 download_public_data.py --verify")
    print("Copiar:   python3 download_public_data.py --copy")


if __name__ == "__main__":
    main()
