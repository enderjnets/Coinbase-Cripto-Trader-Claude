"""
numba_futures_backtester.py - Numba JIT Accelerated Futures Backtester
======================================================================
Phase 1 of GPU acceleration: CPU JIT compilation for futures trading.

Provides a fast backtester for futures with:
- Long and Short positions
- Leverage 1x-10x (Coinbase max)
- Funding rates (hourly for perpetuos)
- Margin intraday (10%) vs overnight (25-30%)
- Liquidation simulation
- Futures fees: 0.02% maker / 0.05% taker

Usage:
    from numba_futures_backtester import numba_evaluate_futures_population
    results = numba_evaluate_futures_population(df, population, risk_level)
"""

import numpy as np
import pandas as pd
import time
import os

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    print("WARNING: Numba not installed. GPU/JIT acceleration unavailable.")

# ============================================================================
# FUTURES-SPECIFIC CONSTANTS
# ============================================================================

# Maximum leverage allowed by Coinbase
MAX_LEVERAGE = 10.0

# Margin requirements
INTRADAY_MARGIN = 0.10     # 10% margin for intraday
OVERNIGHT_MARGIN = 0.25    # 25% margin for overnight

# Maintenance margin (liquidation threshold)
MAINTENANCE_MARGIN = 0.05  # 5%

# Futures fees (lower than spot)
FEE_MAKER = 0.0002  # 0.02%
FEE_TAKER = 0.0005  # 0.05%

# ============================================================================
# SLIPPAGE MODELING (PHASE 3A - Realistic Execution)
# ============================================================================
# Base slippage for crypto futures (market orders)
SLIPPAGE_BASE = 0.0003  # 0.03% base slippage

# Volatility multiplier (higher ATR = more slippage)
SLIPPAGE_VOLATILITY_MULT = 0.5  # 50% of volatility added

# Position size impact (larger positions = more market impact)
SLIPPAGE_SIZE_BASE = 50000.0  # $50k position = no size impact
SLIPPAGE_SIZE_MULT = 0.0001  # Additional 0.01% per $50k over base

# Maximum slippage cap (prevent absurd values)
SLIPPAGE_MAX = 0.005  # 0.5% max slippage

# Funding rate (average for BTC/ETH perpetuals)
DEFAULT_FUNDING_RATE = 0.0001  # 0.01% per 8 hours
FUNDING_INTERVAL_CANDLES = 60  # Every 60 candles (1 hour for 1-min data)

# ============================================================================
# SAFETY LIMITS
# ============================================================================

MAX_BALANCE = 1_000_000.0
MAX_POSITION_VALUE = 100_000.0
MAX_PNL = 1_000_000.0
MIN_PRICE = 0.00001
MAX_PRICE = 1_000_000.0

# ============================================================================
# INDICATOR ID MAPPING (same as spot backtester)
# ============================================================================

IND_CLOSE = 0
IND_HIGH = 1
IND_LOW = 2
IND_VOLUME = 3

IND_RSI_10 = 4
IND_RSI_14 = 5
IND_RSI_20 = 6
IND_RSI_50 = 7
IND_RSI_100 = 8
IND_RSI_200 = 9

IND_SMA_10 = 10
IND_SMA_14 = 11
IND_SMA_20 = 12
IND_SMA_50 = 13
IND_SMA_100 = 14
IND_SMA_200 = 15

IND_EMA_10 = 16
IND_EMA_14 = 17
IND_EMA_20 = 18
IND_EMA_50 = 19
IND_EMA_100 = 20
IND_EMA_200 = 21

IND_VOLSMA_10 = 22
IND_VOLSMA_14 = 23
IND_VOLSMA_20 = 24
IND_VOLSMA_50 = 25
IND_VOLSMA_100 = 26
IND_VOLSMA_200 = 27

NUM_INDICATORS = 28
IND_CONSTANT = 99

OP_GT = 0
OP_LT = 1

# Direction encoding
DIR_LONG = 0
DIR_SHORT = 1
DIR_BOTH = 2

MAX_RULES = 3

# ============================================================================
# GENOME ENCODING FOR FUTURES
# ============================================================================
#
# Layout (24 floats for futures):
# [0] sl_pct
# [1] tp_pct
# [2] size_pct
# [3] max_positions
# [4] num_rules
# [5] leverage          # 1.0 - 10.0
# [6] direction         # 0=LONG, 1=SHORT, 2=BOTH
# [7] funding_threshold # Max funding rate to hold (0.0-0.01)
# For each rule r (0-2), base = 8 + r*5:
# [base+0] left_id
# [base+1] left_const
# [base+2] right_id
# [base+3] right_const
# [base+4] op

GENOME_SIZE_FUTURES = 24

