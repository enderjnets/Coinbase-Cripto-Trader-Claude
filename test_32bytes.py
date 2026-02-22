#!/usr/bin/env python3
"""
COINBASE API - PRUEBA CON 32 BYTES
Usa solo los primeros 32 bytes como Ed25519 private key
"""

import base64
import json
import time

# Cargar la key
with open("/Users/enderj/Downloads/cdp_api_key.json") as f:
    data = json.load(f)

API_KEY_ID = data["id"]
KEY_B64 = data["privateKey"]

# Decodificar - tomar solo 32 bytes (Ed25519 private key)
KEY_BYTES = base64.b64decode(KEY_B64)[:32]

print("="*60)
print("COINBASE API - SOLO 32 BYTES")
print("="*60)
print(f"\nAPI Key: {API_KEY_ID}")
print(f"Key bytes: {len(KEY_BYTES)} (Ed25519 requiere 32)")
print(f"Hex: {KEY_BYTES.hex()[:40]}...")

# Probar con cryptography
try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    
    # Crear private key
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(KEY_BYTES)
    print(f"\n✅ Private key cargada!")
    
    # Firmar mensaje
    message = b"test"
    signature = private_key.sign(message)
    print(f"✅ Mensaje firmado ({len(signature)} bytes)")
    
    # Verificar
    public = private_key.public_key()
    public.verify(signature, message)
    print("✅ Firma verificada!")
    
    print("\n🎉 La key FUNCIONA para firmar!")
    print("El problema es la autenticacion de Coinbase.")
    
except ImportError:
    print("\n⚠️ cryptography no instalado")
    print("pip install cryptography")
except Exception as e:
    print(f"\n❌ Error: {e}")
