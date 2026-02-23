#!/usr/bin/env python3
"""
Descargador de TODOS los datos de futuros de Coinbase
Descarga los contratos más líquidos de cada activo
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


def download_futures(product_id, days=30):
    """Descarga datos de futuros en chunks de 1 día"""
    all_candles = []
    end = int(time.time())

    for i in range(days):
        chunk_end = end - (i * 86400)
        chunk_start = chunk_end - 86400

        path = f"/api/v3/brokerage/products/{product_id}/candles"
        jwt = make_jwt("GET", path)
        url = f"{API_URL}{path}?start={chunk_start}&end={chunk_end}&granularity=FIVE_MINUTE"
        headers = {"Authorization": f"Bearer {jwt}"}

        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                candles = resp.json().get("candles", [])
                all_candles.extend(candles)
        except:
            pass

        time.sleep(0.2)

    if not all_candles:
        return None

    # Convertir a DataFrame
    df = pd.DataFrame(all_candles)
    df = df.rename(columns={"start": "timestamp"})
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="s")

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.drop_duplicates(subset=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    return df


def main():
    print("=" * 70)
    print("📥 DESCARGANDO TODOS LOS DATOS DE FUTUROS")
    print("=" * 70)
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Contratos a descargar - los más líquidos de cada activo
    # Prioridad: Perpetuals > Cercanos a vencer
    contracts = [
        # Crypto principales
        ("BIP-20DEC30-CDE", "BTC", "Perpetual"),
        ("BIT-27FEB26-CDE", "BTC", "Feb26"),
        ("BIT-27MAR26-CDE", "BTC", "Mar26"),

        ("ETP-20DEC30-CDE", "ETH", "Perpetual"),
        ("ET-27FEB26-CDE", "ETH", "Feb26"),
        ("ET-27MAR26-CDE", "ETH", "Mar26"),

        ("SLP-20DEC30-CDE", "SOL", "Perpetual"),
        ("SOL-27FEB26-CDE", "SOL", "Feb26"),
        ("SOL-27MAR26-CDE", "SOL", "Mar26"),

        # Altcoins principales
        ("XPP-20DEC30-CDE", "XRP", "Perpetual"),
        ("XRP-27FEB26-CDE", "XRP", "Feb26"),

        ("ADP-20DEC30-CDE", "ADA", "Perpetual"),
        ("ADA-27FEB26-CDE", "ADA", "Feb26"),

        ("DOP-20DEC30-CDE", "DOT", "Perpetual"),
        ("DOT-27FEB26-CDE", "DOT", "Feb26"),

        ("LNP-20DEC30-CDE", "LINK", "Perpetual"),
        ("LNK-27FEB26-CDE", "LINK", "Feb26"),

        ("AVP-20DEC30-CDE", "AVAX", "Perpetual"),
        ("AVA-27FEB26-CDE", "AVAX", "Feb26"),

        ("DOG-27FEB26-CDE", "DOGE", "Feb26"),
        ("DOP-20DEC30-CDE", "DOGE", "Perpetual"),  # Conflicto con DOT, verificar

        ("SUI-27FEB26-CDE", "SUI", "Feb26"),
        ("SUI-27MAR26-CDE", "SUI", "Mar26"),

        ("XLP-20DEC30-CDE", "XLM", "Perpetual"),
        ("XLM-27FEB26-CDE", "XLM", "Feb26"),

        ("HED-27FEB26-CDE", "HED", "Feb26"),
        ("HEP-20DEC30-CDE", "HED", "Perpetual"),

        ("SHB-27FEB26-CDE", "SHIB", "Feb26"),

        ("LCP-20DEC30-CDE", "LTC", "Perpetual"),
        ("LC-27FEB26-CDE", "LTC", "Feb26"),

        ("BCH-27FEB26-CDE", "BCH", "Feb26"),

        # Commodities
        ("GOL-27MAR26-CDE", "GOLD", "Mar26"),
        ("NOL-19MAR26-CDE", "OIL", "Mar26"),
        ("NGS-24FEB26-CDE", "NATGAS", "Feb26"),
        ("CU-25FEB26-CDE", "COPPER", "Feb26"),
        ("PT-27MAR26-CDE", "PLATINUM", "Mar26"),

        # Indices
        ("MC-19MAR26-CDE", "SP500", "Mar26"),
    ]

    # Eliminar duplicados
    seen = set()
    unique_contracts = []
    for c in contracts:
        if c[0] not in seen:
            seen.add(c[0])
            unique_contracts.append(c)

    print(f"📋 Contratos a descargar: {len(unique_contracts)}")
    print()

    success = 0
    failed = 0
    results = []

    for contract, asset, expiry in unique_contracts:
        print(f"  {contract} ({asset})...", end=" ", flush=True)

        df = download_futures(contract, days=30)

        if df is not None and len(df) > 50:
            filename = f"{contract}_FIVE_MINUTE.csv"
            filepath = OUTPUT_DIR / filename
            df.to_csv(filepath, index=False)

            last_price = df["close"].iloc[-1]
            print(f"✅ {len(df)} velas, ${last_price:,.2f}")
            results.append((contract, asset, len(df), last_price))
            success += 1
        else:
            print(f"❌ Sin datos suficientes")
            failed += 1

        time.sleep(0.3)

    print()
    print("=" * 70)
    print(f"✅ COMPLETADO: {success} exitosos, {failed} fallidos")
    print("=" * 70)
    print()
    print("📊 RESUMEN POR ACTIVO:")
    print("-" * 70)

    by_asset = {}
    for contract, asset, candles, price in results:
        if asset not in by_asset:
            by_asset[asset] = []
        by_asset[asset].append((contract, candles, price))

    for asset in sorted(by_asset.keys()):
        contracts = by_asset[asset]
        total_candles = sum(c[1] for c in contracts)
        prices = [c[2] for c in contracts]
        print(f"  {asset:10} | {len(contracts)} contratos | {total_candles:,} velas | ~${prices[-1]:,.2f}")

    print()
    print(f"📁 Directorio: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
