#!/usr/bin/env python3
"""
live_spot_executor.py - Spot Trading Executor for Coinbase
==========================================================

Executes real spot trades on Coinbase Advanced Trade API.
Adapted from live_futures_executor.py without leverage/margin/liquidation.

Features:
- Authenticated API connection
- Market buy/sell orders
- Account balance queries
- Kill switch (close all positions)
- dry_run=True by default (ALWAYS)

Usage:
    from live_spot_executor import LiveSpotExecutor
    executor = LiveSpotExecutor(dry_run=True)  # ALWAYS start with dry_run
    balance = executor.get_available_balance("USD")
    result = executor.place_market_buy("BTC-USD", quote_size=100)
"""

import os
import json
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass
import requests

from coinbase_auth import CoinbaseAuth, COINBASE_API_URL, API_KEY_PATH

# ============================================================================
# ENDPOINTS
# ============================================================================

ENDPOINTS = {
    'accounts': '/api/v3/brokerage/accounts',
    'orders': '/api/v3/brokerage/orders',
    'products': '/api/v3/brokerage/products',
    'fills': '/api/v3/brokerage/orders/historical/fills',
}

# Rate limits
RATE_LIMIT_DELAY = 0.1  # 100ms between requests


@dataclass
class SpotTrade:
    """Record of a spot trade."""
    trade_id: str
    product_id: str
    side: str  # BUY or SELL
    size: float
    price: float
    fee: float
    timestamp: float
    dry_run: bool


