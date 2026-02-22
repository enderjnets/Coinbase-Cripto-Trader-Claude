#!/usr/bin/env python3
"""
PRUEBA DIRECTA CON BASE64 KEY
"""

import os
import json
import base64
import urllib.request

# Cargar la key del JSON
with open("/Users/enderj/Downloads/cdp_api_key.json") as f:
    data = json.load(f)

API_KEY_ID = data["id"]
PRIVATE_KEY_B64 = data["privateKey"]

print("="*60)
print("PRUEBA DIRECTA CON BASE64 KEY")
print("="*60)
print(f"\nAPI Key ID: {API_KEY_ID}")
print(f"Private Key: {PRIVATE_KEY_B64[:30]}...")
print(f"Private Key Length: {len(PRIVATE_KEY_B64)} chars")

# Probar diferentes metodos de autenticacion
URLS = [
    "https://api.coinbase.com/api/v3/time",
    "https://api.coinbase.com/api/v3/brokerage/products",
]

# Metodo 1: Solo API Key ID
print("\n" + "="*60)
print("METODO 1: API Key ID como Bearer")
print("="*60)

for url in URLS:
    try:
        headers = {"Authorization": f"Bearer {API_KEY_ID}"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"  ✅ {url.split('/')[-1]}: OK")
    except Exception as e:
        print(f"  ❌ {url.split('/')[-1]}: {type(e).__name__}")

# Metodo 2: Basic Auth (ID:Base64Key)
print("\n" + "="*60)
print("METODO 2: Basic Auth (ID:Base64Key)")
print("="*60)

creds = f"{API_KEY_ID}:{PRIVATE_KEY_B64}"
encoded = base64.b64encode(creds.encode()).decode()

for url in URLS:
    try:
        headers = {"Authorization": f"Basic {encoded}"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"  ✅ {url.split('/')[-1]}: OK")
    except Exception as e:
        print(f"  ❌ {url.split('/')[-1]}: {type(e).__name__}")

# Metodo 3: API Key como password vacio
print("\n" + "="*60)
print("METODO 3: API Key como password")
print("="*60)

creds = f":{API_KEY_ID}"
encoded = base64.b64encode(creds.encode()).decode()

for url in URLS:
    try:
        headers = {"Authorization": f"Basic {encoded}"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"  ✅ {url.split('/')[-1]}: OK")
    except Exception as e:
        print(f"  ❌ {url.split('/')[-1]}: {type(e).__name__}")

print("\n" + "="*60)
print("NOTA")
print("="*60)
print("""
La key del JSON parece ser una "Client API Key" que no es
la misma que la "Advanced Trade API Key" para futuros.

Para futuros, se necesita:
1. API Key de Advanced Trade
2. Private Key en formato PEM (-----BEGIN PRIVATE KEY-----)
3. JWT firmado con Ed25519

Verificar en: https://portal.coinbase.com/portal/api-keys
""")
