#!/usr/bin/env python3
"""
COINBASE API - ULTIMATE AUTHENTICATION TEST v1.0

Prueba todos los métodos de autenticación posibles.
"""

import os
import sys
import time
import json
import base64
import hmac
import hashlib
import urllib.request
from datetime import datetime
from urllib.parse import urlencode

# Cargar API Key
API_KEY_FILE = "/Users/enderj/Downloads/cdp_api_key.json"

with open(API_KEY_FILE, 'r') as f:
    data = json.load(f)

API_KEY_ID = data['id']
PRIVATE_KEY_B64 = data['privateKey']
PRIVATE_KEY_32 = base64.b64decode(PRIVATE_KEY_B64)[:32]

print("="*60)
print("COINBASE API - ULTIMATE AUTH TEST")
print("="*60)
print(f"\nAPI Key ID: {API_KEY_ID}")
print(f"Private Key: {len(PRIVATE_KEY_B64)} chars (Base64)")
print(f"Private Key: {len(PRIVATE_KEY_32)} bytes (Ed25519)")

# URLs a probar
URLS = [
    ("Products", "https://api.coinbase.com/api/v3/brokerage/products"),
    ("Accounts", "https://api.coinbase.com/api/v3/accounts"),
    ("Time", "https://api.coinbase.com/api/v3/time"),
]

# Metodo 1: Solo API Key
print("\n" + "="*60)
print("METODO 1: CB-ACCESS-KEY")
print("="*60)

for name, url in URLS:
    try:
        headers = {"CB-ACCESS-KEY": API_KEY_ID}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read().decode()
            print(f"  ✅ {name}: OK")
    except Exception as e:
        print(f"  ❌ {name}: {type(e).__name__}")

# Metodo 2: API Key + Timestamp
print("\n" + "="*60)
print("METODO 2: CB-ACCESS-KEY + SIGNATURE")
print("="*60)

timestamp = str(int(time.time()))
for name, url in URLS:
    try:
        # Crear signature
        message = timestamp + "GET" + url.replace("https://api.coinbase.com", "")
        signature = hmac.new(
            PRIVATE_KEY_32,
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "CB-ACCESS-KEY": API_KEY_ID,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read().decode()
            print(f"  ✅ {name}: OK")
    except Exception as e:
        print(f"  ❌ {name}: {type(e).__name__}")

# Metodo 3: Bearer Token
print("\n" + "="*60)
print("METODO 3: Bearer Token")
print("="*60)

for name, url in URLS:
    try:
        headers = {"Authorization": f"Bearer {API_KEY_ID}"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read().decode()
            print(f"  ✅ {name}: OK")
    except Exception as e:
        print(f"  ❌ {name}: {type(e).__name__}")

# Metodo 4: Basic Auth
print("\n" + "="*60)
print("METODO 4: Basic Auth (API Key + Secret)")
print("="*60)

# Crear credenciales Basic
credentials = f"{API_KEY_ID}:{PRIVATE_KEY_B64}"
encoded = base64.b64encode(credentials.encode()).decode()

for name, url in URLS:
    try:
        headers = {"Authorization": f"Basic {encoded}"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read().decode()
            print(f"  ✅ {name}: OK")
    except Exception as e:
        print(f"  ❌ {name}: {type(e).__name__}")

# Metodo 5: Solo URL publica
print("\n" + "="*60)
print("METODO 5: Sin autenticacion (URLs publicas)")
print("="*60)

PUBLIC_URLS = [
    ("Coinbase Time", "https://api.coinbase.com/api/v3/time"),
    ("Public Products", "https://api.coinbase.com/api/v3/brokerage/products"),
]

for name, url in PUBLIC_URLS:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read().decode()
            print(f"  ✅ {name}: OK")
    except Exception as e:
        print(f"  ❌ {name}: {type(e).__name__}")

print("\n" + "="*60)
print("CONCLUSION")
print("="*60)
print("""
Si ninguno funciono, la API Key puede tener:
- Restricciones de IP
- Permisos insuficientes
- Expirada
- Revocada

Verificar en: https://portal.coinbase.com/portal/api-keys
""")
