#!/usr/bin/env python3
"""
coinbase_auth.py - Shared Coinbase JWT Authentication
=====================================================

Extracted from live_futures_executor.py for use by both
futures and spot executors.

Usage:
    from coinbase_auth import CoinbaseAuth
    auth = CoinbaseAuth()
    headers = auth.get_headers("GET", "/api/v3/brokerage/accounts")
"""

import os
import json
import time
import base64
from typing import Dict, Tuple

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# Default API key path
API_KEY_PATH = "/Users/enderj/Downloads/cdp_api_key.json"
COINBASE_API_URL = "https://api.coinbase.com"


class CoinbaseAuth:
    """JWT Ed25519 authentication for Coinbase Advanced Trade API."""

    def __init__(self, api_key_path: str = API_KEY_PATH):
        if not HAS_CRYPTO:
            raise ImportError("cryptography required: pip install cryptography")
        self.api_key, self.private_key = self._load_key(api_key_path)

    def _load_key(self, path: str) -> Tuple[str, 'Ed25519PrivateKey']:
        """Load API key from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)

        key_id = data['id']
        private_key_b64 = data['privateKey']

        # Decode base64 - first 32 bytes are the Ed25519 seed
        raw = base64.b64decode(private_key_b64)
        seed = raw[:32]
        private_key = Ed25519PrivateKey.from_private_bytes(seed)

        return key_id, private_key

    def generate_jwt(self, method: str, path: str) -> str:
        """Generate JWT for API authentication."""
        now = int(time.time())

        # URI without https://
        uri = f"{method} api.coinbase.com{path}"

        header = {
            "alg": "EdDSA",
            "kid": self.api_key,
            "typ": "JWT",
            "nonce": now
        }

        payload = {
            "iss": "cdp",
            "nbf": now,
            "exp": now + 120,
            "sub": self.api_key,
            "uri": uri
        }

        def b64url(data):
            if isinstance(data, str):
                data = data.encode()
            return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

        header_b64 = b64url(json.dumps(header, separators=(',', ':')))
        payload_b64 = b64url(json.dumps(payload, separators=(',', ':')))

        message = f"{header_b64}.{payload_b64}".encode()
        signature = self.private_key.sign(message)
        signature_b64 = b64url(signature)

        return f"{message.decode()}.{signature_b64}"

    def get_headers(self, method: str, path: str) -> Dict[str, str]:
        """Get authenticated request headers."""
        return {
            "Authorization": f"Bearer {self.generate_jwt(method, path)}",
            "Content-Type": "application/json"
        }
