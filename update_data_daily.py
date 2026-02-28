#!/usr/bin/env python3
"""
📅 Actualizador Diario de Datos
================================

Actualiza todos los archivos CSV con los datos más recientes.
Se ejecuta automáticamente vía cron cada día.

Uso:
    python update_data_daily.py
"""

import os
import sys
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Configuración
PROJECT_DIR = Path("/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude")
DATA_DIR = PROJECT_DIR / "data"
DATA_FUTURES_DIR = PROJECT_DIR / "data_futures"
LOG_FILE = PROJECT_DIR / "data_update.log"

API_URL = "https://api.exchange.coinbase.com"

def log(msg):
    """Log con timestamp"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_last_timestamp(filepath):
    """Obtener el último timestamp de un archivo CSV"""
    try:
        df = pd.read_csv(filepath)
        if 'timestamp' in df.columns:
            # Convertir a datetime si no lo está
            ts = pd.to_datetime(df['timestamp'].iloc[-1])
            return ts
    except:
        pass
    return None

def download_new_candles(product_id, granularity, start_ts, end_ts):
    """Descargar velas desde la API de Coinbase"""
    url = f"{API_URL}/products/{product_id}/candles"
    
    gran_map = {
        "ONE_MINUTE": 60,
        "FIVE_MINUTE": 300,
        "FIFTEEN_MINUTE": 900,
    }
    
    gran_seconds = gran_map.get(granularity, 300)
    all_candles = []
    current_end = int(end_ts.timestamp())
    start_seconds = int(start_ts.timestamp())
    
    while current_end > start_seconds:
        params = {
            "granularity": gran_seconds,
            "start": str(start_seconds),
            "end": str(current_end)
        }
        
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                break
            
            candles = resp.json()
            if not candles:
                break
            
            all_candles.extend(candles)
            oldest = min(c[0] for c in candles)
            current_end = oldest - 1
            
            time.sleep(0.3)
        except Exception as e:
            log(f"   Error descargando {product_id}: {e}")
            break
    
    if not all_candles:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_candles, columns=['timestamp', 'low', 'high', 'open', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    df = df.sort_values('timestamp').drop_duplicates('timestamp')
    
    return df

def update_spot_files():
    """Actualizar todos los archivos SPOT"""
    log("="*50)
    log("📥 ACTUALIZANDO DATOS SPOT")
    log("="*50)
    
    if not DATA_DIR.exists():
        log("Directorio data/ no existe")
        return
    
    updated = 0
    skipped = 0
    
    for csv_file in sorted(DATA_DIR.glob("*.csv")):
        # Parsear nombre: BTC-USD_FIVE_MINUTE.csv
        parts = csv_file.stem.split("_")
        if len(parts) < 2:
            continue
        
        product_id = parts[0]
        granularity = "_".join(parts[1:])
        
        # Obtener último timestamp
        last_ts = get_last_timestamp(csv_file)
        
        if last_ts is None:
            log(f"⚠️ {csv_file.name}: no se pudo leer timestamp")
            continue
        
        now = datetime.now()
        
        # Si el último dato es de hace menos de 1 hora, saltar
        age_hours = (now - last_ts).total_seconds() / 3600
        if age_hours < 1:
            log(f"⏭️ {csv_file.name}: datos recientes ({age_hours:.1f}h)")
            skipped += 1
            continue
        
        log(f"🔄 {csv_file.name}: actualizando desde {last_ts}")
        
        # Descargar nuevos datos
        new_df = download_new_candles(product_id, granularity, last_ts, now)
        
        if new_df.empty:
            log(f"   ⚠️ Sin datos nuevos")
            skipped += 1
            continue
        
        # Cargar datos existentes y mergear
        existing_df = pd.read_csv(csv_file)
        existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
        
        combined = pd.concat([existing_df, new_df])
        combined = combined.sort_values('timestamp').drop_duplicates('timestamp')
        
        # Guardar
        combined.to_csv(csv_file, index=False)
        
        new_rows = len(new_df)
        log(f"   ✅ {new_rows} velas nuevas agregadas")
        updated += 1
        
        time.sleep(0.5)
    
    log(f"\n📊 SPOT: {updated} actualizados, {skipped} saltados")

def update_futures_files():
    """Actualizar archivos FUTURES"""
    log("\n" + "="*50)
    log("📥 ACTUALIZANDO DATOS FUTURES")
    log("="*50)
    
    if not DATA_FUTURES_DIR.exists():
        log("Directorio data_futures/ no existe")
        return
    
    updated = 0
    skipped = 0
    
    for csv_file in sorted(DATA_FUTURES_DIR.glob("*.csv")):
        parts = csv_file.stem.split("_")
        if len(parts) < 2:
            continue
        
        contract = parts[0]
        granularity = "_".join(parts[1:])
        
        last_ts = get_last_timestamp(csv_file)
        
        if last_ts is None:
            continue
        
        now = datetime.now()
        age_hours = (now - last_ts).total_seconds() / 3600
        
        if age_hours < 1:
            skipped += 1
            continue
        
        log(f"🔄 {csv_file.name}: actualizando")
        
        new_df = download_new_candles(contract, granularity, last_ts, now)
        
        if new_df.empty:
            skipped += 1
            continue
        
        existing_df = pd.read_csv(csv_file)
        existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
        
        combined = pd.concat([existing_df, new_df])
        combined = combined.sort_values('timestamp').drop_duplicates('timestamp')
        combined.to_csv(csv_file, index=False)
        
        log(f"   ✅ {len(new_df)} velas nuevas")
        updated += 1
        time.sleep(0.5)
    
    log(f"\n📊 FUTURES: {updated} actualizados, {skipped} saltados")

def main():
    log("\n" + "="*60)
    log("📅 ACTUALIZACIÓN DIARIA DE DATOS")
    log("="*60)
    
    start_time = time.time()
    
    update_spot_files()
    update_futures_files()
    
    elapsed = time.time() - start_time
    log(f"\n✅ Completado en {elapsed:.1f} segundos")

if __name__ == "__main__":
    main()
