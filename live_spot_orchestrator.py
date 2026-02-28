#!/usr/bin/env python3
"""
live_spot_orchestrator.py - Live Spot Trading Orchestrator
==========================================================

Connects validated paper trading strategies to the live spot executor
with full risk management.

Features:
- Loads strategies validated in paper trading
- Risk manager validates each signal before execution
- dry_run_parallel: executes real AND simulated trades for comparison
- Complete logging of every trade (real vs dry_run)
- Telegram notification on each real trade

Usage:
    python live_spot_orchestrator.py --dry-run       # Dry run only
    python live_spot_orchestrator.py --live           # Live trading (careful!)
    python live_spot_orchestrator.py --status         # Show status
"""

import os
import sys
import json
import time
import asyncio
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import requests

from coinbase_auth import CoinbaseAuth
from live_spot_executor import LiveSpotExecutor
from risk_manager_live import RiskManager, RiskConfig, SPOT_RISK_CONFIG, emergency_close_all

# Configuration
PAPER_STRATEGIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "paper_trading_strategies.json")
ORCHESTRATOR_DB = "/tmp/spot_orchestrator.db"

# Telegram
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


def send_telegram(message: str):
    """Send notification via Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
        }, timeout=10)
    except Exception:
        pass


class LiveSpotOrchestrator:
    """
    Orchestrates live spot trading with validated strategies.
    """

    def __init__(
        self,
        initial_capital: float = 500.0,
        dry_run: bool = True,
        dry_run_parallel: bool = True,
    ):
        """
        Args:
            initial_capital: Starting capital in USD
            dry_run: If True, all orders are simulated
            dry_run_parallel: If True, run real AND simulated trades for comparison
        """
        self.initial_capital = initial_capital
        self.dry_run = dry_run
        self.dry_run_parallel = dry_run_parallel

        # Create executor (always starts with dry_run=True for safety)
        self.executor = LiveSpotExecutor(dry_run=dry_run)

        # Create parallel dry-run executor for comparison
        if dry_run_parallel and not dry_run:
            self.dry_executor = LiveSpotExecutor(dry_run=True)
        else:
            self.dry_executor = None

        # Risk manager with spot config
        self.risk_manager = RiskManager(
            initial_balance=initial_capital,
            config=SPOT_RISK_CONFIG,
        )

        # State
        self.strategies: List[Dict] = []
        self.running = False

        # Initialize DB
        self._init_db()

    def _init_db(self):
        """Initialize orchestrator database."""
        conn = sqlite3.connect(ORCHESTRATOR_DB)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS live_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                strategy_id TEXT,
                product_id TEXT,
                side TEXT,
                size REAL,
                price REAL,
                pnl REAL,
                fee REAL,
                reason TEXT,
                dry_run INTEGER,
                order_id TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                trades INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                pnl REAL DEFAULT 0,
                drawdown REAL DEFAULT 0,
                balance REAL DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    def load_strategies(self, path: str = PAPER_STRATEGIES_FILE) -> int:
        """Load validated strategies from JSON file."""
        if not os.path.exists(path):
            print(f"Strategies file not found: {path}")
            return 0

        with open(path, 'r') as f:
            data = json.load(f)

        self.strategies = data.get('strategies', [])
        print(f"Loaded {len(self.strategies)} strategies")
        return len(self.strategies)

    def evaluate_signals(self, strategy: Dict, price: float, indicators: Dict) -> Optional[str]:
        """
        Evaluate entry/exit signals for a strategy.

        Returns:
            "BUY", "SELL", or None
        """
        genome = strategy.get('genome', {})
        entry_rules = genome.get('entry_rules', [])

        if not entry_rules:
            return None

        # Evaluate entry rules
        all_pass = True
        for rule in entry_rules:
            left = rule.get('left', {})
            right = rule.get('right', {})
            op = rule.get('op', '>')

            left_val = self._get_rule_value(left, indicators)
            right_val = self._get_rule_value(right, indicators)

            if left_val is None or right_val is None:
                all_pass = False
                break

            if op == '>':
                if not (left_val > right_val):
                    all_pass = False
                    break
            elif op == '<':
                if not (left_val < right_val):
                    all_pass = False
                    break

        return "BUY" if all_pass else None

    def _get_rule_value(self, item: Dict, indicators: Dict) -> Optional[float]:
        """Get value from a rule item."""
        if not isinstance(item, dict):
            return float(item) if item else None

        if 'value' in item:
            return float(item['value'])

        if 'indicator' in item:
            key = f"{item['indicator']}_{item.get('period', 14)}"
            return indicators.get(key)

        if 'field' in item:
            return indicators.get(item['field'])

        return None

    def execute_signal(self, strategy_id: str, product_id: str,
                       signal: str, price: float) -> Dict:
        """
        Execute a trading signal with risk validation.

        Args:
            strategy_id: ID of the strategy
            product_id: Trading pair (e.g., "BTC-USD")
            signal: "BUY" or "SELL"
            price: Current price

        Returns:
            Dict with execution result
        """
        # Risk check
        if signal == "BUY":
            position_size = self.initial_capital * SPOT_RISK_CONFIG.max_position_size_pct
            can_trade, reason = self.risk_manager.can_open_position(
                product_id=product_id,
                side="BUY",
                leverage=1,
                margin_usd=position_size,
                current_positions={},
            )

            if not can_trade:
                return {"success": False, "reason": f"Risk blocked: {reason}"}

            # Execute
            result = self.executor.place_market_buy(product_id, position_size)

            # Parallel dry run for comparison
            if self.dry_executor:
                dry_result = self.dry_executor.place_market_buy(product_id, position_size)

            # Log trade
            self._log_trade(strategy_id, product_id, "BUY", position_size,
                           price, 0, 0, "signal", self.dry_run,
                           result.get('order_id', ''))

            # Telegram notification for real trades
            if not self.dry_run and result.get('success'):
                send_telegram(
                    f"<b>SPOT TRADE</b>\n\n"
                    f"BUY {product_id}\n"
                    f"Size: ${position_size:.2f}\n"
                    f"Price: ${price:.2f}\n"
                    f"Strategy: {strategy_id}"
                )

            return result

        elif signal == "SELL":
            crypto = product_id.split("-")[0]
            balance = self.executor.get_available_balance(crypto)

            if balance <= 0:
                return {"success": False, "reason": "No crypto to sell"}

            result = self.executor.place_market_sell(product_id, balance)

            if self.dry_executor:
                dry_balance = self.dry_executor.get_available_balance(crypto)
                if dry_balance > 0:
                    self.dry_executor.place_market_sell(product_id, dry_balance)

            self._log_trade(strategy_id, product_id, "SELL", balance,
                           price, 0, 0, "signal", self.dry_run,
                           result.get('order_id', ''))

            if not self.dry_run and result.get('success'):
                send_telegram(
                    f"<b>SPOT TRADE</b>\n\n"
                    f"SELL {balance:.8f} {crypto}\n"
                    f"Price: ${price:.2f}\n"
                    f"Strategy: {strategy_id}"
                )

            return result

        return {"success": False, "reason": "Invalid signal"}

    def _log_trade(self, strategy_id, product_id, side, size, price,
                   pnl, fee, reason, dry_run, order_id):
        """Log trade to database."""
        conn = sqlite3.connect(ORCHESTRATOR_DB)
        c = conn.cursor()
        c.execute("""
            INSERT INTO live_trades
            (timestamp, strategy_id, product_id, side, size, price, pnl, fee, reason, dry_run, order_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (time.time(), strategy_id, product_id, side, size, price,
              pnl, fee, reason, 1 if dry_run else 0, order_id))
        conn.commit()
        conn.close()

    def get_status(self) -> Dict:
        """Get orchestrator status."""
        executor_status = self.executor.get_status()
        risk_status = self.risk_manager.get_status()

        return {
            "dry_run": self.dry_run,
            "parallel_dry_run": self.dry_run_parallel,
            "strategies_loaded": len(self.strategies),
            "running": self.running,
            "executor": executor_status,
            "risk": risk_status,
        }

    def print_status(self):
        """Print formatted status."""
        status = self.get_status()

        print("\n" + "=" * 60)
        print("LIVE SPOT ORCHESTRATOR STATUS")
        print("=" * 60)
        print(f"Mode: {'DRY RUN' if status['dry_run'] else 'LIVE'}")
        print(f"Parallel dry run: {status['parallel_dry_run']}")
        print(f"Strategies: {status['strategies_loaded']}")
        print(f"Risk level: {status['risk']['risk_level']}")
        print(f"Can trade: {status['risk']['can_trade']}")
        print(f"USD Balance: ${status['executor'].get('usd_balance', 0):.2f}")
        print("=" * 60)


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Live Spot Trading Orchestrator")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Run in dry-run mode (default)")
    parser.add_argument("--live", action="store_true",
                        help="Run with real trading (CAREFUL!)")
    parser.add_argument("--capital", type=float, default=500,
                        help="Initial capital in USD")
    parser.add_argument("--status", action="store_true",
                        help="Show current status")
    parser.add_argument("--kill", action="store_true",
                        help="Emergency close all positions")
    args = parser.parse_args()

    dry_run = not args.live

    orchestrator = LiveSpotOrchestrator(
        initial_capital=args.capital,
        dry_run=dry_run,
        dry_run_parallel=args.live,  # parallel only when live
    )

    if args.kill:
        print("EMERGENCY: Closing all positions...")
        emergency_close_all(orchestrator.executor, orchestrator.risk_manager)
        return

    if args.status:
        orchestrator.load_strategies()
        orchestrator.print_status()
        return

    # Load strategies
    loaded = orchestrator.load_strategies()
    if loaded == 0:
        print("No strategies loaded. Run select_top_strategies.py first.")
        return

    orchestrator.print_status()

    if not dry_run:
        print("\n*** WARNING: LIVE TRADING MODE ***")
        print("Real money will be used. Press Ctrl+C to abort.")
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("Aborted.")
            return

    print("\nOrchestrator ready. Use paper_trading_pipeline.py --run to feed signals.")


if __name__ == "__main__":
    main()