class LiveSpotExecutor:
    """
    Spot trading executor for Coinbase.

    No leverage, no margin, no liquidation. Simple buy/sell.
    dry_run=True by default - ALWAYS.
    """

    def __init__(self, api_key_path: str = API_KEY_PATH, dry_run: bool = True):
        """
        Args:
            api_key_path: Path to Coinbase API key JSON
            dry_run: If True, simulates all orders (default: True)
        """
        self.auth = CoinbaseAuth(api_key_path)
        self.dry_run = dry_run
        self.session = requests.Session()
        self.last_request_time = 0

        # Trade history
        self.trades: List[SpotTrade] = []

        # Cached balances
        self._balances: Dict[str, float] = {}

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

    def _request(self, method: str, path: str, data: dict = None) -> dict:
        """Make authenticated API request."""
        self._rate_limit()

        url = f"{COINBASE_API_URL}{path}"
        headers = self.auth.get_headers(method, path)

        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=30)
            else:
                return {"error": f"Unsupported method: {method}"}

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}", "body": response.text}

        except Exception as e:
            return {"error": str(e)}

    # ========== ACCOUNT METHODS ==========

    def get_accounts(self) -> List[Dict]:
        """Get all account balances."""
        result = self._request("GET", ENDPOINTS['accounts'])

        if "error" in result:
            print(f"Error getting accounts: {result['error']}")
            return []

        accounts = []
        self._balances.clear()

        for acc in result.get("accounts", []):
            currency = acc.get("currency", "")
            available = float(acc.get("available_balance", {}).get("value", 0))
            hold = float(acc.get("hold", {}).get("value", 0))
            total = available + hold

            if total > 0:
                accounts.append({
                    'currency': currency,
                    'available': available,
                    'hold': hold,
                    'total': total,
                    'uuid': acc.get('uuid', ''),
                })
                self._balances[currency] = available

        return accounts

    def get_available_balance(self, currency: str = "USD") -> float:
        """Get available balance for a specific currency."""
        if not self._balances:
            self.get_accounts()
        return self._balances.get(currency, 0.0)

    # ========== ORDER METHODS ==========

    def place_market_buy(self, product_id: str, quote_size: float) -> Dict:
        """
        Place a market buy order (buy crypto with USD).

        Args:
            product_id: Trading pair (e.g., "BTC-USD")
            quote_size: Amount in USD to spend

        Returns:
            Dict with order result
        """
        if quote_size < 1.0:
            return {"success": False, "error": "Minimum order size is $1"}

        # Check balance
        usd_balance = self.get_available_balance("USD")
        if quote_size > usd_balance and not self.dry_run:
            return {"success": False, "error": f"Insufficient USD. Available: ${usd_balance:.2f}"}

        if self.dry_run:
            trade_id = f"DRY-BUY-{int(time.time()*1000)}"
            print(f"[DRY RUN] BUY ${quote_size:.2f} of {product_id}")
            self.trades.append(SpotTrade(
                trade_id=trade_id,
                product_id=product_id,
                side="BUY",
                size=quote_size,
                price=0,
                fee=quote_size * 0.004,
                timestamp=time.time(),
                dry_run=True,
            ))
            return {"success": True, "dry_run": True, "order_id": trade_id}

        # Real order
        client_order_id = f"SM-{uuid.uuid4().hex[:12]}"
        payload = {
            "client_order_id": client_order_id,
            "product_id": product_id,
            "side": "BUY",
            "order_configuration": {
                "market_market_ioc": {
                    "quote_size": str(round(quote_size, 2))
                }
            }
        }

        result = self._request("POST", ENDPOINTS['orders'], payload)

        if "error" in result:
            return {"success": False, "error": result["error"]}

        order_id = result.get("order_id", result.get("success_response", {}).get("order_id", ""))
        success = result.get("success", False)

        if success:
            self.trades.append(SpotTrade(
                trade_id=order_id,
                product_id=product_id,
                side="BUY",
                size=quote_size,
                price=0,
                fee=0,
                timestamp=time.time(),
                dry_run=False,
            ))

        return {"success": success, "order_id": order_id, "response": result}

    def place_market_sell(self, product_id: str, base_size: float) -> Dict:
        """
        Place a market sell order (sell crypto for USD).

        Args:
            product_id: Trading pair (e.g., "BTC-USD")
            base_size: Amount of crypto to sell

        Returns:
            Dict with order result
        """
        if base_size <= 0:
            return {"success": False, "error": "Size must be positive"}

        # Check balance
        crypto = product_id.split("-")[0]
        crypto_balance = self.get_available_balance(crypto)
        if base_size > crypto_balance and not self.dry_run:
            return {"success": False, "error": f"Insufficient {crypto}. Available: {crypto_balance}"}

        if self.dry_run:
            trade_id = f"DRY-SELL-{int(time.time()*1000)}"
            print(f"[DRY RUN] SELL {base_size} {crypto} on {product_id}")
            self.trades.append(SpotTrade(
                trade_id=trade_id,
                product_id=product_id,
                side="SELL",
                size=base_size,
                price=0,
                fee=0,
                timestamp=time.time(),
                dry_run=True,
            ))
            return {"success": True, "dry_run": True, "order_id": trade_id}

        # Real order
        client_order_id = f"SM-{uuid.uuid4().hex[:12]}"
        payload = {
            "client_order_id": client_order_id,
            "product_id": product_id,
            "side": "SELL",
            "order_configuration": {
                "market_market_ioc": {
                    "base_size": str(base_size)
                }
            }
        }

        result = self._request("POST", ENDPOINTS['orders'], payload)

        if "error" in result:
            return {"success": False, "error": result["error"]}

        order_id = result.get("order_id", result.get("success_response", {}).get("order_id", ""))
        success = result.get("success", False)

        if success:
            self.trades.append(SpotTrade(
                trade_id=order_id,
                product_id=product_id,
                side="SELL",
                size=base_size,
                price=0,
                fee=0,
                timestamp=time.time(),
                dry_run=False,
            ))

        return {"success": success, "order_id": order_id, "response": result}

    def close_all_positions(self) -> List[Dict]:
        """
        Kill switch: sell all crypto holdings back to USD.

        Returns:
            List of sell order results
        """
        results = []
        accounts = self.get_accounts()

        for acc in accounts:
            currency = acc['currency']
            # Skip USD and stablecoins
            if currency in ('USD', 'USDC', 'USDT'):
                continue

            available = acc['available']
            if available <= 0:
                continue

            product_id = f"{currency}-USD"
            print(f"[KILL SWITCH] Selling {available} {currency}...")

            result = self.place_market_sell(product_id, available)
            results.append({
                'currency': currency,
                'amount': available,
                'result': result,
            })

        return results

    # ========== STATUS ==========

    def get_status(self) -> Dict:
        """Get executor status."""
        accounts = self.get_accounts()
        usd = self.get_available_balance("USD")

        return {
            "dry_run": self.dry_run,
            "usd_balance": usd,
            "accounts": len(accounts),
            "total_trades": len(self.trades),
            "holdings": {
                a['currency']: a['available']
                for a in accounts
                if a['available'] > 0
            }
        }


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("LIVE SPOT EXECUTOR - TEST (dry_run=True)")
    print("=" * 60)

    executor = LiveSpotExecutor(dry_run=True)

    # Get accounts
    print("\nFetching accounts...")
    accounts = executor.get_accounts()
    for acc in accounts:
        print(f"  {acc['currency']}: {acc['available']:.8f} (hold: {acc['hold']:.8f})")

    usd = executor.get_available_balance("USD")
    print(f"\nUSD Available: ${usd:.2f}")

    # Test dry run buy
    print("\nDry run: BUY $10 of BTC-USD")
    result = executor.place_market_buy("BTC-USD", 10.0)
    print(f"  Result: {result}")

    # Test dry run sell
    btc = executor.get_available_balance("BTC")
    if btc > 0:
        print(f"\nDry run: SELL {btc:.8f} BTC")
        result = executor.place_market_sell("BTC-USD", btc)
        print(f"  Result: {result}")

    # Status
    print(f"\nStatus: {json.dumps(executor.get_status(), indent=2)}")
    print("\nDone!")