# Mapping from (indicator_name, period) to matrix index
INDICATOR_MAP = {
    ('close', 0): IND_CLOSE,
    ('high', 0): IND_HIGH,
    ('low', 0): IND_LOW,
    ('volume', 0): IND_VOLUME,
    ('RSI', 10): IND_RSI_10, ('RSI', 14): IND_RSI_14, ('RSI', 20): IND_RSI_20,
    ('RSI', 50): IND_RSI_50, ('RSI', 100): IND_RSI_100, ('RSI', 200): IND_RSI_200,
    ('SMA', 10): IND_SMA_10, ('SMA', 14): IND_SMA_14, ('SMA', 20): IND_SMA_20,
    ('SMA', 50): IND_SMA_50, ('SMA', 100): IND_SMA_100, ('SMA', 200): IND_SMA_200,
    ('EMA', 10): IND_EMA_10, ('EMA', 14): IND_EMA_14, ('EMA', 20): IND_EMA_20,
    ('EMA', 50): IND_EMA_50, ('EMA', 100): IND_EMA_100, ('EMA', 200): IND_EMA_200,
    ('VOLSMA', 10): IND_VOLSMA_10, ('VOLSMA', 14): IND_VOLSMA_14, ('VOLSMA', 20): IND_VOLSMA_20,
    ('VOLSMA', 50): IND_VOLSMA_50, ('VOLSMA', 100): IND_VOLSMA_100, ('VOLSMA', 200): IND_VOLSMA_200,
}

PERIODS = [10, 14, 20, 50, 100, 200]


# ============================================================================
# INDICATOR PRE-COMPUTATION (same as spot)
# ============================================================================

def precompute_indicators(df):
    """Pre-compute ALL possible indicators as a numpy matrix."""
    n = len(df)
    indicators = np.full((NUM_INDICATORS, n), np.nan, dtype=np.float64)

    close = df['close'].values.astype(np.float64)
    high = df['high'].values.astype(np.float64)
    low = df['low'].values.astype(np.float64)
    volume = df['volume'].values.astype(np.float64)

    # Data validation
    close = np.clip(close, MIN_PRICE, MAX_PRICE)
    high = np.clip(high, MIN_PRICE, MAX_PRICE)
    low = np.clip(low, MIN_PRICE, MAX_PRICE)
    volume = np.clip(volume, 0.0, 1e15)

    close = np.nan_to_num(close, nan=1.0, posinf=MAX_PRICE, neginf=MIN_PRICE)
    high = np.nan_to_num(high, nan=1.0, posinf=MAX_PRICE, neginf=MIN_PRICE)
    low = np.nan_to_num(low, nan=1.0, posinf=MAX_PRICE, neginf=MIN_PRICE)
    volume = np.nan_to_num(volume, nan=0.0, posinf=1e12, neginf=0.0)

    indicators[IND_CLOSE] = close
    indicators[IND_HIGH] = high
    indicators[IND_LOW] = low
    indicators[IND_VOLUME] = volume

    close_series = pd.Series(close)
    volume_series = pd.Series(volume)

    for i, period in enumerate(PERIODS):
        # RSI
        delta = close_series.diff()
        gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        rsi = rsi.fillna(50.0)
        indicators[IND_RSI_10 + i] = rsi.values

        # SMA
        sma = close_series.rolling(window=period).mean()
        indicators[IND_SMA_10 + i] = sma.values

        # EMA
        ema = close_series.ewm(span=period, adjust=False).mean()
        indicators[IND_EMA_10 + i] = ema.values

        # VOLSMA
        volsma = volume_series.rolling(window=period).mean()
        indicators[IND_VOLSMA_10 + i] = volsma.values

    return indicators, close, high, low


# ============================================================================
# GENOME ENCODING FOR FUTURES
# ============================================================================

def _resolve_item_id(item):
    """Resolve a rule side (left/right) to indicator ID and constant value."""
    if not isinstance(item, dict):
        return IND_CONSTANT, float(item) if item else 0.0

    if 'value' in item:
        return IND_CONSTANT, float(item['value'])

    if 'indicator' in item:
        name = item['indicator']
        period = item.get('period', 14)
        ind_id = INDICATOR_MAP.get((name, period), -1)
        if ind_id == -1:
            return IND_CONSTANT, 0.0
        return ind_id, 0.0

    if 'field' in item:
        field = item['field']
        field_map = {'close': IND_CLOSE, 'high': IND_HIGH, 'low': IND_LOW, 'volume': IND_VOLUME}
        return field_map.get(field, IND_CONSTANT), 0.0

    return IND_CONSTANT, 0.0


