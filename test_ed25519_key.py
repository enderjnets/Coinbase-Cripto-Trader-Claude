#!/usr/bin/env python3
"""
COINBASE API CON ED25519 - LLAVE REAL v1.0

Usa la Private Key del archivo JSON para crear JWT y acceder a la API.
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

# Decodificar la private key (64 bytes = Ed25519)
PRIVATE_KEY_BYTES = base64.b64decode(PRIVATE_KEY_B64)

print("="*60)
print("COINBASE API - LLAVE REAL")
print("="*60)
print(f"\nAPI Key ID: {API_KEY_ID}")
print(f"Private Key: {len(PRIVATE_KEY_B64)} caracteres (Base64)")
print(f"Private Key: {len(PRIVATE_KEY_BYTES)} bytes (Ed25519)")

# Intentar crear JWT con la clave
try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    
    # Cargar la clave privada
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(PRIVATE_KEY_BYTES)
    
    print(f"\n✅ Clave privada cargada correctamente!")
    print(f"   Tipo: Ed25519")
    
    # Obtener clave publica
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    print(f"   Public Key: {len(public_bytes)} bytes")
    
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
    print(f"   Header: {header_b64[:30]}...")
    print(f"   Payload: {payload_b64[:30]}...")
    print(f"   Signature: {signature_b64[:30]}...")
    
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
        for p in products[:10]:
            if p.get("status") == "online":
                print(f"   {p.get('product_id', ''):20} | ${p.get('price', 'N/A')}")
        
        if len(products) > 10:
            print(f"   ... ({len(products)} productos)")
        
except ImportError as e:
    print(f"\n⚠️  cryptography no instalado:")
    print(f"   {e}")
    print(f"\n   Instalar con:")
    print(f"   pip install cryptography")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
