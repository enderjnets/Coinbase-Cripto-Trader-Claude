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
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    print("WARNING: websockets not installed. Run: pip install websockets")

try:
    from risk_manager_live import RiskManager, RiskConfig, SPOT_RISK_CONFIG
    HAS_RISK_MANAGER = True
except ImportError:
    HAS_RISK_MANAGER = False

try:
    from position_sizing import PositionSizer
    HAS_POSITION_SIZER = True
except ImportError:
    HAS_POSITION_SIZER = False

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Fees de Coinbase Advanced (maker/taker)
DEFAULT_FEE_RATE = 0.004  # 0.4% (maker fee)
DEFAULT_SLIPPAGE = 0.002   # 0.2% base (realistic for crypto)
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
# CANDLE AGGREGATOR - Converts ticks to 1-minute OHLCV candles
# ============================================================================

class CandleAggregator:
    """
    Aggregates raw ticks into 1-minute OHLCV candles.

    The backtester trains on 1-minute candles, so indicators must be calculated
    on candles (not raw ticks) for signals to match backtest expectations.
    """

    def __init__(self, candle_interval_sec: int = 60, max_candles: int = 500):
        self.candle_interval = candle_interval_sec
        self.max_candles = max_candles

        # Completed candles (OHLCV)
        self.candles: List[Dict] = []

        # Current forming candle
        self._current_candle: Optional[Dict] = None
        self._candle_start_time: float = 0

    @property
    def candle_count(self) -> int:
        return len(self.candles)

    def add_tick(self, price: float, volume: float, timestamp: float) -> Optional[Dict]:
        """
        Add a tick and return a completed candle if one closed.

        Args:
            price: Tick price
            volume: Tick volume
            timestamp: Unix timestamp

        Returns:
            Completed candle dict if a candle just closed, else None
        """
        # Determine which candle interval this tick belongs to
        candle_slot = int(timestamp // self.candle_interval) * self.candle_interval

        # If no current candle or tick is in a new slot, close current and start new
        if self._current_candle is None:
            self._start_new_candle(price, volume, candle_slot)
            return None

        if candle_slot > self._candle_start_time:
            # Close current candle
            completed = self._close_current_candle()

            # Start new candle with this tick
            self._start_new_candle(price, volume, candle_slot)

            return completed

        # Same candle interval - update OHLCV
        self._current_candle['high'] = max(self._current_candle['high'], price)
        self._current_candle['low'] = min(self._current_candle['low'], price)
        self._current_candle['close'] = price
        self._current_candle['volume'] += volume
        self._current_candle['tick_count'] += 1

        return None

    def _start_new_candle(self, price: float, volume: float, slot_time: float):
        """Start a new candle."""
        self._candle_start_time = slot_time
        self._current_candle = {
            'timestamp': slot_time,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': volume,
            'tick_count': 1,
        }

    def _close_current_candle(self) -> Optional[Dict]:
        """Close the current candle and add to history."""
        if self._current_candle is None:
            return None

        candle = self._current_candle.copy()
        self.candles.append(candle)

        # Trim to max size
        if len(self.candles) > self.max_candles:
            self.candles = self.candles[-self.max_candles:]

        return candle

    def get_close_prices(self) -> np.ndarray:
        """Get array of close prices from completed candles."""
        if not self.candles:
            return np.array([])
        return np.array([c['close'] for c in self.candles])

    def get_high_prices(self) -> np.ndarray:
        if not self.candles:
            return np.array([])
        return np.array([c['high'] for c in self.candles])

    def get_low_prices(self) -> np.ndarray:
        if not self.candles:
            return np.array([])
        return np.array([c['low'] for c in self.candles])

    def get_volumes(self) -> np.ndarray:
        if not self.candles:
            return np.array([])
        return np.array([c['volume'] for c in self.candles])

    def get_state(self) -> Dict:
        """Get serializable state for persistence."""
        return {
            'candles': self.candles[-200:],
            'current_candle': self._current_candle,
            'candle_start_time': self._candle_start_time,
        }

    def load_state(self, state: Dict):
        """Restore from saved state."""
        self.candles = state.get('candles', [])
        self._current_candle = state.get('current_candle')
        self._candle_start_time = state.get('candle_start_time', 0)


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
        product_id: str = "BTC-USD",
        use_risk_manager: bool = True,
    ):
        self.strategy_genome = strategy_genome
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.position_size_pct = position_size_pct
        self.max_position_pct = max_position_pct
        self.product_id = product_id

        # Position tracking
        self.position: Optional[Dict] = None
        self.trades: List[Dict] = []

        # Candle aggregator: converts ticks to 1-minute candles
        # Indicators are calculated on candles, matching backtester behavior
        self.candle_agg = CandleAggregator(candle_interval_sec=60, max_candles=500)
        self.min_candles_for_warmup = 200  # Need >=200 candles before trading

        # Legacy price/volume history (kept for state persistence compatibility)
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.max_history = 500

        # Running state
        self.running = False
        self.start_time: Optional[float] = None
        self.last_price: float = 0.0
        self._ticks_received = 0
        self._candles_formed = 0

        # Risk Manager integration
        self.risk_manager = None
        if use_risk_manager and HAS_RISK_MANAGER:
            self.risk_manager = RiskManager(
                initial_balance=initial_capital,
                config=SPOT_RISK_CONFIG,
                db_path="/tmp/paper_risk_manager.db"
            )
            print(f"[PaperTrader] Risk Manager active (daily loss limit: {SPOT_RISK_CONFIG.max_daily_loss_pct:.0%})")

        # Position Sizer integration
        self.position_sizer = None
        if HAS_POSITION_SIZER:
            self.position_sizer = PositionSizer(
                capital=initial_capital,
                method='fixed',
                default_fixed_pct=position_size_pct
            )

        # Load previous state if exists
        self._load_state()

    def _calculate_realistic_slippage(self, price: float, position_value: float) -> float:
        """Calculate realistic slippage based on position size."""
        slippage_pct = self.slippage  # 0.2% base
        if position_value > 10000:
            slippage_pct += ((position_value - 10000) / 10000) * 0.0005
        return price * min(slippage_pct, 0.02)  # Cap at 2%

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
                # Restore candle aggregator state
                candle_state = state.get('candle_aggregator')
                if candle_state:
                    self.candle_agg.load_state(candle_state)
                print(f"[PaperTrader] Loaded state: ${self.capital:.2f}, {len(self.trades)} trades, "
                      f"{self.candle_agg.candle_count} candles")
            except Exception as e:
                print(f"[PaperTrader] Could not load state: {e}")

    def _save_state(self):
        """Save current state to file."""
        state = {
            'capital': self.capital,
            'trades': self.trades[-100:],
            'price_history': self.price_history[-200:],
            'volume_history': self.volume_history[-200:],
            'candle_aggregator': self.candle_agg.get_state(),
            'timestamp': time.time()
        }
        try:
            with open(PAPER_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[PaperTrader] Could not save state: {e}")

    def _get_indicators(self) -> Dict[str, float]:
        """Calculate all indicators from completed 1-minute candles.

        Uses candle close prices (not raw ticks) to match backtester behavior.
        The backtester trains on 1-minute OHLCV candles, so indicators must
        be computed on the same timeframe for signals to be consistent.
        """
        candle_count = self.candle_agg.candle_count
        if candle_count < 10:
            return {}

        prices = self.candle_agg.get_close_prices()
        highs = self.candle_agg.get_high_prices()
        lows = self.candle_agg.get_low_prices()
        volumes = self.candle_agg.get_volumes()

        indicators = {
            'close': float(prices[-1]),
            'high': float(highs[-1]),
            'low': float(lows[-1]),
            'volume': float(volumes[-1]) if len(volumes) > 0 else 0,
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
        """Simulate buy with realistic costs and risk management."""
        # Calculate position size
        if self.position_sizer:
            self.position_sizer.capital = self.capital
            result = self.position_sizer.calculate()
            size_usd = result.size_usd
        else:
            size_usd = self.capital * self.position_size_pct

        if size_usd < 10:
            return False  # Skip dust trades

        # Risk Manager check
        if self.risk_manager:
            direction = self.strategy_genome.get('params', {}).get('direction', 'LONG')
            leverage = self.strategy_genome.get('params', {}).get('leverage', 1)
            current_positions = {self.product_id: self.position} if self.position else {}

            can_open, reason = self.risk_manager.can_open_position(
                product_id=self.product_id,
                side=direction,
                leverage=leverage,
                margin_usd=size_usd,
                current_positions=current_positions
            )
            if not can_open:
                print(f"[RISK] Trade blocked: {reason}")
                return False

        # Simulate latency
        await asyncio.sleep(DEFAULT_LATENCY_MS / 1000.0)

        # Apply realistic slippage (buy at slightly higher price)
        slippage_amount = self._calculate_realistic_slippage(price, size_usd)
        fill_price = price + slippage_amount

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

        # Apply realistic slippage (sell at slightly lower price)
        sell_value = self.position['size_crypto'] * price
        slippage_amount = self._calculate_realistic_slippage(price, sell_value)
        fill_price = price - slippage_amount

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

        # Record trade in Risk Manager
        if self.risk_manager:
            from risk_manager_live import TradeRecord
            self.risk_manager.record_trade(TradeRecord(
                timestamp=time.time(),
                product_id=self.product_id,
                side=self.strategy_genome.get('params', {}).get('direction', 'LONG'),
                pnl=pnl,
                pnl_pct=pnl_pct / 100.0,
                reason=reason,
                leverage=self.strategy_genome.get('params', {}).get('leverage', 1),
                margin_used=self.position['size_usd']
            ))
            self.risk_manager.current_balance = self.capital

        # Save state
        self._save_state()

        print(f"[PAPER SELL] {timestamp}: {fill_price:.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%) | {reason}")

        # Clear position
        self.position = None

        return pnl

    async def _process_tick(self, data: Dict):
        """Process incoming tick data.

        Ticks are aggregated into 1-minute candles. Indicators and entry
        signals are only evaluated when a candle closes (every 60 seconds),
        matching the backtester which was trained on 1-minute OHLCV data.

        Exit conditions (SL/TP) are still checked on every tick for realism.
        """
        if data.get('type') not in ['ticker', 'match']:
            return

        price = float(data.get('price', 0))
        volume = float(data.get('size', data.get('volume_24h', 1)))
        timestamp_str = data.get('time', datetime.utcnow().isoformat())

        if price <= 0:
            return

        self.last_price = price
        self._ticks_received += 1

        # Parse timestamp to unix for candle aggregation
        try:
            if isinstance(timestamp_str, str):
                # Coinbase sends ISO format: "2026-03-04T12:00:00.123456Z"
                ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                tick_time = ts.timestamp()
            else:
                tick_time = float(timestamp_str)
        except (ValueError, TypeError):
            tick_time = time.time()

        # Feed tick to candle aggregator
        completed_candle = self.candle_agg.add_tick(price, volume, tick_time)

        # Check exit conditions on EVERY tick (SL/TP must be responsive)
        if self.position:
            direction = self.strategy_genome.get('params', {}).get('direction', 'LONG')

            if direction == 'SHORT':
                # Short: SL is above entry, TP is below entry
                new_sl = price + self.position['trailing_stop']
                if new_sl < self.position['stop_loss']:
                    self.position['stop_loss'] = new_sl

                if price >= self.position['stop_loss']:
                    await self._simulate_sell(price, timestamp_str, "stop_loss")
                    return
                if price <= self.position['take_profit']:
                    await self._simulate_sell(price, timestamp_str, "take_profit")
                    return
            else:
                # Long: original logic
                new_sl = price - self.position['trailing_stop']
                if new_sl > self.position['stop_loss']:
                    self.position['stop_loss'] = new_sl

                if price <= self.position['stop_loss']:
                    await self._simulate_sell(price, timestamp_str, "stop_loss")
                    return
                if price >= self.position['take_profit']:
                    await self._simulate_sell(price, timestamp_str, "take_profit")
                    return

        # Only evaluate entry signals when a candle closes
        if completed_candle is None:
            return

        self._candles_formed += 1

        # Warmup check: need enough candles for indicator calculation
        if self.candle_agg.candle_count < self.min_candles_for_warmup:
            if self._candles_formed % 50 == 0:
                logger.info(f"[PaperTrader] Warmup: {self.candle_agg.candle_count}/{self.min_candles_for_warmup} candles")
                print(f"[PaperTrader] Warmup: {self.candle_agg.candle_count}/{self.min_candles_for_warmup} candles")
            return

        # Evaluate entry on candle close (not on every tick)
        if not self.position:
            indicators = self._get_indicators()
            if indicators and self._evaluate_entry_rules(indicators):
                candle_close = completed_candle['close']
                await self._simulate_buy(candle_close, timestamp_str)

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
        print(f"Direction: {self.strategy_genome.get('params', {}).get('direction', 'LONG')}")
        print(f"Candle Interval: 60s (1-minute candles)")
        print(f"Warmup Candles: {self.min_candles_for_warmup}")
        print(f"Pre-loaded Candles: {self.candle_agg.candle_count}")
        print(f"Risk Manager: {'Active' if self.risk_manager else 'Disabled'}")
        print(f"Position Sizer: {'Active' if self.position_sizer else 'Fixed %'}")
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
        print(f"Ticks Received: {self._ticks_received}")
        print(f"Candles Formed: {self._candles_formed}")
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
            'trades': self.trades[-20:],
            'start_time': self.start_time,
            'candles_formed': self._candles_formed,
            'ticks_received': self._ticks_received,
            'candle_buffer_size': self.candle_agg.candle_count,
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
    Get the best OOS-validated strategy from the results database.

    Only returns strategies that passed OOS validation:
    - is_canonical = 1, is_overfitted = 0
    - oos_trades >= 15, oos_pnl >= 0, oos_degradation <= 0.35

    Returns None if no OOS-validated strategy exists (does NOT fallback to non-OOS).
    """
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return None

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Only OOS-validated strategies
        c.execute("""
            SELECT r.strategy_genome, r.pnl, r.trades, r.win_rate, r.sharpe_ratio,
                   r.oos_pnl, r.oos_trades, r.oos_degradation, r.robustness_score
            FROM results r
            WHERE r.is_canonical = 1
              AND r.is_overfitted = 0
              AND r.oos_trades >= 15
              AND r.oos_pnl >= 0
              AND r.oos_degradation <= 0.35
            ORDER BY r.robustness_score DESC, r.oos_pnl DESC
            LIMIT 1
        """)
        row = c.fetchone()

        conn.close()

        if row:
            genome = json.loads(row[0]) if row[0] else None
            print(f"Loaded OOS-validated strategy: PnL=${row[1]:.2f}, Trades={row[2]}, "
                  f"WinRate={row[3]*100:.1f}%, Sharpe={row[4]:.2f}, "
                  f"OOS_PnL=${row[5]:.2f}, OOS_Trades={row[6]}, "
                  f"OOS_Degradation={row[7]:.2f}, Robustness={row[8]:.0f}/100")
            return genome

        print("No OOS-validated strategy found. All strategies overfitted or insufficient OOS data.")
        return None

    except Exception as e:
        print(f"Error loading strategy: {e}")
        return None


def get_best_oos_strategy(db_path: str = "coordinator.db") -> Optional[Dict]:
    """
    Get the best OOS-validated strategy with full metadata.

    Returns dict with 'genome' + 'metadata' (asset, timeframe, OOS metrics, result_id)
    or None if no OOS-validated strategy exists.
    """
    if not os.path.exists(db_path):
        return None

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("""
            SELECT r.id as result_id, r.strategy_genome, r.pnl, r.trades, r.win_rate,
                   r.sharpe_ratio, r.max_drawdown,
                   r.oos_pnl, r.oos_trades, r.oos_degradation, r.robustness_score,
                   w.strategy_params
            FROM results r
            JOIN work_units w ON r.work_unit_id = w.id
            WHERE r.is_canonical = 1
              AND r.is_overfitted = 0
              AND r.oos_trades >= 15
              AND r.oos_pnl >= 0
              AND r.oos_degradation <= 0.35
            ORDER BY r.robustness_score DESC, r.oos_pnl DESC
            LIMIT 1
        """)
        row = c.fetchone()
        conn.close()

        if not row:
            return None

        genome = json.loads(row['strategy_genome']) if row['strategy_genome'] else None
        if not genome:
            return None

        # Extract asset from data_file in strategy_params
        strategy_params = json.loads(row['strategy_params']) if row['strategy_params'] else {}
        data_file = strategy_params.get('data_file', '')

        # Determine Coinbase product from data file name
        # e.g. "BTC-USD_ONE_MINUTE.csv" -> "BTC-USD"
        product_id = "BTC-USD"  # default
        if data_file:
            parts = data_file.split('_')
            if len(parts) >= 2 and '-' in parts[0]:
                product_id = parts[0]  # e.g. "BTC-USD", "ETH-USD"

        return {
            'genome': genome,
            'result_id': row['result_id'],
            'product_id': product_id,
            'data_file': data_file,
            'metrics': {
                'pnl': row['pnl'],
                'trades': row['trades'],
                'win_rate': row['win_rate'],
                'sharpe_ratio': row['sharpe_ratio'],
                'max_drawdown': row['max_drawdown'],
            },
            'oos_metrics': {
                'oos_pnl': row['oos_pnl'],
                'oos_trades': row['oos_trades'],
                'oos_degradation': row['oos_degradation'],
                'robustness_score': row['robustness_score'],
            },
        }

    except Exception as e:
        print(f"Error loading OOS strategy: {e}")
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
    parser.add_argument("--dry-run", action="store_true", help="Dry run: connect and show candle formation without trading")
    args = parser.parse_args()

    # Get best OOS-validated strategy
    strategy_data = get_best_oos_strategy()

    if strategy_data:
        genome = strategy_data['genome']
        # Use the product from the strategy's data file if not explicitly specified
        if args.product == "BTC-USD" and strategy_data['product_id'] != "BTC-USD":
            args.product = strategy_data['product_id']
            print(f"Auto-selected product: {args.product} (from strategy data)")
        oos = strategy_data['oos_metrics']
        print(f"OOS Metrics: PnL=${oos['oos_pnl']:.2f}, Trades={oos['oos_trades']}, "
              f"Degradation={oos['oos_degradation']:.2f}, Robustness={oos['robustness_score']:.0f}/100")
    else:
        # Fallback to legacy function for backwards compatibility
        genome = get_best_strategy_from_db()

    if not genome:
        print("No OOS-validated strategy found. Paper trading requires a strategy that passed OOS validation.")
        print("Waiting for genetic algorithm to produce a robust strategy...")
        return

    # Create and run trader
    trader = LivePaperTrader(
        strategy_genome=genome,
        initial_capital=args.capital,
        position_size_pct=args.size,
        product_id=args.product,
        use_risk_manager=True
    )

    try:
        await trader.run(args.product)
    except KeyboardInterrupt:
        print("\nStopping paper trader...")
        trader.stop()


if __name__ == "__main__":
    asyncio.run(main())
