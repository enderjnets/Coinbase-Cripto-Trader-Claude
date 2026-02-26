#!/usr/bin/env python3
"""
live_paper_trader.py - Paper Trading con datos en tiempo real de Coinbase
=========================================================================

Sistema de paper trading que:
1. Se conecta a Coinbase WebSocket para datos en tiempo real
2. Evalúa señales usando la mejor estrategia encontrada
3. Simula trades con fees, slippage y latencia realistas
4. Registra resultados para análisis

NO ejecuta órdenes reales, solo simula.

Uso:
    from live_paper_trader import LivePaperTrader
    trader = LivePaperTrader(strategy_genome, initial_capital=10000)
    await trader.run("BTC-USD")
"""

import asyncio
import json
import time
import os
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List, Any
import pandas as pd
import numpy as np

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    print("WARNING: websockets not installed. Run: pip install websockets")

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Fees de Coinbase Advanced (maker/taker)
DEFAULT_FEE_RATE = 0.004  # 0.4% (maker fee)
DEFAULT_SLIPPAGE = 0.0005  # 0.05%
DEFAULT_LATENCY_MS = 100  # 100ms latencia simulada

# WebSocket endpoints
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"

# Paper trading state file
PAPER_STATE_FILE = "/tmp/paper_trading_state.json"
PAPER_DB_FILE = "/tmp/paper_trading.db"

# ============================================================================
# INDICATORS FOR REAL-TIME CALCULATION
# ============================================================================

def calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    """Calculate RSI from price array."""
    if len(prices) < period + 1:
        return 50.0  # Neutral

    deltas = np.diff(prices[-(period+1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains) if len(gains) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_sma(prices: np.ndarray, period: int) -> float:
    """Calculate SMA from price array."""
    if len(prices) < period:
        return prices[-1] if len(prices) > 0 else 0
    return float(np.mean(prices[-period:]))


def calculate_ema(prices: np.ndarray, period: int) -> float:
    """Calculate EMA from price array."""
    if len(prices) < period:
        return prices[-1] if len(prices) > 0 else 0

    multiplier = 2.0 / (period + 1)
    ema = float(np.mean(prices[:period]))  # Start with SMA
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def calculate_volume_sma(volumes: np.ndarray, period: int) -> float:
    """Calculate Volume SMA."""
    if len(volumes) < period:
        return float(np.mean(volumes)) if len(volumes) > 0 else 0
    return float(np.mean(volumes[-period:]))

# ============================================================================
# PAPER TRADER CLASS
# ============================================================================

class LivePaperTrader:
    """
    Paper trading con datos en tiempo real de Coinbase.

    NO ejecuta órdenes reales, solo simula con condiciones realistas:
    - Fees de Coinbase (0.4% maker)
    - Slippage (0.05%)
    - Latencia simulada (100ms)
    """

    def __init__(
        self,
        strategy_genome: Dict,
        initial_capital: float = 10000.0,
        fee_rate: float = DEFAULT_FEE_RATE,
        slippage: float = DEFAULT_SLIPPAGE,
        position_size_pct: float = 0.10,  # 10% del capital por trade
        max_position_pct: float = 0.30,   # Max 30% capital en posiciones
    ):
        self.strategy_genome = strategy_genome
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.position_size_pct = position_size_pct
        self.max_position_pct = max_position_pct

        # Position tracking
        self.position: Optional[Dict] = None
        self.trades: List[Dict] = []

        # Price history for indicators
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.max_history = 500  # Keep last 500 candles

        # Running state
        self.running = False
        self.start_time: Optional[float] = None
        self.last_price: float = 0.0

        # Load previous state if exists
        self._load_state()

    def _load_state(self):
        """Load previous state from file."""
        if os.path.exists(PAPER_STATE_FILE):
            try:
                with open(PAPER_STATE_FILE, 'r') as f:
                    state = json.load(f)
                self.capital = state.get('capital', self.initial_capital)
                self.trades = state.get('trades', [])
                self.price_history = state.get('price_history', [])
                self.volume_history = state.get('volume_history', [])
                print(f"[PaperTrader] Loaded state: ${self.capital:.2f}, {len(self.trades)} trades")
            except Exception as e:
                print(f"[PaperTrader] Could not load state: {e}")

    def _save_state(self):
        """Save current state to file."""
        state = {
            'capital': self.capital,
            'trades': self.trades[-100:],  # Keep last 100 trades
            'price_history': self.price_history[-200:],
            'volume_history': self.volume_history[-200:],
            'timestamp': time.time()
        }
        try:
            with open(PAPER_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[PaperTrader] Could not save state: {e}")

    def _get_indicators(self) -> Dict[str, float]:
        """Calculate all indicators from price history."""
        if len(self.price_history) < 10:
            return {}

        prices = np.array(self.price_history)
        volumes = np.array(self.volume_history) if self.volume_history else np.ones(len(prices))

        indicators = {
            'close': prices[-1],
            'high': prices[-1] * 1.001,  # Approximate
            'low': prices[-1] * 0.999,   # Approximate
            'volume': volumes[-1] if len(volumes) > 0 else 0,
        }

        # RSI variants
        for period in [10, 14, 20, 50, 100, 200]:
            if len(prices) >= period + 1:
                indicators[f'RSI_{period}'] = calculate_rsi(prices, period)

        # SMA variants
        for period in [10, 14, 20, 50, 100, 200]:
            if len(prices) >= period:
                indicators[f'SMA_{period}'] = calculate_sma(prices, period)

        # EMA variants
        for period in [10, 14, 20, 50, 100, 200]:
            if len(prices) >= period:
                indicators[f'EMA_{period}'] = calculate_ema(prices, period)

        # Volume SMA
        for period in [10, 14, 20, 50, 100, 200]:
            if len(volumes) >= period:
                indicators[f'VOLSMA_{period}'] = calculate_volume_sma(volumes, period)

        return indicators

    def _evaluate_entry_rules(self, indicators: Dict) -> bool:
        """Evaluate entry rules from strategy genome."""
        entry_rules = self.strategy_genome.get('entry_rules', [])

        if not entry_rules:
            return False

        for rule in entry_rules:
            left = rule.get('left', {})
            right = rule.get('right', {})
            op = rule.get('op', '>')

            # Get left value
            left_val = self._get_rule_value(left, indicators)

            # Get right value
            right_val = self._get_rule_value(right, indicators)

            # Skip if NaN
            if np.isnan(left_val) or np.isnan(right_val):
                return False

            # Evaluate
            if op == '>':
                if not (left_val > right_val):
                    return False
            elif op == '<':
                if not (left_val < right_val):
                    return False
            elif op == 'crosses_above':
                # Need at least 2 data points - simplified
                if not (left_val > right_val):
                    return False

        return True

    def _get_rule_value(self, item: Dict, indicators: Dict) -> float:
        """Get value from rule item (indicator or constant)."""
        if not isinstance(item, dict):
            return float(item) if item else 0.0

        if 'value' in item:
            return float(item['value'])

        if 'indicator' in item:
            name = item['indicator']
            period = item.get('period', 14)
            key = f"{name}_{period}"
            return indicators.get(key, np.nan)

        if 'field' in item:
            field = item['field']
            return indicators.get(field, np.nan)

        return 0.0

    async def _simulate_buy(self, price: float, timestamp: str) -> bool:
        """Simulate buy with realistic costs."""
        # Calculate position size
        size_usd = self.capital * self.position_size_pct

        if size_usd < 10:
            return False  # Skip dust trades

        # Simulate latency
        await asyncio.sleep(DEFAULT_LATENCY_MS / 1000.0)

        # Apply slippage (buy at slightly higher price)
        fill_price = price * (1 + self.slippage)

        # Calculate fee
        fee = size_usd * self.fee_rate

        # Deduct from capital
        cost = size_usd + fee
        if cost > self.capital:
            size_usd = self.capital / (1 + self.fee_rate)
            fee = size_usd * self.fee_rate
            cost = size_usd + fee

        self.capital -= cost

        # Record position
        params = self.strategy_genome.get('params', {})
        sl_pct = params.get('sl_pct', 0.05)
        tp_pct = params.get('tp_pct', 0.10)

        self.position = {
            'entry_price': fill_price,
            'size_usd': size_usd,
            'size_crypto': size_usd / fill_price,
            'fee_paid': fee,
            'entry_time': timestamp,
            'stop_loss': fill_price * (1 - sl_pct),
            'take_profit': fill_price * (1 + tp_pct),
            'trailing_stop': (fill_price - fill_price * (1 - sl_pct)) * 0.8
        }

        print(f"[PAPER BUY] {timestamp}: {fill_price:.2f} | Size: ${size_usd:.2f} | Fee: ${fee:.2f}")
        return True

    async def _simulate_sell(self, price: float, timestamp: str, reason: str = "signal") -> float:
        """Simulate sell with realistic costs."""
        if not self.position:
            return 0.0

        # Simulate latency
        await asyncio.sleep(DEFAULT_LATENCY_MS / 1000.0)

        # Apply slippage (sell at slightly lower price)
        fill_price = price * (1 - self.slippage)

        # Calculate proceeds
        gross_proceeds = self.position['size_crypto'] * fill_price
        fee = gross_proceeds * self.fee_rate
        net_proceeds = gross_proceeds - fee

        # Calculate PnL
        pnl = net_proceeds - self.position['size_usd']
        pnl_pct = (pnl / self.position['size_usd']) * 100 if self.position['size_usd'] > 0 else 0

        # Update capital
        self.capital += net_proceeds

        # Record trade
        trade = {
            'entry_time': self.position['entry_time'],
            'exit_time': timestamp,
            'entry_price': self.position['entry_price'],
            'exit_price': fill_price,
            'size_usd': self.position['size_usd'],
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'exit_reason': reason,
            'fee_total': self.position['fee_paid'] + fee
        }
        self.trades.append(trade)

        # Save state
        self._save_state()

        print(f"[PAPER SELL] {timestamp}: {fill_price:.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%) | {reason}")

        # Clear position
        self.position = None

        return pnl

    async def _process_tick(self, data: Dict):
        """Process incoming tick data."""
        if data.get('type') not in ['ticker', 'match']:
            return

        price = float(data.get('price', 0))
        volume = float(data.get('size', data.get('volume_24h', 1)))
        timestamp = data.get('time', datetime.utcnow().isoformat())

        if price <= 0:
            return

        self.last_price = price

        # Update history
        self.price_history.append(price)
        if volume > 0:
            self.volume_history.append(volume)

        # Trim history
        if len(self.price_history) > self.max_history:
            self.price_history = self.price_history[-self.max_history:]
        if len(self.volume_history) > self.max_history:
            self.volume_history = self.volume_history[-self.max_history:]

        # Check exit conditions if in position
        if self.position:
            # Update trailing stop
            new_sl = price - self.position['trailing_stop']
            if new_sl > self.position['stop_loss']:
                self.position['stop_loss'] = new_sl

            # Check stop loss
            if price <= self.position['stop_loss']:
                await self._simulate_sell(price, timestamp, "stop_loss")
                return

            # Check take profit
            if price >= self.position['take_profit']:
                await self._simulate_sell(price, timestamp, "take_profit")
                return

        # Check entry conditions if not in position
        else:
            indicators = self._get_indicators()
            if indicators and self._evaluate_entry_rules(indicators):
                await self._simulate_buy(price, timestamp)

    async def run(self, product_id: str = "BTC-USD"):
        """
        Main loop: connect to Coinbase WebSocket and run paper trading.

        Args:
            product_id: Trading pair (e.g., "BTC-USD", "ETH-USD")
        """
        if not HAS_WEBSOCKETS:
            print("ERROR: websockets library not installed")
            return

        self.running = True
        self.start_time = time.time()

        print(f"\n{'='*60}")
        print(f"PAPER TRADING STARTED")
        print(f"{'='*60}")
        print(f"Product: {product_id}")
        print(f"Initial Capital: ${self.initial_capital:.2f}")
        print(f"Position Size: {self.position_size_pct*100:.1f}%")
        print(f"Fee Rate: {self.fee_rate*100:.2f}%")
        print(f"Slippage: {self.slippage*100:.3f}%")
        print(f"Strategy: {len(self.strategy_genome.get('entry_rules', []))} entry rules")
        print(f"{'='*60}\n")

        ws_url = COINBASE_WS_URL

        try:
            async with websockets.connect(ws_url) as ws:
                # Subscribe to ticker channel
                subscribe = {
                    "type": "subscribe",
                    "product_ids": [product_id],
                    "channels": ["ticker", "matches"]
                }
                await ws.send(json.dumps(subscribe))

                print(f"[PaperTrader] Connected to {ws_url}")
                print(f"[PaperTrader] Subscribed to {product_id}")

                # Process messages
                async for message in ws:
                    if not self.running:
                        break

                    try:
                        data = json.loads(message)
                        await self._process_tick(data)
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"[PaperTrader] Error processing tick: {e}")

        except Exception as e:
            print(f"[PaperTrader] Connection error: {e}")
        finally:
            self.running = False
            self._save_state()
            self._print_summary()

    def stop(self):
        """Stop the paper trader."""
        self.running = False

    def _print_summary(self):
        """Print trading summary."""
        duration = time.time() - self.start_time if self.start_time else 0
        hours = duration / 3600

        total_pnl = sum(t['pnl'] for t in self.trades)
        wins = sum(1 for t in self.trades if t['pnl'] > 0)
        losses = len(self.trades) - wins
        win_rate = (wins / len(self.trades) * 100) if self.trades else 0

        print(f"\n{'='*60}")
        print(f"PAPER TRADING SUMMARY")
        print(f"{'='*60}")
        print(f"Duration: {hours:.2f} hours")
        print(f"Total Trades: {len(self.trades)}")
        print(f"Win/Loss: {wins}/{losses}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Total PnL: ${total_pnl:+.2f}")
        print(f"Final Capital: ${self.capital:.2f}")
        print(f"Return: {((self.capital / self.initial_capital) - 1) * 100:+.2f}%")
        print(f"{'='*60}\n")

    def get_status(self) -> Dict:
        """Get current status for dashboard."""
        total_pnl = sum(t['pnl'] for t in self.trades)
        wins = sum(1 for t in self.trades if t['pnl'] > 0)
        win_rate = (wins / len(self.trades) * 100) if self.trades else 0

        return {
            'running': self.running,
            'capital': self.capital,
            'initial_capital': self.initial_capital,
            'position': self.position,
            'last_price': self.last_price,
            'total_trades': len(self.trades),
            'wins': wins,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'return_pct': ((self.capital / self.initial_capital) - 1) * 100,
            'trades': self.trades[-20:],  # Last 20 trades
            'start_time': self.start_time
        }

    def get_equity_curve(self) -> List[Dict]:
        """Calculate equity curve from trades."""
        if not self.trades:
            return []

        equity = self.initial_capital
        curve = [{'trade': 0, 'equity': equity, 'pnl': 0}]

        for i, trade in enumerate(self.trades):
            equity += trade['pnl']
            curve.append({
                'trade': i + 1,
                'equity': equity,
                'pnl': trade['pnl']
            })

        return curve


# ============================================================================
# HELPER: Get best strategy from database
# ============================================================================

def get_best_strategy_from_db(db_path: str = "coordinator.db") -> Optional[Dict]:
    """
    Get the best strategy from the results database.

    Returns strategy genome that passed all validation criteria.
    """
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return None

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Try to get canonical result first
        c.execute("""
            SELECT r.strategy_genome, r.pnl, r.trades, r.win_rate, r.sharpe_ratio
            FROM results r
            WHERE r.is_canonical = 1
            ORDER BY r.pnl DESC
            LIMIT 1
        """)
        row = c.fetchone()

        # Fallback to best overall
        if not row:
            c.execute("""
                SELECT r.strategy_genome, r.pnl, r.trades, r.win_rate, r.sharpe_ratio
                FROM results r
                WHERE r.pnl > 0 AND r.trades >= 10
                ORDER BY r.sharpe_ratio DESC
                LIMIT 1
            """)
            row = c.fetchone()

        conn.close()

        if row:
            genome = json.loads(row[0]) if row[0] else None
            print(f"Loaded strategy: PnL=${row[1]:.2f}, Trades={row[2]}, WinRate={row[3]:.1f}%, Sharpe={row[4]:.2f}")
            return genome

        return None

    except Exception as e:
        print(f"Error loading strategy: {e}")
        return None


# ============================================================================
# STANDALONE RUNNER
# ============================================================================

async def main():
    """Run paper trading standalone."""
    import argparse

    parser = argparse.ArgumentParser(description="Paper Trading with Coinbase WebSocket")
    parser.add_argument("--product", default="BTC-USD", help="Trading pair")
    parser.add_argument("--capital", type=float, default=10000, help="Initial capital")
    parser.add_argument("--size", type=float, default=0.10, help="Position size %%")
    args = parser.parse_args()

    # Get best strategy
    genome = get_best_strategy_from_db()

    if not genome:
        print("No strategy found. Using default RSI strategy.")
        genome = {
            "entry_rules": [
                {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30}}
            ],
            "params": {"sl_pct": 0.03, "tp_pct": 0.06}
        }

    # Create and run trader
    trader = LivePaperTrader(
        strategy_genome=genome,
        initial_capital=args.capital,
        position_size_pct=args.size
    )

    try:
        await trader.run(args.product)
    except KeyboardInterrupt:
        print("\nStopping paper trader...")
        trader.stop()


if __name__ == "__main__":
    asyncio.run(main())
