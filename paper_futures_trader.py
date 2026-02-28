#!/usr/bin/env python3
"""
paper_futures_trader.py - Paper Trading para Futuros con Coinbase
================================================================

Sistema de paper trading para futuros que:
1. Se conecta a Coinbase WebSocket para datos en tiempo real
2. Evalúa señales usando la mejor estrategia encontrada
3. Simula trades con:
   - Posiciones Long y Short
   - Apalancamiento 1x-10x
   - Funding rates (cada hora para perpetuos)
   - Margin management
   - Liquidaciones automáticas
4. Registra resultados para análisis

NO ejecuta órdenes reales, solo simula.

Uso:
    from paper_futures_trader import PaperFuturesTrader
    trader = PaperFuturesTrader(strategy_genome, initial_capital=10000, leverage=5)
    await trader.run("BIT-27FEB26-CDE")
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
# CONFIGURACIÓN DE FUTUROS
# ============================================================================

# Fees de Coinbase Futures (maker/taker)
DEFAULT_FEE_MAKER = 0.0002  # 0.02%
DEFAULT_FEE_TAKER = 0.0005  # 0.05%
DEFAULT_SLIPPAGE = 0.002    # 0.2% (realistic for crypto)

# Margin requirements
INTRADAY_MARGIN = 0.10     # 10%
OVERNIGHT_MARGIN = 0.25    # 25%
MAINTENANCE_MARGIN = 0.05  # 5%

# Funding rate (promedio para perpetuos)
DEFAULT_FUNDING_RATE = 0.0001  # 0.01% per 8 hours
FUNDING_INTERVAL_SECONDS = 3600  # 1 hora

# WebSocket endpoints
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"

# Paper trading state files
PAPER_FUTURES_STATE_FILE = "/tmp/paper_futures_state.json"
PAPER_FUTURES_DB_FILE = "/tmp/paper_futures_trading.db"

# ============================================================================
# INDICATORS FOR REAL-TIME CALCULATION (same as spot)
# ============================================================================

def calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    """Calculate RSI from price array."""
    if len(prices) < period + 1:
        return 50.0

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
    ema = float(np.mean(prices[:period]))
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


# ============================================================================
# PAPER FUTURES TRADER CLASS
# ============================================================================

class PaperFuturesTrader:
    """
    Paper trading para futuros con datos en tiempo real de Coinbase.

    Features:
    - Long y Short positions
    - Apalancamiento 1x-10x
    - Funding rates (cada hora para perpetuos)
    - Margin management
    - Liquidación automática
    """

    def __init__(
        self,
        strategy_genome: Dict,
        initial_capital: float = 10000.0,
        leverage: int = 3,
        direction: str = "BOTH",  # LONG, SHORT, BOTH
        fee_rate: float = DEFAULT_FEE_MAKER,
        slippage: float = DEFAULT_SLIPPAGE,
        position_size_pct: float = 0.10,
        is_perpetual: bool = True,
    ):
        self.strategy_genome = strategy_genome
        self.initial_capital = initial_capital
        self.balance = initial_capital
        self.leverage = min(leverage, 10)  # Max 10x
        self.direction = direction.upper()
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.position_size_pct = position_size_pct
        self.is_perpetual = is_perpetual

        # Margin tracking
        self.available_margin = initial_capital
        self.used_margin = 0.0

        # Position tracking
        self.position: Optional[Dict] = None
        self.trades: List[Dict] = []
        self.liquidations = 0

        # Funding tracking
        self.last_funding_time = time.time()
        self.funding_paid = 0.0
        self.funding_received = 0.0

        # Price history for indicators
        self.price_history: List[float] = []
        self.max_history = 500

        # Running state
        self.running = False
        self.start_time: Optional[float] = None
        self.last_price: float = 0.0
        self.contract_id: str = ""

        # Load previous state
        self._load_state()

    def _load_state(self):
        """Load previous state from file."""
        if os.path.exists(PAPER_FUTURES_STATE_FILE):
            try:
                with open(PAPER_FUTURES_STATE_FILE, 'r') as f:
                    state = json.load(f)
                self.balance = state.get('balance', self.initial_capital)
                self.trades = state.get('trades', [])
                self.price_history = state.get('price_history', [])
                self.liquidations = state.get('liquidations', 0)
                self.funding_paid = state.get('funding_paid', 0)
                self.funding_received = state.get('funding_received', 0)
                print(f"[PaperFutures] Loaded state: ${self.balance:.2f}, {len(self.trades)} trades, {self.liquidations} liqs")
            except Exception as e:
                print(f"[PaperFutures] Could not load state: {e}")

    def _save_state(self):
        """Save current state to file."""
        state = {
            'balance': self.balance,
            'trades': self.trades[-100:],
            'price_history': self.price_history[-200:],
            'liquidations': self.liquidations,
            'funding_paid': self.funding_paid,
            'funding_received': self.funding_received,
            'timestamp': time.time()
        }
        try:
            with open(PAPER_FUTURES_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[PaperFutures] Could not save state: {e}")

    def calculate_liquidation_price(self, entry_price: float, side: str, leverage: int) -> float:
        """
        Calculate liquidation price.

        For LONG: liquidates when price drops below (entry * (1 - 1/leverage + maintenance_margin))
        For SHORT: liquidates when price rises above (entry * (1 + 1/leverage - maintenance_margin))
        """
        if side == "LONG":
            return entry_price * (1 - (1/leverage) + MAINTENANCE_MARGIN)
        else:
            return entry_price * (1 + (1/leverage) - MAINTENANCE_MARGIN)

    def _get_indicators(self) -> Dict[str, float]:
        """Calculate all indicators from price history."""
        if len(self.price_history) < 10:
            return {}

        prices = np.array(self.price_history)

        indicators = {
            'close': prices[-1],
            'high': prices[-1] * 1.001,
            'low': prices[-1] * 0.999,
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

        return indicators

    def _evaluate_entry_rules(self, indicators: Dict, side: str) -> bool:
        """Evaluate entry rules from strategy genome for given side."""
        entry_rules = self.strategy_genome.get('entry_rules', [])

        if not entry_rules:
            return False

        for rule in entry_rules:
            left = rule.get('left', {})
            right = rule.get('right', {})
            op = rule.get('op', '>')

            left_val = self._get_rule_value(left, indicators)
            right_val = self._get_rule_value(right, indicators)

            if np.isnan(left_val) or np.isnan(right_val):
                return False

            # For SHORT, invert the comparison
            if side == "SHORT":
                if op == '>':
                    op = '<'
                elif op == '<':
                    op = '>'

            if op == '>':
                if not (left_val > right_val):
                    return False
            elif op == '<':
                if not (left_val < right_val):
                    return False

        return True

    def _get_rule_value(self, item: Dict, indicators: Dict) -> float:
        """Get value from rule item."""
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

    async def _apply_funding(self, price: float):
        """Apply funding rate payment/receipt."""
        current_time = time.time()
        time_since_funding = current_time - self.last_funding_time

        if time_since_funding >= FUNDING_INTERVAL_SECONDS and self.position:
            # Calculate funding (simplified - use average rate)
            funding_rate = DEFAULT_FUNDING_RATE * (time_since_funding / (8 * 3600))  # Pro-rated

            position_value = self.position['size_contracts'] * price
            funding_amount = position_value * funding_rate

            if self.position['side'] == 'LONG':
                # Longs pay when funding > 0
                self.balance -= funding_amount
                self.funding_paid += funding_amount
                print(f"[FUNDING] LONG paid ${funding_amount:.4f}")
            else:
                # Shorts receive when funding > 0
                self.balance += funding_amount
                self.funding_received += funding_amount
                print(f"[FUNDING] SHORT received ${funding_amount:.4f}")

            self.last_funding_time = current_time
            self._save_state()

    async def _check_liquidation(self, price: float, timestamp: str) -> bool:
        """Check if position should be liquidated."""
        if not self.position:
            return False

        liq_price = self.position['liquidation_price']
        side = self.position['side']

        should_liq = False
        if side == 'LONG' and price <= liq_price:
            should_liq = True
        elif side == 'SHORT' and price >= liq_price:
            should_liq = True

        if should_liq:
            # Liquidation - lose all margin
            margin_lost = self.position['margin']
            self.used_margin -= margin_lost
            self.available_margin += 0  # Margin is lost
            self.liquidations += 1

            trade = {
                'entry_time': self.position['entry_time'],
                'exit_time': timestamp,
                'entry_price': self.position['entry_price'],
                'exit_price': price,
                'side': self.position['side'],
                'size_usd': self.position['size_usd'],
                'pnl': -margin_lost,
                'pnl_pct': -100.0,
                'exit_reason': 'LIQUIDATION',
                'leverage': self.position['leverage']
            }
            self.trades.append(trade)

            print(f"[LIQUIDATION] {self.position['side']} at ${price:.2f} | Lost ${margin_lost:.2f}")

            self.position = None
            self._save_state()
            return True

        return False

    async def _open_position(self, price: float, side: str, timestamp: str) -> bool:
        """Open a futures position."""
        # Calculate position size
        position_value = self.balance * self.position_size_pct
        margin_required = position_value / self.leverage

        if margin_required > self.available_margin:
            return False

        if margin_required < 10:
            return False  # Skip dust trades

        # Apply slippage
        if side == 'LONG':
            fill_price = price * (1 + self.slippage)
        else:
            fill_price = price * (1 - self.slippage)

        # Calculate fee
        fee = position_value * self.fee_rate

        # Deduct margin and fee
        self.available_margin -= margin_required
        self.used_margin += margin_required
        self.balance -= fee

        # Calculate liquidation price
        liq_price = self.calculate_liquidation_price(fill_price, side, self.leverage)

        # Get strategy params
        params = self.strategy_genome.get('params', {})
        sl_pct = params.get('sl_pct', 0.05)
        tp_pct = params.get('tp_pct', 0.10)

        self.position = {
            'side': side,
            'entry_price': fill_price,
            'size_usd': position_value,
            'size_contracts': position_value / fill_price,
            'margin': margin_required,
            'leverage': self.leverage,
            'entry_time': timestamp,
            'liquidation_price': liq_price,
            'stop_loss': fill_price * (1 - sl_pct) if side == 'LONG' else fill_price * (1 + sl_pct),
            'take_profit': fill_price * (1 + tp_pct) if side == 'LONG' else fill_price * (1 - tp_pct),
            'fee_paid': fee
        }

        print(f"[FUTURES {side}] {timestamp}: ${fill_price:.2f} | Size: ${position_value:.2f} | "
              f"Margin: ${margin_required:.2f} | Leverage: {self.leverage}x | Liq: ${liq_price:.2f}")

        return True

    async def _close_position(self, price: float, timestamp: str, reason: str = "signal") -> float:
        """Close the futures position."""
        if not self.position:
            return 0.0

        # Apply slippage
        if self.position['side'] == 'LONG':
            fill_price = price * (1 - self.slippage)
        else:
            fill_price = price * (1 + self.slippage)

        # Calculate PnL
        entry_price = self.position['entry_price']
        size = self.position['size_contracts']
        leverage = self.position['leverage']

        if self.position['side'] == 'LONG':
            pnl_pct = (fill_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - fill_price) / entry_price

        # PnL = position_value * pnl_pct * leverage
        exit_value = size * fill_price
        fee = exit_value * self.fee_rate
        pnl = (self.position['size_usd'] * pnl_pct * leverage) - self.position['fee_paid'] - fee

        # Return margin + PnL
        margin_return = self.position['margin'] + pnl
        self.balance += margin_return
        self.used_margin -= self.position['margin']
        self.available_margin += self.position['margin']

        # Record trade
        trade = {
            'entry_time': self.position['entry_time'],
            'exit_time': timestamp,
            'entry_price': entry_price,
            'exit_price': fill_price,
            'side': self.position['side'],
            'size_usd': self.position['size_usd'],
            'pnl': pnl,
            'pnl_pct': pnl_pct * leverage * 100,
            'exit_reason': reason,
            'leverage': leverage
        }
        self.trades.append(trade)

        self._save_state()

        print(f"[FUTURES CLOSE {self.position['side']}] {timestamp}: ${fill_price:.2f} | "
              f"PnL: ${pnl:+.2f} ({pnl_pct*leverage*100:+.2f}%) | {reason}")

        self.position = None
        return pnl

    async def _process_tick(self, data: Dict):
        """Process incoming tick data."""
        if data.get('type') not in ['ticker', 'match']:
            return

        price = float(data.get('price', 0))
        timestamp = data.get('time', datetime.utcnow().isoformat())

        if price <= 0:
            return

        self.last_price = price
        self.price_history.append(price)

        if len(self.price_history) > self.max_history:
            self.price_history = self.price_history[-self.max_history:]

        # Apply funding for perpetuals
        if self.is_perpetual and self.position:
            await self._apply_funding(price)

        # Check liquidation
        if await self._check_liquidation(price, timestamp):
            return

        # Check exit conditions if in position
        if self.position:
            # Update trailing stop
            if self.position['side'] == 'LONG':
                new_sl = price - (self.position['entry_price'] * 0.03)
                if new_sl > self.position['stop_loss']:
                    self.position['stop_loss'] = new_sl

                # Check stop loss
                if price <= self.position['stop_loss']:
                    await self._close_position(price, timestamp, "stop_loss")
                    return
                # Check take profit
                if price >= self.position['take_profit']:
                    await self._close_position(price, timestamp, "take_profit")
                    return
            else:
                new_sl = price + (self.position['entry_price'] * 0.03)
                if new_sl < self.position['stop_loss']:
                    self.position['stop_loss'] = new_sl

                # Check stop loss
                if price >= self.position['stop_loss']:
                    await self._close_position(price, timestamp, "stop_loss")
                    return
                # Check take profit
                if price <= self.position['take_profit']:
                    await self._close_position(price, timestamp, "take_profit")
                    return

        # Check entry conditions if not in position
        else:
            indicators = self._get_indicators()
            if not indicators:
                return

            # Check based on allowed direction
            if self.direction in ['LONG', 'BOTH']:
                if self._evaluate_entry_rules(indicators, 'LONG'):
                    await self._open_position(price, 'LONG', timestamp)
                    return

            if self.direction in ['SHORT', 'BOTH']:
                if self._evaluate_entry_rules(indicators, 'SHORT'):
                    await self._open_position(price, 'SHORT', timestamp)
                    return

    async def run(self, contract_id: str = "BIT-27FEB26-CDE"):
        """
        Main loop: connect to Coinbase WebSocket and run futures paper trading.

        Args:
            contract_id: Futures contract ID (e.g., "BIT-27FEB26-CDE", "BIP-20DEC30-CDE")
        """
        if not HAS_WEBSOCKETS:
            print("ERROR: websockets library not installed")
            return

        self.running = True
        self.start_time = time.time()
        self.contract_id = contract_id

        # Determine product ID for WebSocket (use underlying for price feed)
        # For futures, we need to subscribe to the underlying spot price for indicators
        underlying = contract_id.split("-")[0]
        if underlying in ["BIT", "BIP"]:
            product_id = "BTC-USD"
        elif underlying in ["ET", "ETP"]:
            product_id = "ETH-USD"
        elif underlying in ["SOL", "SLP", "SLR"]:
            product_id = "SOL-USD"
        elif underlying in ["XRP", "XPP"]:
            product_id = "XRP-USD"
        else:
            product_id = f"{underlying}-USD"

        print(f"\n{'='*60}")
        print(f"FUTURES PAPER TRADING STARTED")
        print(f"{'='*60}")
        print(f"Contract: {contract_id}")
        print(f"Price Feed: {product_id}")
        print(f"Initial Capital: ${self.initial_capital:.2f}")
        print(f"Leverage: {self.leverage}x")
        print(f"Direction: {self.direction}")
        print(f"Perpetual: {self.is_perpetual}")
        print(f"Fee Rate: {self.fee_rate*100:.3f}%")
        print(f"Position Size: {self.position_size_pct*100:.1f}%")
        print(f"{'='*60}\n")

        try:
            async with websockets.connect(COINBASE_WS_URL) as ws:
                subscribe = {
                    "type": "subscribe",
                    "product_ids": [product_id],
                    "channels": ["ticker", "matches"]
                }
                await ws.send(json.dumps(subscribe))

                print(f"[PaperFutures] Connected to {COINBASE_WS_URL}")
                print(f"[PaperFutures] Subscribed to {product_id}")

                async for message in ws:
                    if not self.running:
                        break

                    try:
                        data = json.loads(message)
                        await self._process_tick(data)
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"[PaperFutures] Error processing tick: {e}")

        except Exception as e:
            print(f"[PaperFutures] Connection error: {e}")
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
        print(f"FUTURES PAPER TRADING SUMMARY")
        print(f"{'='*60}")
        print(f"Contract: {self.contract_id}")
        print(f"Duration: {hours:.2f} hours")
        print(f"Leverage: {self.leverage}x")
        print(f"")
        print(f"Total Trades: {len(self.trades)}")
        print(f"Win/Loss: {wins}/{losses}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Liquidations: {self.liquidations}")
        print(f"")
        print(f"Trading PnL: ${total_pnl:+.2f}")
        print(f"Funding Paid: ${self.funding_paid:.4f}")
        print(f"Funding Received: ${self.funding_received:.4f}")
        print(f"Net Funding: ${self.funding_received - self.funding_paid:+.4f}")
        print(f"")
        print(f"Final Balance: ${self.balance:.2f}")
        print(f"Return: {((self.balance / self.initial_capital) - 1) * 100:+.2f}%")
        print(f"{'='*60}\n")

    def get_status(self) -> Dict:
        """Get current status for dashboard."""
        total_pnl = sum(t['pnl'] for t in self.trades)
        wins = sum(1 for t in self.trades if t['pnl'] > 0)
        win_rate = (wins / len(self.trades) * 100) if self.trades else 0

        return {
            'running': self.running,
            'contract': self.contract_id,
            'balance': self.balance,
            'initial_capital': self.initial_capital,
            'available_margin': self.available_margin,
            'used_margin': self.used_margin,
            'position': self.position,
            'last_price': self.last_price,
            'leverage': self.leverage,
            'direction': self.direction,
            'total_trades': len(self.trades),
            'wins': wins,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'liquidations': self.liquidations,
            'funding_net': self.funding_received - self.funding_paid,
            'return_pct': ((self.balance / self.initial_capital) - 1) * 100,
            'trades': self.trades[-20:],
            'start_time': self.start_time
        }


# ============================================================================
# HELPER: Get best futures strategy from database
# ============================================================================

def get_best_futures_strategy_from_db(db_path: str = "coordinator.db") -> Optional[Dict]:
    """Get the best futures strategy from the results database."""
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return None

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Look for futures strategies
        c.execute("""
            SELECT r.strategy_genome, r.pnl, r.trades, r.win_rate, r.sharpe_ratio
            FROM results r
            WHERE r.strategy_genome LIKE '%FUTURES%' OR r.strategy_genome LIKE '%leverage%'
            ORDER BY r.sharpe_ratio DESC
            LIMIT 1
        """)
        row = c.fetchone()

        # Fallback to any good strategy
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
            if genome:
                # Ensure futures params
                if 'params' not in genome:
                    genome['params'] = {}
                if 'leverage' not in genome['params']:
                    genome['params']['leverage'] = 3
                if 'direction' not in genome['params']:
                    genome['params']['direction'] = 'BOTH'
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
    """Run futures paper trading standalone."""
    import argparse

    parser = argparse.ArgumentParser(description="Futures Paper Trading")
    parser.add_argument("--contract", default="BIT-27FEB26-CDE", help="Futures contract")
    parser.add_argument("--capital", type=float, default=10000, help="Initial capital")
    parser.add_argument("--leverage", type=int, default=3, help="Leverage (1-10)")
    parser.add_argument("--direction", default="BOTH", help="LONG, SHORT, or BOTH")
    parser.add_argument("--size", type=float, default=0.10, help="Position size %%")
    parser.add_argument("--perpetual", action="store_true", help="Is perpetual contract")
    args = parser.parse_args()

    # Get best strategy
    genome = get_best_futures_strategy_from_db()

    if not genome:
        print("No strategy found. Using default RSI strategy.")
        genome = {
            "entry_rules": [
                {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30}}
            ],
            "params": {
                "sl_pct": 0.03,
                "tp_pct": 0.06,
                "leverage": args.leverage,
                "direction": args.direction
            }
        }

    # Create and run trader
    trader = PaperFuturesTrader(
        strategy_genome=genome,
        initial_capital=args.capital,
        leverage=args.leverage,
        direction=args.direction,
        position_size_pct=args.size,
        is_perpetual=args.perpetual
    )

    try:
        await trader.run(args.contract)
    except KeyboardInterrupt:
        print("\nStopping futures paper trader...")
        trader.stop()


if __name__ == "__main__":
    asyncio.run(main())