def encode_genome_futures(genome):
    """
    Convert a genome dict to a fixed-size numpy array for Numba futures.

    Layout (24 floats):
    [0] sl_pct
    [1] tp_pct
    [2] size_pct
    [3] max_positions
    [4] num_rules
    [5] leverage
    [6] direction
    [7] funding_threshold
    [8-23] rules (3 rules x 5 fields each)
    """
    encoded = np.zeros(GENOME_SIZE_FUTURES, dtype=np.float64)

    # Basic params
    params = genome.get('params', {})
    encoded[0] = params.get('sl_pct', 0.05)
    encoded[1] = params.get('tp_pct', 0.10)
    encoded[2] = params.get('size_pct', 0.10)
    encoded[3] = params.get('max_positions', 1)

    # Futures-specific params
    encoded[5] = min(params.get('leverage', 3.0), MAX_LEVERAGE)
    direction_str = params.get('direction', 'BOTH').upper()
    if direction_str == 'LONG':
        encoded[6] = DIR_LONG
    elif direction_str == 'SHORT':
        encoded[6] = DIR_SHORT
    else:
        encoded[6] = DIR_BOTH
    encoded[7] = params.get('funding_threshold', 0.001)  # 0.1% default

    # Entry rules
    rules = genome.get('entry_rules', [])
    encoded[4] = min(len(rules), MAX_RULES)

    for r_idx, rule in enumerate(rules[:MAX_RULES]):
        base = 8 + r_idx * 5

        left = rule.get('left', {})
        encoded[base], encoded[base + 1] = _resolve_item_id(left)

        right = rule.get('right', {})
        encoded[base + 2], encoded[base + 3] = _resolve_item_id(right)

        op = rule.get('op', '>')
        encoded[base + 4] = OP_GT if op == '>' else OP_LT

    return encoded


def decode_genome_futures(encoded):
    """Debug helper: decode futures genome to readable format."""
    inv_map = {v: k for k, v in INDICATOR_MAP.items()}
    inv_map[IND_CONSTANT] = ('CONST', 0)

    direction_names = {DIR_LONG: 'LONG', DIR_SHORT: 'SHORT', DIR_BOTH: 'BOTH'}

    info = {
        'sl_pct': encoded[0],
        'tp_pct': encoded[1],
        'size_pct': encoded[2],
        'max_positions': int(encoded[3]),
        'num_rules': int(encoded[4]),
        'leverage': encoded[5],
        'direction': direction_names.get(int(encoded[6]), 'BOTH'),
        'funding_threshold': encoded[7],
        'rules': []
    }

    for r in range(int(encoded[4])):
        base = 8 + r * 5
        left_id = int(encoded[base])
        left_const = encoded[base + 1]
        right_id = int(encoded[base + 2])
        right_const = encoded[base + 3]
        op = '>' if int(encoded[base + 4]) == OP_GT else '<'

        left_name = inv_map.get(left_id, ('UNKNOWN', 0))
        right_name = inv_map.get(right_id, ('UNKNOWN', 0))

        left_str = f"{left_name[0]}_{left_name[1]}" if left_id != IND_CONSTANT else f"{left_const}"
        right_str = f"{right_name[0]}_{right_name[1]}" if right_id != IND_CONSTANT else f"{right_const}"

        info['rules'].append(f"{left_str} {op} {right_str}")

    return info


# ============================================================================
# NUMBA JIT COMPILED FUTURES BACKTEST KERNEL
# ============================================================================

