#!/usr/bin/env python3
"""
PRUEBA DE API KEY DE COINBASE

Usa la API Key y Private Key para hacer una solicitud autenticada.
"""

import os
import sys
import time
import json
import base64
import urllib.request
from datetime import datetime
from urllib.parse import urlencode

# Cargar API Key del archivo
API_KEY_FILE = "/Users/enderj/Downloads/cdp_api_key.json"

def load_api_keys():
    """Carga API keys desde el archivo JSON"""
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, 'r') as f:
            data = json.load(f)
            return data.get('id'), data.get('privateKey')
    return None, None

API_KEY, PRIVATE_KEY = load_api_keys()

print("="*60)
print("PRUEBA DE API KEY DE COINBASE")
print("="*60)
print(f"\nAPI Key ID: {API_KEY}")
if PRIVATE_KEY:
    print(f"Private Key: {PRIVATE_KEY[:30]}...")
else:
    print("Private Key: None")

print("\n" + "="*60)
print("PRUEBA DE CONEXION")
print("="*60)

# Endpoint publico de Coinbase
url = "https://api.coinbase.com/api/v3/brokerage/products"

headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

print(f"\nURL: {url}")
print(f"Headers: Authorization = Bearer {API_KEY[:20]}...")

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode())
        
        print("\nCONEXION EXITOSA!")
        print(f"\nProductos disponibles:")
        
        products = data.get("products", [])[:10]
        for p in products:
            if p.get("status") == "online":
                print(f"  {p.get('product_id'):20} | ${p.get('price', 'N/A')}")
        
        print(f"\n... ({len(data.get('products', []))} productos)")
        
except urllib.error.HTTPError as e:
    print(f"\nHTTP Error: {e.code} - {e.reason}")
    body = e.read().decode()[:500]
    print(f"Body: {body}")
except Exception as e:
    print(f"\nError: {e}")

print("\n" + "="*60)
print("NOTA")
print("="*60)
print("""
Para la API de futuros, se necesita JWT token firmado con Ed25519.
La private key del archivo parece estar codificada (Base64).

Si la conexion falla, se necesita la Private Key en formato PEM:
-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
""")
