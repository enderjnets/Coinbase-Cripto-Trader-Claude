#!/usr/bin/env python3
"""
Descargador de datos REALES de futuros de Coinbase
Descarga en chunks para evitar límites de API
"""

import json
import time
import base64
import requests
import pandas as pd
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

API_KEY_PATH = "/Users/enderj/Downloads/cdp_api_key.json"
OUTPUT_DIR = Path("/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/data_futures")
API_URL = "https://api.coinbase.com"

# Cache de key
_key_id = None
_private_key = None


def load_key():
    global _key_id, _private_key
    if _key_id is None:
        with open(API_KEY_PATH) as f:
            data = json.load(f)
        raw = base64.b64decode(data["privateKey"])
        _key_id = data["id"]
        _private_key = Ed25519PrivateKey.from_private_bytes(raw[:32])
    return _key_id, _private_key


def make_jwt(method, path):
    key_id, private_key = load_key()
    now = int(time.time())
    def b64url(d):
        if isinstance(d, str): d = d.encode()
        return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
    header = b64url(json.dumps({"alg":"EdDSA","kid":key_id,"typ":"JWT"}, separators=(",",":")))
    payload = b64url(json.dumps({
        "iss":"cdp","nbf":now,"exp":now+120,"sub":key_id,
        "uri":f"{method} api.coinbase.com{path}"
    }, separators=(",",":")))
    msg = f"{header}.{payload}"
    return f"{msg}.{b64url(private_key.sign(msg.encode()))}"


def download_chunk(product_id, start, end):
    """Descarga un chunk de datos"""
    path = f"/api/v3/brokerage/products/{product_id}/candles"
    jwt = make_jwt("GET", path)
    url = f"{API_URL}{path}?start={start}&end={end}&granularity=FIVE_MINUTE"
    headers = {"Authorization": f"Bearer {jwt}"}

    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        return None

    return resp.json().get("candles", [])


def download_futures(product_id, days=30):
    """Descarga datos en chunks de 1 día"""
    all_candles = []
    end = int(time.time())

    # Descargar en chunks de 1 día
    chunks = days
    print(f"   {product_id}: ", end="", flush=True)

    for i in range(chunks):
        chunk_end = end - (i * 86400)
        chunk_start = chunk_end - 86400

        candles = download_chunk(product_id, chunk_start, chunk_end)

        if candles:
            all_candles.extend(candles)
            print(".", end="", flush=True)
        else:
            print("x", end="", flush=True)

        time.sleep(0.3)  # Rate limiting

    if not all_candles:
        print(" ❌ Sin datos")
        return None

    # Convertir a DataFrame
    df = pd.DataFrame(all_candles)
    df = df.rename(columns={"start": "timestamp"})
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="s")

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Eliminar duplicados y ordenar
    df = df.drop_duplicates(subset=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    last_price = df["close"].iloc[-1]
    print(f" ✅ {len(df)} velas, ${last_price:,.2f}")

    return df


def main():
    print("=" * 70)
    print("📥 DESCARGANDO DATOS REALES DE FUTUROS")
    print("=" * 70)
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    contracts = [
        ("BIT-27FEB26-CDE", "BTC"),
        ("BIT-27MAR26-CDE", "BTC"),
        ("BIP-20DEC30-CDE", "BTC"),
        ("ET-27FEB26-CDE", "ETH"),
        ("ET-27MAR26-CDE", "ETH"),
        ("ETP-20DEC30-CDE", "ETH"),
        ("SOL-27FEB26-CDE", "SOL"),
        ("SOL-27MAR26-CDE", "SOL"),
        ("SLP-20DEC30-CDE", "SOL"),
    ]

    success = 0

    for contract, asset in contracts:
        df = download_futures(contract, days=30)

        if df is not None and len(df) > 100:
            filename = f"{contract}_FIVE_MINUTE.csv"
            filepath = OUTPUT_DIR / filename
            df.to_csv(filepath, index=False)
            print(f"      💾 Guardado: {filename}")
            success += 1

        time.sleep(0.5)

    print()
    print("=" * 70)
    print(f"✅ {success} contratos descargados")
    print(f"📁 Directorio: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