if HAS_NUMBA:
    @njit(cache=True)
    def _calculate_slippage(price, position_value, atr_pct, is_entry):
        """
        Calculate realistic slippage for market orders.

        Components:
        1. Base slippage (0.03%)
        2. Volatility-adjusted slippage (higher ATR = more slippage)
        3. Position size impact (larger = more market impact)
        4. Entry vs Exit (entries often have more slippage due to urgency)

        Args:
            price: Current price
            position_value: Dollar value of position
            atr_pct: ATR as percentage of price (volatility measure)
            is_entry: True for entry, False for exit

        Returns:
            Slippage as price adjustment (in price units)
        """
        # Base slippage
        slippage_pct = SLIPPAGE_BASE

        # Add volatility component (higher volatility = more slippage)
        if atr_pct > 0:
            slippage_pct += atr_pct * SLIPPAGE_VOLATILITY_MULT

        # Add position size impact
        if position_value > SLIPPAGE_SIZE_BASE:
            size_ratio = (position_value - SLIPPAGE_SIZE_BASE) / SLIPPAGE_SIZE_BASE
            slippage_pct += size_ratio * SLIPPAGE_SIZE_MULT

        # Entry has slightly more slippage (market urgency)
        if is_entry:
            slippage_pct *= 1.1

        # Cap slippage
        if slippage_pct > SLIPPAGE_MAX:
            slippage_pct = SLIPPAGE_MAX

        return price * slippage_pct

    @njit(cache=True)
    def _fast_futures_backtest(close, high, low, indicators, genome_encoded,
                                fee_rate, is_perpetual=True):
        """
        JIT-compiled futures backtest loop for a single genome.

        Features:
        - Long and Short positions
        - Leverage 1x-10x
        - Funding rate payments (hourly for perpetuos)
        - Liquidation simulation
        - Margin management

        Args:
            close: float64[n] - close prices
            high: float64[n] - high prices
            low: float64[n] - low prices
            indicators: float64[NUM_IND, n] - pre-computed indicator matrix
            genome_encoded: float64[24] - encoded futures genome
            fee_rate: float64 - trading fee rate (e.g. 0.0002 for 0.02%)
            is_perpetual: bool - whether this is a perpetual contract

        Returns:
            total_pnl: float64
            num_trades: int64
            wins: int64
            max_drawdown: float64
            sharpe_ratio: float64
            liquidations: int64
        """
        n = len(close)

        # Decode genome
        sl_pct = genome_encoded[0]
        tp_pct = genome_encoded[1]
        size_pct = genome_encoded[2]
        max_positions = int(genome_encoded[3])
        num_rules = int(genome_encoded[4])
        leverage = genome_encoded[5]
        direction = int(genome_encoded[6])
        funding_threshold = genome_encoded[7]

        # Clamp parameters
        if size_pct < 0.05:
            size_pct = 0.05
        if size_pct > 0.95:
            size_pct = 0.95
        if max_positions < 1:
            max_positions = 1
        if max_positions > 3:
            max_positions = 3
        if leverage < 1.0:
            leverage = 1.0
        if leverage > MAX_LEVERAGE:
            leverage = MAX_LEVERAGE

        balance = 500.0  # Starting balance

        # Position arrays (up to 3 positions)
        pos_active = np.zeros(3, dtype=np.int64)      # 0 or 1
        pos_direction = np.zeros(3, dtype=np.int64)   # 0=LONG, 1=SHORT
        pos_entry_price = np.zeros(3, dtype=np.float64)
        pos_size = np.zeros(3, dtype=np.float64)       # contracts
        pos_margin = np.zeros(3, dtype=np.float64)     # margin locked
        pos_cost_basis = np.zeros(3, dtype=np.float64)
        pos_entry_fee = np.zeros(3, dtype=np.float64)
        pos_sl = np.zeros(3, dtype=np.float64)
        pos_tp = np.zeros(3, dtype=np.float64)
        pos_liquidation = np.zeros(3, dtype=np.float64)  # liquidation price

        total_pnl = 0.0
        num_trades = 0
        wins = 0
        liquidations = 0
        peak_balance = balance
        max_drawdown = 0.0
        sum_ret = 0.0
        sum_ret_sq = 0.0

        # Funding rate tracking (simplified - use random variation around average)
        np.random.seed(42)  # Reproducible funding rates
        funding_rates = np.random.normal(0.0001, 0.00005, n)

        # Main loop - starts at 200 for indicator warmup
        for i in range(200, n):
            price = close[i]
            candle_high = high[i]
            candle_low = low[i]

            # === FUNDING RATE PAYMENT (every hour for perpetuos) ===
            if is_perpetual and i % FUNDING_INTERVAL_CANDLES == 0 and i > 200:
                funding_rate = funding_rates[i]
                for s in range(3):
                    if pos_active[s] == 1:
                        # Position value
                        pos_value = pos_size[s] * price
                        # Funding = position_value * funding_rate
                        funding_cost = pos_value * funding_rate * leverage

                        if pos_direction[s] == DIR_LONG:
                            # Longs pay when funding > 0
                            balance -= funding_cost
                        else:
                            # Shorts receive when funding > 0
                            balance += funding_cost

                        # Safety cap
                        if balance > MAX_BALANCE:
                            balance = MAX_BALANCE
                        if balance < 0:
                            balance = 0

            # === EXIT LOOP: check all positions ===
            for s in range(3):
                if pos_active[s] == 0:
                    continue

                # Check liquidation first
                if pos_direction[s] == DIR_LONG:
                    # Long liquidates when price drops below liquidation price
                    if candle_low <= pos_liquidation[s]:
                        # Liquidation - lose all margin
                        balance -= pos_margin[s]  # Margin is already deducted
                        liquidations += 1
                        num_trades += 1
                        total_pnl -= pos_margin[s]
                        pos_active[s] = 0
                        continue
                else:
                    # Short liquidates when price rises above liquidation price
                    if candle_high >= pos_liquidation[s]:
                        balance -= pos_margin[s]
                        liquidations += 1
                        num_trades += 1
                        total_pnl -= pos_margin[s]
                        pos_active[s] = 0
                        continue

                # Trailing stop calculation
                if pos_direction[s] == DIR_LONG:
                    new_sl = price - (pos_entry_price[s] * sl_pct * 0.8)
                    if new_sl > pos_sl[s]:
                        pos_sl[s] = new_sl
                else:
                    new_sl = price + (pos_entry_price[s] * sl_pct * 0.8)
                    if new_sl < pos_sl[s]:
                        pos_sl[s] = new_sl

                # Check exit conditions
                sl_hit = False
                tp_hit = False

                if pos_direction[s] == DIR_LONG:
                    sl_hit = candle_low <= pos_sl[s]
                    tp_hit = candle_high >= pos_tp[s]
                else:
                    sl_hit = candle_high >= pos_sl[s]
                    tp_hit = candle_low <= pos_tp[s]

                if sl_hit or tp_hit:
                    if sl_hit:
                        exit_price = pos_sl[s]
                    else:
                        exit_price = pos_tp[s]

                    # === APPLY SLIPPAGE TO EXIT ===
                    # Calculate local volatility (ATR proxy using high-low)
                    atr_pct = (candle_high - candle_low) / price if price > 0 else 0.01

                    # Apply slippage against the exit direction
                    slippage = _calculate_slippage(price, pos_cost_basis[s], atr_pct, is_entry=False)
                    if pos_direction[s] == DIR_LONG:
                        # Long exit (sell): get slightly worse price
                        exit_price = exit_price * (1.0 - slippage/price)
                    else:
                        # Short exit (buy): pay slightly higher price
                        exit_price = exit_price * (1.0 + slippage/price)

                    # Calculate PnL with leverage
                    if pos_direction[s] == DIR_LONG:
                        pnl_pct = (exit_price - pos_entry_price[s]) / pos_entry_price[s]
                    else:
                        pnl_pct = (pos_entry_price[s] - exit_price) / pos_entry_price[s]

                    # Position value at exit
                    exit_value = pos_size[s] * exit_price
                    exit_fee = exit_value * fee_rate

                    # PnL = (pnl_pct * leverage * position_value) - fees
                    trade_pnl = (pnl_pct * leverage * pos_cost_basis[s]) - pos_entry_fee[s] - exit_fee

                    # Return margin + PnL
                    balance += pos_margin[s] + trade_pnl

                    # Safety cap
                    if balance > MAX_BALANCE:
                        balance = MAX_BALANCE
                    if trade_pnl > MAX_POSITION_VALUE:
                        trade_pnl = MAX_POSITION_VALUE
                    if trade_pnl < -MAX_POSITION_VALUE:
                        trade_pnl = -MAX_POSITION_VALUE

                    total_pnl += trade_pnl
                    num_trades += 1
                    if trade_pnl > 0.0:
                        wins += 1

                    # Track metrics
                    if pos_margin[s] > 0.0:
                        ret = trade_pnl / pos_margin[s]
                        sum_ret += ret
                        sum_ret_sq += ret * ret
                    if balance > peak_balance:
                        peak_balance = balance
                    if peak_balance > 0.0:
                        dd = (peak_balance - balance) / peak_balance
                        if dd > max_drawdown:
                            max_drawdown = dd

                    pos_active[s] = 0

            # === ENTRY: evaluate rules and open if slot available ===
            num_open = 0
            for s in range(3):
                num_open += pos_active[s]

            if num_open < max_positions:
                # Determine entry direction based on genome
                entry_direction = -1  # -1 = not set

                if direction == DIR_LONG:
                    # Only check long conditions
                    all_rules_pass = True
                    if num_rules == 0:
                        all_rules_pass = False
                    for r in range(num_rules):
                        base = 8 + r * 5
                        left_id = int(genome_encoded[base])
                        left_const = genome_encoded[base + 1]
                        right_id = int(genome_encoded[base + 2])
                        right_const = genome_encoded[base + 3]
                        op = int(genome_encoded[base + 4])

                        if left_id == 99:
                            val_a = left_const
                        elif left_id >= 0 and left_id < 28:
                            val_a = indicators[left_id, i]
                        else:
                            val_a = 0.0

                        if right_id == 99:
                            val_b = right_const
                        elif right_id >= 0 and right_id < 28:
                            val_b = indicators[right_id, i]
                        else:
                            val_b = 0.0

                        if np.isnan(val_a) or np.isnan(val_b):
                            all_rules_pass = False
                            break

                        if op == 0:
                            if not (val_a > val_b):
                                all_rules_pass = False
                                break
                        else:
                            if not (val_a < val_b):
                                all_rules_pass = False
                                break

                    if all_rules_pass:
                        entry_direction = DIR_LONG

                elif direction == DIR_SHORT:
                    # Only check short conditions (inverted rules)
                    all_rules_pass = True
                    if num_rules == 0:
                        all_rules_pass = False
                    for r in range(num_rules):
                        base = 8 + r * 5
                        left_id = int(genome_encoded[base])
                        left_const = genome_encoded[base + 1]
                        right_id = int(genome_encoded[base + 2])
                        right_const = genome_encoded[base + 3]
                        op = int(genome_encoded[base + 4])

                        if left_id == 99:
                            val_a = left_const
                        elif left_id >= 0 and left_id < 28:
                            val_a = indicators[left_id, i]
                        else:
                            val_a = 0.0

                        if right_id == 99:
                            val_b = right_const
                        elif right_id >= 0 and right_id < 28:
                            val_b = indicators[right_id, i]
                        else:
                            val_b = 0.0

                        if np.isnan(val_a) or np.isnan(val_b):
                            all_rules_pass = False
                            break

                        # Inverted for short
                        if op == 0:
                            if not (val_a < val_b):
                                all_rules_pass = False
                                break
                        else:
                            if not (val_a > val_b):
                                all_rules_pass = False
                                break

                    if all_rules_pass:
                        entry_direction = DIR_SHORT

                else:  # DIR_BOTH
                    # Check long conditions first
                    long_pass = True
                    if num_rules > 0:
                        for r in range(num_rules):
                            base = 8 + r * 5
                            left_id = int(genome_encoded[base])
                            left_const = genome_encoded[base + 1]
                            right_id = int(genome_encoded[base + 2])
                            right_const = genome_encoded[base + 3]
                            op = int(genome_encoded[base + 4])

                            if left_id == 99:
                                val_a = left_const
                            elif left_id >= 0 and left_id < 28:
                                val_a = indicators[left_id, i]
                            else:
                                val_a = 0.0

                            if right_id == 99:
                                val_b = right_const
                            elif right_id >= 0 and right_id < 28:
                                val_b = indicators[right_id, i]
                            else:
                                val_b = 0.0

                            if np.isnan(val_a) or np.isnan(val_b):
                                long_pass = False
                                break

                            if op == 0:
                                if not (val_a > val_b):
                                    long_pass = False
                                    break
                            else:
                                if not (val_a < val_b):
                                    long_pass = False
                                    break

                    # Check short conditions
                    short_pass = True
                    if num_rules > 0:
                        for r in range(num_rules):
                            base = 8 + r * 5
                            left_id = int(genome_encoded[base])
                            left_const = genome_encoded[base + 1]
                            right_id = int(genome_encoded[base + 2])
                            right_const = genome_encoded[base + 3]
                            op = int(genome_encoded[base + 4])

                            if left_id == 99:
                                val_a = left_const
                            elif left_id >= 0 and left_id < 28:
                                val_a = indicators[left_id, i]
                            else:
                                val_a = 0.0

                            if right_id == 99:
                                val_b = right_const
                            elif right_id >= 0 and right_id < 28:
                                val_b = indicators[right_id, i]
                            else:
                                val_b = 0.0

                            if np.isnan(val_a) or np.isnan(val_b):
                                short_pass = False
                                break

                            # Inverted for short
                            if op == 0:
                                if not (val_a < val_b):
                                    short_pass = False
                                    break
                            else:
                                if not (val_a > val_b):
                                    short_pass = False
                                    break

                    if long_pass:
                        entry_direction = DIR_LONG
                    elif short_pass:
                        entry_direction = DIR_SHORT

                # Open position
                if entry_direction >= 0:
                    # Calculate margin requirement
                    position_value = balance * size_pct
                    if position_value > MAX_POSITION_VALUE:
                        position_value = MAX_POSITION_VALUE

                    # Margin = position_value / leverage
                    margin_required = position_value / leverage

                    if margin_required >= 10.0 and balance >= margin_required:
                        # Find free slot
                        slot = -1
                        for s in range(3):
                            if pos_active[s] == 0:
                                slot = s
                                break

                        if slot >= 0:
                            entry_fee = position_value * fee_rate
                            balance -= margin_required

                            pos_active[slot] = 1
                            pos_direction[slot] = entry_direction

                            # === APPLY SLIPPAGE TO ENTRY ===
                            # Calculate local volatility (ATR proxy using high-low)
                            atr_pct = (candle_high - candle_low) / price if price > 0 else 0.01
                            entry_slippage = _calculate_slippage(price, position_value, atr_pct, is_entry=True)

                            if entry_direction == DIR_LONG:
                                # Long entry (buy): pay slightly higher price
                                actual_entry_price = price * (1.0 + entry_slippage/price)
                            else:
                                # Short entry (sell): get slightly lower price
                                actual_entry_price = price * (1.0 - entry_slippage/price)

                            pos_entry_price[slot] = actual_entry_price
                            pos_size[slot] = position_value / actual_entry_price  # Contracts
                            pos_margin[slot] = margin_required
                            pos_cost_basis[slot] = position_value
                            pos_entry_fee[slot] = entry_fee

                            if entry_direction == DIR_LONG:
                                # Long: SL below entry, TP above entry
                                pos_sl[slot] = price * (1.0 - sl_pct)
                                pos_tp[slot] = price * (1.0 + tp_pct)
                                # Liquidation: when price drops enough to wipe margin
                                pos_liquidation[slot] = price * (1.0 - (1.0/leverage) + MAINTENANCE_MARGIN)
                            else:
                                # Short: SL above entry, TP below entry
                                pos_sl[slot] = price * (1.0 + sl_pct)
                                pos_tp[slot] = price * (1.0 - tp_pct)
                                # Liquidation: when price rises enough to wipe margin
                                pos_liquidation[slot] = price * (1.0 + (1.0/leverage) - MAINTENANCE_MARGIN)

        # === CLOSE ALL OPEN POSITIONS AT END ===
        final_price = close[n - 1]
        final_high = high[n - 1]
        final_low = low[n - 1]

        for s in range(3):
            if pos_active[s] == 1:
                # Apply slippage to final exit
                final_atr_pct = (final_high - final_low) / final_price if final_price > 0 else 0.01
                final_slippage = _calculate_slippage(final_price, pos_cost_basis[s], final_atr_pct, is_entry=False)

                if pos_direction[s] == DIR_LONG:
                    # Long exit (sell): get slightly worse price
                    actual_final_price = final_price * (1.0 - final_slippage/final_price)
                    pnl_pct = (actual_final_price - pos_entry_price[s]) / pos_entry_price[s]
                else:
                    # Short exit (buy): pay slightly higher price
                    actual_final_price = final_price * (1.0 + final_slippage/final_price)
                    pnl_pct = (pos_entry_price[s] - actual_final_price) / pos_entry_price[s]

                exit_value = pos_size[s] * actual_final_price
                exit_fee = exit_value * fee_rate
                trade_pnl = (pnl_pct * leverage * pos_cost_basis[s]) - pos_entry_fee[s] - exit_fee

                balance += pos_margin[s] + trade_pnl

                if balance > MAX_BALANCE:
                    balance = MAX_BALANCE
                if trade_pnl > MAX_POSITION_VALUE:
                    trade_pnl = MAX_POSITION_VALUE
                if trade_pnl < -MAX_POSITION_VALUE:
                    trade_pnl = -MAX_POSITION_VALUE

                total_pnl += trade_pnl
                num_trades += 1
                if trade_pnl > 0.0:
                    wins += 1

                if pos_margin[s] > 0.0:
                    ret = trade_pnl / pos_margin[s]
                    sum_ret += ret
                    sum_ret_sq += ret * ret
                if balance > peak_balance:
                    peak_balance = balance
                if peak_balance > 0.0:
                    dd = (peak_balance - balance) / peak_balance
                    if dd > max_drawdown:
                        max_drawdown = dd

                pos_active[s] = 0

        # Compute Sharpe Ratio
        sharpe_ratio = 0.0
        if num_trades > 1:
            mean_ret = sum_ret / num_trades
            var = (sum_ret_sq / num_trades) - (mean_ret * mean_ret)
            if var < 1e-10:
                var = 1e-10
            std = var ** 0.5
            sharpe_ratio = (mean_ret / std) * (252.0 ** 0.5)

        # Final safety checks
        if total_pnl > MAX_PNL:
            total_pnl = MAX_PNL
        if total_pnl < -MAX_PNL:
            total_pnl = -MAX_PNL

        if np.isnan(total_pnl) or np.isinf(total_pnl):
            total_pnl = -10000.0
        if np.isnan(max_drawdown) or np.isinf(max_drawdown):
            max_drawdown = 1.0
        if np.isnan(sharpe_ratio) or np.isinf(sharpe_ratio):
            sharpe_ratio = 0.0

        if max_drawdown > 1.0:
            max_drawdown = 1.0
        if max_drawdown < 0.0:
            max_drawdown = 0.0

        return total_pnl, num_trades, wins, max_drawdown, sharpe_ratio, liquidations


