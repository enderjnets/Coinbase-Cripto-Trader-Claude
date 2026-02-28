#!/usr/bin/env python3
"""
Descarga histórico completo (180 días) para pares SPOT prioritarios.
Usa la API pública de Coinbase Exchange - no requiere autenticación.
"""
import requests
import time
import csv
import os
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ASSETS = ["ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD",
          "DOT-USD", "LINK-USD", "LTC-USD", "ATOM-USD"]

TIMEFRAMES = {"FIVE_MINUTE": 300, "FIFTEEN_MINUTE": 900}

DAYS_BACK = 180
BASE_URL = "https://api.exchange.coinbase.com"
CANDLES_PER_REQUEST = 300


def fetch_candles(product_id, granularity, start_ts, end_ts):
    url = f"{BASE_URL}/products/{product_id}/candles"
    params = {"granularity": granularity, "start": str(start_ts), "end": str(end_ts), "limit": CANDLES_PER_REQUEST}
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            # Format: [time, low, high, open, close, volume]
            return [(c[0], c[3], c[2], c[1], c[4], c[5]) for c in data]  # ts, open, high, low, close, vol
        except Exception as e:
            print(f"  Retry {attempt+1}: {e}")
            time.sleep(2)
    return []


def download_asset(product_id, tf_name, granularity):
    out_file = DATA_DIR / f"{product_id}_{tf_name}.csv"

    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=DAYS_BACK)).timestamp())

    all_candles = []
    current = start_ts
    step = CANDLES_PER_REQUEST * granularity

    print(f"\n[{product_id} {tf_name}] Downloading {DAYS_BACK} days...")

    while current < end_ts:
        batch_end = min(current + step, end_ts)
        candles = fetch_candles(product_id, granularity, current, batch_end)
        if candles:
            all_candles.extend(candles)
            current = max(c[0] for c in candles) + granularity
            print(f"  {len(all_candles):,} candles...", end="\r")
        else:
            current += step
        time.sleep(0.4)

    if not all_candles:
        print(f"  ERROR: no data")
        return 0

    # Deduplicate and sort
    seen = {}
    for c in all_candles:
        seen[c[0]] = c
    sorted_candles = sorted(seen.values(), key=lambda x: x[0])

    with open(out_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for ts, o, h, l, c, v in sorted_candles:
            dt = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([dt, o, h, l, c, v])

    print(f"  DONE: {len(sorted_candles):,} candles → {out_file.name}")
    return len(sorted_candles)


if __name__ == "__main__":
    print(f"Downloading {len(ASSETS)} assets x {len(TIMEFRAMES)} timeframes...")
    print(f"Period: last {DAYS_BACK} days\n")

    results = []
    for asset in ASSETS:
        for tf_name, granularity in TIMEFRAMES.items():
            count = download_asset(asset, tf_name, granularity)
            results.append((asset, tf_name, count))
            time.sleep(1)

    print("\n=== SUMMARY ===")
    for asset, tf, count in results:
        status = "OK" if count > 500 else "WARN (short)" if count > 0 else "FAILED"
        print(f"  {asset} {tf}: {count:,} candles [{status}]")
