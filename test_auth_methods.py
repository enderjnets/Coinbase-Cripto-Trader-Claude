#!/usr/bin/env python3
"""
COINBASE API - METODOS ALTERNATIVOS DE AUTENTICACION
"""

import os
import sys
import time
import json
import base64
import urllib.request

# Cargar API Key
API_KEY_FILE = "/Users/enderj/Downloads/cdp_api_key.json"

with open(API_KEY_FILE, 'r') as f:
    data = json.load(f)

API_KEY_ID = data['id']
PRIVATE_KEY_B64 = data['privateKey']
PRIVATE_KEY_FULL = base64.b64decode(PRIVATE_KEY_B64)
PRIVATE_KEY = PRIVATE_KEY_FULL[:32]

print("="*60)
print("COINBASE API - METODOS DE AUTENTICACION")
print("="*60)
print(f"\nAPI Key ID: {API_KEY_ID}")

# Metodo 1: Solo con API Key
print("\n" + "="*60)
print("METODO 1: Solo API Key (CB-ACCESS-KEY header)")
print("="*60)

url = "https://api.coinbase.com/api/v3/brokerage/products"
headers = {
    "Accept": "application/json",
    "CB-ACCESS-KEY": API_KEY_ID,
}
print(f"Headers: {headers}")

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode())
        print(f"\n✅ METODO 1 FUNCIONO!")
        products = data.get("products", [])
        print(f"   {len(products)} productos")
except Exception as e:
    print(f"❌ Fallo: {type(e).__name__}")

# Metodo 2: API Key + Timestamp
print("\n" + "="*60)
print("METODO 2: API Key + Timestamp")
print("="*60)

timestamp = str(int(time.time()))
headers2 = {
    "Accept": "application/json",
    "CB-ACCESS-KEY": API_KEY_ID,
    "CB-ACCESS-SIGN": timestamp,  # Firmar timestamp
    "CB-ACCESS-TIMESTAMP": timestamp,
}
print(f"Headers: {headers2}")

try:
    req = urllib.request.Request(url, headers=headers2)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode())
        print(f"\n✅ METODO 2 FUNCIONO!")
except Exception as e:
    print(f"❌ Fallo: {type(e).__name__}")

# Metodo 3: Bearer Token (sin JWT)
print("\n" + "="*60)
print("METODO 3: Bearer Token (solo API Key)")
print("="*60)

headers3 = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_KEY_ID}",
}
print(f"Headers: Authorization: Bearer {API_KEY_ID[:20]}...")

try:
    req = urllib.request.Request(url, headers=headers3)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode())
        print(f"\n✅ METODO 3 FUNCIONO!")
        products = data.get("products", [])
        for p in products[:5]:
            if p.get("status") == "online":
                print(f"   {p.get('product_id')}")
except Exception as e:
    print(f"❌ Fallo: {type(e).__name__}: {e}")

print("\n" + "="*60)
print("NOTA")
print("="*60)
print("""
Los endpoints de futuros regulados (CFM) requieren JWT completo.
Los endpoints publicos de productos pueden tener restricciones.

Para datos OHLCV historicos, se necesita la API de Advanced Trade.
""")