# ============================================================================
# PUBLIC API
# ============================================================================

def numba_evaluate_futures_population(df, population, risk_level="LOW",
                                       progress_cb=None, cancel_event=None,
                                       is_perpetual=True):
    """
    Evaluate an entire population of futures genomes using Numba JIT.

    Args:
        df: pandas DataFrame with OHLCV data
        population: list of genome dicts with futures params
        risk_level: unused (kept for API compatibility)
        progress_cb: callback(float) for progress updates
        cancel_event: threading.Event to cancel evaluation
        is_perpetual: bool - whether this is a perpetual contract

    Returns:
        list of dicts: [{'metrics': {...}}, ...]
    """
    if not HAS_NUMBA:
        raise RuntimeError("Numba not installed. Cannot use JIT acceleration.")

    total = len(population)

    # Pre-compute indicators once
    t0 = time.time()
    indicators, close, high, low = precompute_indicators(df)
    t_indicators = time.time() - t0

    # Encode all genomes
    genomes_encoded = np.array([encode_genome_futures(g) for g in population], dtype=np.float64)

    # Fee rate (futures is lower)
    fee_rate = FEE_MAKER

    # Warmup JIT
    t_warmup = time.time()
    _fast_futures_backtest(close, high, low, indicators, genomes_encoded[0], fee_rate, is_perpetual)
    t_warmup = time.time() - t_warmup

    # Run all backtests
    t_run = time.time()
    results = []

    for i in range(total):
        if cancel_event and cancel_event.is_set():
            return []

        total_pnl, num_trades, num_wins, max_dd, sharpe, liqs = _fast_futures_backtest(
            close, high, low, indicators, genomes_encoded[i], fee_rate, is_perpetual
        )

        win_rate = (num_wins / num_trades * 100.0) if num_trades > 0 else 0.0

        if num_trades == 0:
            total_pnl = -10000.0

        results.append({
            'metrics': {
                'Total PnL': round(total_pnl, 2),
                'Total Trades': num_trades,
                'Win Rate %': round(win_rate, 2),
                'Sharpe Ratio': round(sharpe, 4),
                'Max Drawdown': round(max_dd, 4),
                'Liquidations': liqs
            }
        })

        if progress_cb:
            progress_cb((i + 1) / total)

    t_run = time.time() - t_run

    total_time = t_indicators + t_warmup + t_run
    print(f"   [Numba Futures] Indicators: {t_indicators:.2f}s | JIT warmup: {t_warmup:.2f}s | "
          f"{total} backtests: {t_run:.2f}s | Total: {total_time:.2f}s")

    return results


