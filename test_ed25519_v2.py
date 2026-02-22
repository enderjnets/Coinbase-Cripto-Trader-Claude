#!/usr/bin/env python3
"""
COINBASE API CON ED25519 - LLAVE REAL v2.0

Usa la Private Key del archivo JSON (64 bytes = 32 privados + 32 públicos)
"""

import os
import sys
import time
import json
import base64
import urllib.request
from datetime import datetime

# Cargar API Key
API_KEY_FILE = "/Users/enderj/Downloads/cdp_api_key.json"

with open(API_KEY_FILE, 'r') as f:
    data = json.load(f)

API_KEY_ID = data['id']
PRIVATE_KEY_B64 = data['privateKey']

# Decodificar - son 64 bytes (32 private + 32 public)
PRIVATE_KEY_FULL = base64.b64decode(PRIVATE_KEY_B64)
PRIVATE_KEY = PRIVATE_KEY_FULL[:32]  # Solo los primeros 32 bytes son la clave privada

print("="*60)
print("COINBASE API - LLAVE REAL")
print("="*60)
print(f"\nAPI Key ID: {API_KEY_ID}")
print(f"Private Key: 32 bytes (Ed25519)")

# Intentar crear JWT con la clave
try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    
    # Cargar la clave privada (solo 32 bytes)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(PRIVATE_KEY)
    
    print(f"\n✅ Clave privada cargada correctamente!")
    print(f"   Tipo: Ed25519")
    
    # Obtener clave publica
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    print(f"   Public Key: {len(public_pem)} bytes (PEM)")
    
    # Probar endpoint
    print(f"\n" + "="*60)
    print("PROBANDO CONEXION")
    print("="*60)
    
    # Crear JWT
    now = int(time.time())
    exp = now + 120
    
    # Header y Payload del JWT
    header = {"alg": "EdDSA", "typ": "JWT"}
    payload = {
        "iss": "cdp",
        "nbf": now,
        "exp": exp,
        "sub": API_KEY_ID,
        "uri": "GET api.coinbase.com/api/v3/brokerage/products"
    }
    
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b'=').decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=').decode()
    
    message = f"{header_b64}.{payload_b64}"
    
    # Firmar con Ed25519
    signature = private_key.sign(message.encode())
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()
    
    jwt_token = f"{message}.{signature_b64}"
    
    print(f"\nJWT Token creado:")
    print(f"   Length: {len(jwt_token)} caracteres")
    
    # Probar endpoint
    url = "https://api.coinbase.com/api/v3/brokerage/products"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {jwt_token}"
    }
    
    print(f"\nProbando: {url}")
    
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode())
        
        print(f"\n✅ CONEXION EXITOSA!")
        print(f"\nProductos disponibles:")
        
        products = data.get("products", [])
        count = 0
        for p in products:
            if p.get("status") == "online" and count < 10:
                print(f"   {p.get('product_id', ''):25} | {p.get('quote_currency_id', ''):5} | ${p.get('price', 'N/A')}")
                count += 1
        
        if len(products) > 10:
            print(f"   ... ({len(products)} productos)")
        
        # Guardar productos para usar despues
        with open("coinbase_products.json", "w") as f:
            json.dump(products, f, indent=2)
        print(f"\n💾 Productos guardados: coinbase_products.json")
        
except ImportError as e:
    print(f"\n⚠️ cryptography no instalado:")
    print(f"   {e}")
    print(f"\n   pip install cryptography")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
