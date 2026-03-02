#!/usr/bin/env python3
"""
paper_trading_monitor.py - OOS Pipeline Auto-Launcher Daemon
=============================================================

Daemon que monitorea coordinator.db para estrategias OOS-validadas y
auto-lanza paper trading con datos reales de Coinbase WebSocket.

Pipeline: OOS Validation → Auto-detect → Paper Trading → Monitoring

Funcionalidad:
- Monitorea DB cada 5 min buscando estrategias OOS-validadas
- Auto-lanza LivePaperTrader cuando encuentra una estrategia robusta
- Swap automático si aparece mejor estrategia (mayor robustness_score)
- Health check del WebSocket y auto-restart si muere
- Criterios de parada: PnL < -5% o 0 trades en 24h

Uso:
    python paper_trading_monitor.py                    # Run daemon
    python paper_trading_monitor.py --check-interval 60  # Check every 60s
    python paper_trading_monitor.py --capital 500      # Custom capital
    python paper_trading_monitor.py --dry-run          # Check DB but don't launch
"""

import asyncio
import json
import os
import signal
import sqlite3
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict

# Add project dir to path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from live_paper_trader import LivePaperTrader, get_best_oos_strategy

# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_DB = os.path.join(PROJECT_DIR, "coordinator.db")
MONITOR_STATE_FILE = "/tmp/paper_trading_monitor.json"
DEFAULT_CHECK_INTERVAL = 300  # 5 minutes
DEFAULT_CAPITAL = 500.0

# Stop criteria
MAX_LOSS_PCT = 0.05         # -5% of capital → pause
NO_TRADE_TIMEOUT_H = 24     # 24h without trades → check WebSocket
HEALTH_CHECK_INTERVAL = 3600  # 1 hour


# ============================================================================
# PAPER TRADING MONITOR
# ============================================================================