def warmup_jit_futures():
    """Pre-compile the JIT function at worker startup."""
    if not HAS_NUMBA:
        return

    n = 300
    close = np.random.uniform(90, 110, n)
    high = close + np.random.uniform(0, 2, n)
    low = close - np.random.uniform(0, 2, n)
    indicators = np.random.uniform(0, 100, (NUM_INDICATORS, n))

    genome = np.zeros(GENOME_SIZE_FUTURES, dtype=np.float64)
    genome[0] = 0.02   # sl_pct
    genome[1] = 0.04   # tp_pct
    genome[2] = 0.10   # size_pct
    genome[3] = 1.0    # max_positions
    genome[4] = 1      # 1 rule
    genome[5] = 3.0    # leverage
    genome[6] = DIR_BOTH  # direction
    genome[7] = 0.001  # funding threshold
    genome[8] = IND_RSI_14
    genome[9] = 0.0
    genome[10] = IND_CONSTANT
    genome[11] = 30.0
    genome[12] = OP_LT

    _fast_futures_backtest(close, high, low, indicators, genome, FEE_MAKER, True)


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("NUMBA FUTURES BACKTESTER - Standalone Test")
    print("="*60)

    if not HAS_NUMBA:
        print("ERROR: Numba not installed. Run: pip install numba")
        exit(1)

    print(f"Numba available: {HAS_NUMBA}")

    # Find futures data
    data_path = "data_futures/BIP-20DEC30-CDE_FIVE_MINUTE.csv"
    if not os.path.exists(data_path):
        data_path = "data_futures/BIT-27FEB26-CDE_FIVE_MINUTE.csv"

    if not os.path.exists(data_path):
        print(f"ERROR: No futures data found")
        exit(1)

    print(f"Loading data: {data_path}")
    df = pd.read_csv(data_path).tail(10000).copy()
    df.reset_index(drop=True, inplace=True)
    print(f"Loaded {len(df):,} candles")

    # Test genome
    test_genome = {
        "entry_rules": [
            {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30}}
        ],
        "params": {
            "sl_pct": 0.03,
            "tp_pct": 0.06,
            "leverage": 5,
            "direction": "BOTH"
        }
    }

    print(f"\nTest genome: RSI_14 < 30, SL=3%, TP=6%, Leverage=5x, Direction=BOTH")

    # Warmup
    print("\nWarming up JIT compiler...")
    warmup_jit_futures()

    # Test single backtest
    print("\nRunning single backtest...")
    t0 = time.time()
    results = numba_evaluate_futures_population(df, [test_genome], is_perpetual=True)
    t_single = time.time() - t0

    print(f"\nResults:")
    for k, v in results[0]['metrics'].items():
        print(f"  {k}: {v}")
    print(f"\nTime: {t_single:.3f}s")

    # Test population
    print("\n" + "="*60)
    print("BENCHMARK: 20-genome population evaluation")
    print("="*60)

    population = []
    for _ in range(20):
        g = {
            "entry_rules": [
                {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30}}
            ],
            "params": {
                "sl_pct": np.random.uniform(0.01, 0.05),
                "tp_pct": np.random.uniform(0.02, 0.10),
                "leverage": np.random.randint(2, 8),
                "direction": np.random.choice(["LONG", "SHORT", "BOTH"])
            }
        }
        population.append(g)

    t0 = time.time()
    results = numba_evaluate_futures_population(df, population, is_perpetual=True)
    t_pop = time.time() - t0

    print(f"\nNumba Futures: {t_pop:.2f}s for 20 genomes ({t_pop/20:.3f}s per genome)")

    pnls = [r['metrics']['Total PnL'] for r in results]
    trades_list = [r['metrics']['Total Trades'] for r in results]
    liqs = [r['metrics']['Liquidations'] for r in results]

    print(f"\nResults summary:")
    print(f"  PnL range: ${min(pnls):,.2f} to ${max(pnls):,.2f}")
    print(f"  Trades range: {min(trades_list)} to {max(trades_list)}")
    print(f"  Total liquidations: {sum(liqs)}")
    print(f"  Genomes with trades: {sum(1 for t in trades_list if t > 0)}/20")

    print("\nDone!")