class PaperTradingMonitor:
    """
    Daemon that monitors DB for OOS-validated strategies and auto-launches
    paper trading with Coinbase WebSocket data.
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB,
        check_interval: int = DEFAULT_CHECK_INTERVAL,
        initial_capital: float = DEFAULT_CAPITAL,
        dry_run: bool = False,
    ):
        self.db_path = db_path
        self.check_interval = check_interval
        self.initial_capital = initial_capital
        self.dry_run = dry_run

        # Current trader state
        self.current_trader: Optional[LivePaperTrader] = None
        self.current_strategy_id: Optional[int] = None
        self.current_product: Optional[str] = None
        self.trader_thread: Optional[threading.Thread] = None
        self.trader_loop: Optional[asyncio.AbstractEventLoop] = None

        # Monitoring state
        self.running = False
        self.start_time: Optional[float] = None
        self.last_trade_time: Optional[float] = None
        self.last_health_check: float = 0
        self.swap_count: int = 0
        self.restarts: int = 0

    def find_best_oos_strategy(self) -> Optional[Dict]:
        """Query DB for best OOS-validated strategy."""
        return get_best_oos_strategy(self.db_path)

    def should_swap_strategy(self, new_strategy: Dict) -> bool:
        """Determine if we should swap to a new strategy."""
        if self.current_strategy_id is None:
            return True  # No current strategy, always accept

        new_id = new_strategy['result_id']
        if new_id == self.current_strategy_id:
            return False  # Same strategy

        # Swap if new strategy has significantly better robustness
        new_robustness = new_strategy['oos_metrics']['robustness_score']
        current_robustness = self._get_current_robustness()

        if new_robustness > current_robustness + 5:  # At least 5 points better
            print(f"[Monitor] Better strategy found: #{new_id} "
                  f"(robustness {new_robustness:.0f} vs current {current_robustness:.0f})")
            return True

        return False

    def _get_current_robustness(self) -> float:
        """Get robustness score of current strategy from DB."""
        if self.current_strategy_id is None:
            return 0.0

        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT robustness_score FROM results WHERE id = ?",
                      (self.current_strategy_id,))
            row = c.fetchone()
            conn.close()
            return float(row[0]) if row and row[0] else 0.0
        except Exception:
            return 0.0

    def launch_paper_trader(self, strategy_data: Dict):
        """Start paper trader in a background thread."""
        genome = strategy_data['genome']
        product_id = strategy_data['product_id']
        result_id = strategy_data['result_id']
        oos = strategy_data['oos_metrics']

        print(f"\n{'='*60}")
        print(f"[Monitor] Launching paper trading for {product_id}")
        print(f"[Monitor] Strategy #{result_id} (robustness: {oos['robustness_score']:.0f}/100)")
        print(f"[Monitor] OOS PnL: ${oos['oos_pnl']:.2f}, Trades: {oos['oos_trades']}, "
              f"Degradation: {oos['oos_degradation']:.2f}")
        print(f"{'='*60}\n")

        if self.dry_run:
            print("[Monitor] DRY RUN - not launching trader")
            return

        # Stop current trader if running
        self._stop_current_trader()

        # Create new trader
        self.current_trader = LivePaperTrader(
            strategy_genome=genome,
            initial_capital=self.initial_capital,
        )
        self.current_strategy_id = result_id
        self.current_product = product_id
        self.last_trade_time = time.time()

        # Run in background thread with its own event loop
        def _run_trader():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.trader_loop = loop
            try:
                loop.run_until_complete(self.current_trader.run(product_id))
            except Exception as e:
                print(f"[Monitor] Trader error: {e}")
            finally:
                loop.close()
                self.trader_loop = None

        self.trader_thread = threading.Thread(target=_run_trader, daemon=True)
        self.trader_thread.start()

        self._save_state()

    def _stop_current_trader(self):
        """Gracefully stop the current paper trader."""
        if self.current_trader and self.current_trader.running:
            print("[Monitor] Stopping current trader...")
            self.current_trader.stop()

            # Wait for thread to finish
            if self.trader_thread and self.trader_thread.is_alive():
                self.trader_thread.join(timeout=10)

        self.current_trader = None
        self.trader_thread = None
        self.trader_loop = None

    def _check_health(self):
        """Check trader health: WebSocket alive, trades happening, PnL within limits."""
        if not self.current_trader:
            return

        now = time.time()
        if now - self.last_health_check < HEALTH_CHECK_INTERVAL:
            return

        self.last_health_check = now
        status = self.current_trader.get_status()

        # Log hourly status
        print(f"[Monitor Health] Capital: ${status['capital']:.2f} | "
              f"Trades: {status['total_trades']} | "
              f"PnL: ${status['total_pnl']:+.2f} | "
              f"Return: {status['return_pct']:+.2f}%")

        # Check PnL limit
        if status['return_pct'] < -(MAX_LOSS_PCT * 100):
            print(f"[Monitor] STOP: PnL below -{MAX_LOSS_PCT*100}% "
                  f"({status['return_pct']:.2f}%). Pausing trader.")
            self._stop_current_trader()
            self.current_strategy_id = None
            self._save_state()
            return

        # Check if trader thread died
        if self.trader_thread and not self.trader_thread.is_alive():
            print("[Monitor] Trader thread died. Restarting...")
            self.restarts += 1
            strategy_data = self.find_best_oos_strategy()
            if strategy_data and strategy_data['result_id'] == self.current_strategy_id:
                self.current_strategy_id = None  # Force re-launch
                self.launch_paper_trader(strategy_data)

        # Check no-trade timeout
        if status['total_trades'] > 0:
            last_trade = status['trades'][-1] if status['trades'] else None
            if last_trade and 'exit_time' in last_trade:
                self.last_trade_time = time.time()

        if self.last_trade_time:
            hours_since_trade = (now - self.last_trade_time) / 3600
            if hours_since_trade > NO_TRADE_TIMEOUT_H:
                print(f"[Monitor] WARNING: No trades in {hours_since_trade:.1f}h. "
                      f"Checking WebSocket health...")
                if not self.current_trader.running:
                    print("[Monitor] WebSocket disconnected. Restarting trader...")
                    self.restarts += 1
                    strategy_data = self.find_best_oos_strategy()
                    if strategy_data:
                        self.current_strategy_id = None
                        self.launch_paper_trader(strategy_data)

        self._save_state()

    def _save_state(self):
        """Save monitor state to JSON for dashboard consumption."""
        state = {
            'running': self.running,
            'start_time': self.start_time,
            'current_strategy_id': self.current_strategy_id,
            'current_product': self.current_product,
            'dry_run': self.dry_run,
            'swap_count': self.swap_count,
            'restarts': self.restarts,
            'check_interval': self.check_interval,
            'initial_capital': self.initial_capital,
            'timestamp': time.time(),
        }

        # Add trader status if available
        if self.current_trader:
            try:
                trader_status = self.current_trader.get_status()
                state['trader'] = {
                    'capital': trader_status['capital'],
                    'total_trades': trader_status['total_trades'],
                    'total_pnl': trader_status['total_pnl'],
                    'return_pct': trader_status['return_pct'],
                    'win_rate': trader_status['win_rate'],
                    'last_price': trader_status['last_price'],
                    'position': trader_status['position'] is not None,
                }
            except Exception:
                pass

        try:
            with open(MONITOR_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[Monitor] Could not save state: {e}")

    def run(self):
        """Main monitoring loop."""
        self.running = True
        self.start_time = time.time()

        print(f"\n{'='*60}")
        print(f"PAPER TRADING MONITOR STARTED")
        print(f"{'='*60}")
        print(f"Database: {self.db_path}")
        print(f"Check Interval: {self.check_interval}s")
        print(f"Initial Capital: ${self.initial_capital:.2f}")
        print(f"Max Loss: -{MAX_LOSS_PCT*100}%")
        print(f"Dry Run: {self.dry_run}")
        print(f"{'='*60}\n")

        # Handle graceful shutdown
        def _signal_handler(sig, frame):
            print("\n[Monitor] Shutting down...")
            self.running = False
            self._stop_current_trader()
            self._save_state()
            sys.exit(0)

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        while self.running:
            try:
                # Check for OOS-validated strategy
                strategy_data = self.find_best_oos_strategy()

                if strategy_data:
                    if self.should_swap_strategy(strategy_data):
                        if self.current_strategy_id is not None:
                            self.swap_count += 1
                            print(f"[Monitor] Swapping to better strategy "
                                  f"(swap #{self.swap_count})")
                        self.launch_paper_trader(strategy_data)
                else:
                    if self.current_strategy_id is None:
                        print(f"[Monitor] No OOS-validated strategy found. Waiting...")

                # Health check
                self._check_health()

            except Exception as e:
                print(f"[Monitor] Error in main loop: {e}")

            # Wait for next check
            time.sleep(self.check_interval)

        # Cleanup
        self._stop_current_trader()
        self._save_state()
        print("[Monitor] Stopped.")


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Paper Trading Monitor - OOS Pipeline Auto-Launcher")
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to coordinator.db")
    parser.add_argument("--check-interval", type=int, default=DEFAULT_CHECK_INTERVAL,
                        help="Check interval in seconds (default: 300)")
    parser.add_argument("--capital", type=float, default=DEFAULT_CAPITAL,
                        help="Initial paper trading capital (default: 500)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Check DB but don't launch trader")
    parser.add_argument("--status", action="store_true",
                        help="Show current monitor status and exit")
    args = parser.parse_args()

    if args.status:
        if os.path.exists(MONITOR_STATE_FILE):
            with open(MONITOR_STATE_FILE, 'r') as f:
                state = json.load(f)
            print(json.dumps(state, indent=2))
        else:
            print("No monitor state found. Monitor not running.")
        return

    monitor = PaperTradingMonitor(
        db_path=args.db,
        check_interval=args.check_interval,
        initial_capital=args.capital,
        dry_run=args.dry_run,
    )
    monitor.run()


if __name__ == "__main__":
    main()
