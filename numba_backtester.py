"""
numba_backtester.py - Numba JIT Accelerated Backtester
======================================================
Phase 1 of GPU acceleration: CPU JIT compilation.

Provides a fast alternative to backtester.py for evaluating populations
of DynamicStrategy genomes during genetic algorithm evolution.

Pre-computes ALL indicators once, encodes genomes as numpy arrays,
and runs the backtest loop as compiled native code via Numba JIT.

Expected speedup: 50-100x over pure Python backtester.

Usage:
    from numba_backtester import numba_evaluate_population
    results = numba_evaluate_population(df, population, risk_level)
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
# INDICATOR ID MAPPING
# ============================================================================
# Fixed layout for the indicator matrix [NUM_INDICATORS, n_candles]

IND_CLOSE = 0
IND_HIGH = 1
IND_LOW = 2
IND_VOLUME = 3

# RSI variants (periods: 10, 14, 20, 50, 100, 200)
IND_RSI_10 = 4
IND_RSI_14 = 5
IND_RSI_20 = 6
IND_RSI_50 = 7
IND_RSI_100 = 8
IND_RSI_200 = 9

# SMA variants
IND_SMA_10 = 10
IND_SMA_14 = 11
IND_SMA_20 = 12
IND_SMA_50 = 13
IND_SMA_100 = 14
IND_SMA_200 = 15

# EMA variants
IND_EMA_10 = 16
IND_EMA_14 = 17
IND_EMA_20 = 18
IND_EMA_50 = 19
IND_EMA_100 = 20
IND_EMA_200 = 21

# VOLSMA variants
IND_VOLSMA_10 = 22
IND_VOLSMA_14 = 23
IND_VOLSMA_20 = 24
IND_VOLSMA_50 = 25
IND_VOLSMA_100 = 26
IND_VOLSMA_200 = 27

NUM_INDICATORS = 28

# Special sentinel for constant values
IND_CONSTANT = 99

# Operator encoding
OP_GT = 0  # >
OP_LT = 1  # <

MAX_RULES = 3

# Genome encoding: 20 floats per genome
# [0] sl_pct
# [1] tp_pct
# [2] size_pct        (% of balance per trade, 0.05-0.95)
# [3] max_positions   (1-3 simultaneous positions)
# [4] num_rules
# For each rule r (0-2), base = 5 + r*5:
# [base+0] left_id, [base+1] left_const, [base+2] right_id, [base+3] right_const, [base+4] op
GENOME_SIZE = 20

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

# Period index mapping for matrix offset calculation
PERIODS = [10, 14, 20, 50, 100, 200]
PERIOD_TO_IDX = {p: i for i, p in enumerate(PERIODS)}


# ============================================================================
# INDICATOR PRE-COMPUTATION
# ============================================================================

def precompute_indicators(df):
    """
    Pre-compute ALL possible indicators as a numpy matrix.
    Called ONCE per dataset, shared across all genome evaluations.

    Returns:
        indicators: float64[NUM_INDICATORS, n_candles]
        close: float64[n_candles]
        high: float64[n_candles]
        low: float64[n_candles]
    """
    n = len(df)
    indicators = np.full((NUM_INDICATORS, n), np.nan, dtype=np.float64)

    close = df['close'].values.astype(np.float64)
    high = df['high'].values.astype(np.float64)
    low = df['low'].values.astype(np.float64)
    volume = df['volume'].values.astype(np.float64)

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
# GENOME ENCODING
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
            # Unknown indicator/period combo - treat as constant 0
            return IND_CONSTANT, 0.0
        return ind_id, 0.0

    if 'field' in item:
        field = item['field']
        field_map = {'close': IND_CLOSE, 'high': IND_HIGH, 'low': IND_LOW, 'volume': IND_VOLUME}
        return field_map.get(field, IND_CONSTANT), 0.0

    return IND_CONSTANT, 0.0


def encode_genome(genome):
    """
    Convert a genome dict to a fixed-size numpy array for Numba.

    Layout (20 floats):
    [0] sl_pct
    [1] tp_pct
    [2] size_pct        (% of balance per trade, 0.05-0.95)
    [3] max_positions   (1-3 simultaneous positions)
    [4] num_rules
    For each rule r (0-2), base = 5 + r*5:
    [base+0] left_id     (indicator index, or 99 for constant)
    [base+1] left_const  (value if left_id == 99, else 0)
    [base+2] right_id
    [base+3] right_const
    [base+4] op          (0 = >, 1 = <)
    """
    encoded = np.zeros(GENOME_SIZE, dtype=np.float64)
    encoded[0] = genome.get('params', {}).get('sl_pct', 0.05)
    encoded[1] = genome.get('params', {}).get('tp_pct', 0.10)
    encoded[2] = genome.get('params', {}).get('size_pct', 0.10)
    encoded[3] = genome.get('params', {}).get('max_positions', 1)

    rules = genome.get('entry_rules', [])
    encoded[4] = min(len(rules), MAX_RULES)

    for r_idx, rule in enumerate(rules[:MAX_RULES]):
        base = 5 + r_idx * 5

        # Left side
        left = rule.get('left', {})
        encoded[base], encoded[base + 1] = _resolve_item_id(left)

        # Right side
        right = rule.get('right', {})
        encoded[base + 2], encoded[base + 3] = _resolve_item_id(right)

        # Operator
        op = rule.get('op', '>')
        encoded[base + 4] = OP_GT if op == '>' else OP_LT

    return encoded


def decode_genome_rules(encoded):
    """Debug helper: decode encoded genome back to readable format."""
    inv_map = {v: k for k, v in INDICATOR_MAP.items()}
    inv_map[IND_CONSTANT] = ('CONST', 0)

    info = {
        'sl_pct': encoded[0],
        'tp_pct': encoded[1],
        'size_pct': encoded[2],
        'max_positions': int(encoded[3]),
        'num_rules': int(encoded[4]),
        'rules': []
    }

    for r in range(int(encoded[4])):
        base = 5 + r * 5
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
# NUMBA JIT COMPILED BACKTEST KERNEL
# ============================================================================

if HAS_NUMBA:
    @njit(cache=True)
    def _fast_backtest(close, high, low, indicators, genome_encoded, fee_rate):
        """
        JIT-compiled backtest loop for a single genome.

        Multi-position + percentage sizing + compounding:
        - Up to 3 simultaneous positions
        - Position size = balance * size_pct (compounding)
        - Trailing stop per position
        - Minimum $10 per trade to avoid dust

        Args:
            close: float64[n] - close prices
            high: float64[n] - high prices
            low: float64[n] - low prices
            indicators: float64[NUM_IND, n] - pre-computed indicator matrix
            genome_encoded: float64[20] - encoded genome
            fee_rate: float64 - trading fee rate (e.g. 0.004 for 0.4%)

        Returns:
            total_pnl: float64
            num_trades: int64
            wins: int64
            max_drawdown: float64
            sharpe_ratio: float64
        """
        n = len(close)
        sl_pct = genome_encoded[0]
        tp_pct = genome_encoded[1]
        size_pct = genome_encoded[2]
        max_positions = int(genome_encoded[3])
        num_rules = int(genome_encoded[4])

        # Clamp parameters
        if size_pct < 0.05:
            size_pct = 0.05
        if size_pct > 0.95:
            size_pct = 0.95
        if max_positions < 1:
            max_positions = 1
        if max_positions > 3:
            max_positions = 3

        balance = 10000.0

        # Fixed arrays for up to 3 positions
        pos_active = np.zeros(3, dtype=np.int64)      # 0 or 1
        pos_entry_price = np.zeros(3, dtype=np.float64)
        pos_size = np.zeros(3, dtype=np.float64)       # quantity (coins)
        pos_cost_basis = np.zeros(3, dtype=np.float64)  # USD spent
        pos_entry_fee = np.zeros(3, dtype=np.float64)
        pos_sl = np.zeros(3, dtype=np.float64)
        pos_tp = np.zeros(3, dtype=np.float64)
        pos_trail = np.zeros(3, dtype=np.float64)

        total_pnl = 0.0
        num_trades = 0
        wins = 0
        peak_balance = balance
        max_drawdown = 0.0
        sum_ret = 0.0
        sum_ret_sq = 0.0

        # Main loop - starts at 200 to ensure indicator warmup
        for i in range(200, n):
            price = close[i]
            candle_high = high[i]
            candle_low = low[i]

            # === EXIT LOOP: check all positions ===
            for s in range(3):
                if pos_active[s] == 0:
                    continue

                # Trailing stop: move SL up if price moved favorably
                new_sl = price - pos_trail[s]
                if new_sl > pos_sl[s]:
                    pos_sl[s] = new_sl

                # Check exit conditions
                sl_hit = candle_low <= pos_sl[s]
                tp_hit = candle_high >= pos_tp[s]

                if sl_hit or tp_hit:
                    if sl_hit:
                        exit_price = pos_sl[s]
                    else:
                        exit_price = pos_tp[s]

                    # Close position
                    exit_val_gross = pos_size[s] * exit_price
                    exit_fee = exit_val_gross * fee_rate
                    exit_val_net = exit_val_gross - exit_fee

                    balance += exit_val_net

                    trade_pnl = exit_val_net - (pos_cost_basis[s] + pos_entry_fee[s])
                    total_pnl += trade_pnl
                    num_trades += 1
                    if trade_pnl > 0.0:
                        wins += 1

                    # Track metrics
                    if pos_cost_basis[s] > 0.0:
                        ret = trade_pnl / pos_cost_basis[s]
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
            # Count open positions
            num_open = 0
            for s in range(3):
                num_open += pos_active[s]

            if num_open < max_positions:
                # Evaluate entry rules
                all_rules_pass = True

                if num_rules == 0:
                    all_rules_pass = False

                for r in range(num_rules):
                    base = 5 + r * 5
                    left_id = int(genome_encoded[base])
                    left_const = genome_encoded[base + 1]
                    right_id = int(genome_encoded[base + 2])
                    right_const = genome_encoded[base + 3]
                    op = int(genome_encoded[base + 4])

                    # Resolve left value
                    if left_id == 99:  # CONSTANT
                        val_a = left_const
                    elif left_id >= 0 and left_id < 28:
                        val_a = indicators[left_id, i]
                    else:
                        val_a = 0.0

                    # Resolve right value
                    if right_id == 99:  # CONSTANT
                        val_b = right_const
                    elif right_id >= 0 and right_id < 28:
                        val_b = indicators[right_id, i]
                    else:
                        val_b = 0.0

                    # Skip if NaN
                    if np.isnan(val_a) or np.isnan(val_b):
                        all_rules_pass = False
                        break

                    # Compare
                    if op == 0:  # >
                        if not (val_a > val_b):
                            all_rules_pass = False
                            break
                    else:  # <
                        if not (val_a < val_b):
                            all_rules_pass = False
                            break

                # Open position
                if all_rules_pass:
                    size_usd = balance * size_pct
                    if size_usd < 10.0:
                        size_usd = 0.0  # Skip dust trades

                    if size_usd >= 10.0:
                        entry_fee_val = size_usd * fee_rate
                        cost_deduct = size_usd + entry_fee_val

                        if balance >= cost_deduct:
                            # Find free slot
                            slot = -1
                            for s in range(3):
                                if pos_active[s] == 0:
                                    slot = s
                                    break

                            if slot >= 0:
                                balance -= cost_deduct
                                pos_active[slot] = 1
                                pos_entry_price[slot] = price
                                pos_size[slot] = size_usd / price
                                pos_cost_basis[slot] = size_usd
                                pos_entry_fee[slot] = entry_fee_val
                                pos_sl[slot] = price * (1.0 - sl_pct)
                                pos_tp[slot] = price * (1.0 + tp_pct)
                                pos_trail[slot] = (price - pos_sl[slot]) * 0.8

        # === CLOSE ALL OPEN POSITIONS AT END ===
        final_price = close[n - 1]
        for s in range(3):
            if pos_active[s] == 1:
                exit_val_gross = pos_size[s] * final_price
                exit_fee = exit_val_gross * fee_rate
                exit_val_net = exit_val_gross - exit_fee
                balance += exit_val_net
                trade_pnl = exit_val_net - (pos_cost_basis[s] + pos_entry_fee[s])
                total_pnl += trade_pnl
                num_trades += 1
                if trade_pnl > 0.0:
                    wins += 1

                if pos_cost_basis[s] > 0.0:
                    ret = trade_pnl / pos_cost_basis[s]
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

        return total_pnl, num_trades, wins, max_drawdown, sharpe_ratio


# ============================================================================
# PUBLIC API
# ============================================================================

def numba_evaluate_population(df, population, risk_level="LOW", progress_cb=None, cancel_event=None):
    """
    Evaluate an entire population of genomes using Numba JIT acceleration.

    Drop-in replacement for StrategyMiner._evaluate_local().

    Args:
        df: pandas DataFrame with OHLCV data
        population: list of genome dicts
        risk_level: unused (kept for API compatibility)
        progress_cb: callback(float) for progress updates
        cancel_event: threading.Event to cancel evaluation

    Returns:
        list of dicts: [{'metrics': {'Total PnL': X, 'Total Trades': Y, 'Win Rate %': Z}}, ...]
    """
    if not HAS_NUMBA:
        raise RuntimeError("Numba not installed. Cannot use JIT acceleration.")

    total = len(population)

    # Step 1: Pre-compute all indicators ONCE
    t0 = time.time()
    indicators, close, high, low = precompute_indicators(df)
    t_indicators = time.time() - t0

    # Step 2: Encode all genomes
    genomes_encoded = np.array([encode_genome(g) for g in population], dtype=np.float64)

    # Step 3: Fee rate (matches backtester.py logic)
    try:
        from config import Config
        fee_rate = getattr(Config, 'TRADING_FEE_MAKER', 0.4) / 100.0
    except ImportError:
        fee_rate = 0.004  # Default 0.4%

    # Step 4: Warmup JIT on first call (compile once, cached after)
    t_warmup = time.time()
    _fast_backtest(close, high, low, indicators, genomes_encoded[0], fee_rate)
    t_warmup = time.time() - t_warmup

    # Step 5: Run all backtests
    t_run = time.time()
    results = []

    for i in range(total):
        if cancel_event and cancel_event.is_set():
            return []

        total_pnl, num_trades, num_wins, max_dd, sharpe = _fast_backtest(
            close, high, low, indicators, genomes_encoded[i], fee_rate
        )

        win_rate = (num_wins / num_trades * 100.0) if num_trades > 0 else 0.0

        # Penalize strategies with no trades (matches original behavior)
        if num_trades == 0:
            total_pnl = -10000.0

        results.append({
            'metrics': {
                'Total PnL': round(total_pnl, 2),
                'Total Trades': num_trades,
                'Win Rate %': round(win_rate, 2),
                'Sharpe Ratio': round(sharpe, 4),
                'Max Drawdown': round(max_dd, 4)
            }
        })

        if progress_cb:
            progress_cb((i + 1) / total)

    t_run = time.time() - t_run

    # Log performance
    total_time = t_indicators + t_warmup + t_run
    print(f"   [Numba] Indicators: {t_indicators:.2f}s | JIT warmup: {t_warmup:.2f}s | "
          f"{total} backtests: {t_run:.2f}s | Total: {total_time:.2f}s")

    return results


def warmup_jit():
    """
    Pre-compile the JIT function with a tiny dataset.
    Call this once at worker startup to avoid compilation delay during first backtest.
    """
    if not HAS_NUMBA:
        return

    n = 300
    close = np.random.uniform(90, 110, n)
    high = close + np.random.uniform(0, 2, n)
    low = close - np.random.uniform(0, 2, n)
    indicators = np.random.uniform(0, 100, (NUM_INDICATORS, n))
    genome = np.zeros(GENOME_SIZE, dtype=np.float64)
    genome[0] = 0.02   # sl_pct
    genome[1] = 0.04   # tp_pct
    genome[2] = 0.10   # size_pct (10% of balance)
    genome[3] = 1.0    # max_positions
    genome[4] = 1      # 1 rule
    genome[5] = IND_RSI_14    # left: RSI_14
    genome[6] = 0.0
    genome[7] = IND_CONSTANT  # right: constant
    genome[8] = 30.0          # value: 30
    genome[9] = OP_LT         # RSI_14 < 30

    _fast_backtest(close, high, low, indicators, genome, 0.004)


# ============================================================================
# VALIDATION / TEST
# ============================================================================

def validate_against_original(df, genome, verbose=True):
    """
    Run the same genome through both the original and Numba backtester
    and compare results. Used for correctness verification.

    Returns:
        (match: bool, original_result: dict, numba_result: dict)
    """
    from backtester import Backtester
    from dynamic_strategy import DynamicStrategy

    # Original backtest
    t0 = time.time()
    bt = Backtester()
    _, trades = bt.run_backtest(df, risk_level="LOW", strategy_params=genome, strategy_cls=DynamicStrategy)
    t_original = time.time() - t0

    if len(trades) > 0:
        orig_pnl = round(trades['pnl'].sum(), 2)
        orig_trades = len(trades)
        orig_wins = len(trades[trades['pnl'] > 0])
        orig_winrate = round(orig_wins / orig_trades * 100, 2) if orig_trades > 0 else 0.0
    else:
        orig_pnl = -10000.0
        orig_trades = 0
        orig_wins = 0
        orig_winrate = 0.0

    # Numba backtest
    t0 = time.time()
    indicators, close, high, low = precompute_indicators(df)
    encoded = encode_genome(genome)

    try:
        from config import Config
        fee_rate = getattr(Config, 'TRADING_FEE_MAKER', 0.4) / 100.0
    except ImportError:
        fee_rate = 0.004

    numba_pnl, numba_trades, numba_wins, _, _ = _fast_backtest(close, high, low, indicators, encoded, fee_rate)
    t_numba = time.time() - t0

    numba_pnl = round(numba_pnl, 2)
    numba_winrate = round(numba_wins / numba_trades * 100, 2) if numba_trades > 0 else 0.0

    if numba_trades == 0:
        numba_pnl = -10000.0

    # Compare
    pnl_match = abs(orig_pnl - numba_pnl) < 1.0  # Allow $1 tolerance for rounding
    trades_match = orig_trades == numba_trades

    if verbose:
        print(f"\n{'='*60}")
        print(f"VALIDATION: Original vs Numba Backtester")
        print(f"{'='*60}")
        print(f"Genome: {decode_genome_rules(encoded)}")
        print(f"")
        print(f"{'Metric':<20} {'Original':>12} {'Numba':>12} {'Match':>8}")
        print(f"{'-'*52}")
        print(f"{'PnL ($)':<20} {orig_pnl:>12.2f} {numba_pnl:>12.2f} {'OK' if pnl_match else 'DIFF':>8}")
        print(f"{'Trades':<20} {orig_trades:>12} {numba_trades:>12} {'OK' if trades_match else 'DIFF':>8}")
        print(f"{'Wins':<20} {orig_wins:>12} {numba_wins:>12} {'OK' if orig_wins == numba_wins else 'DIFF':>8}")
        print(f"{'Win Rate %':<20} {orig_winrate:>12.2f} {numba_winrate:>12.2f}")
        print(f"")
        print(f"{'Time (s)':<20} {t_original:>12.2f} {t_numba:>12.2f}")
        if t_numba > 0:
            print(f"{'Speedup':<20} {'':>12} {t_original/t_numba:>11.1f}x")
        print(f"{'='*60}")

    original_result = {'pnl': orig_pnl, 'trades': orig_trades, 'wins': orig_wins, 'winrate': orig_winrate, 'time': t_original}
    numba_result = {'pnl': numba_pnl, 'trades': numba_trades, 'wins': numba_wins, 'winrate': numba_winrate, 'time': t_numba}

    return pnl_match and trades_match, original_result, numba_result


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("NUMBA BACKTESTER - Standalone Test")
    print("="*60)

    # Check Numba
    if not HAS_NUMBA:
        print("ERROR: Numba not installed. Run: pip install numba")
        exit(1)

    print(f"Numba available: {HAS_NUMBA}")

    # Load data
    data_path = "data/BTC-USD_FIVE_MINUTE.csv"
    if not os.path.exists(data_path):
        data_path = "data/BTC-USD_ONE_MINUTE.csv"

    if not os.path.exists(data_path):
        print(f"ERROR: No data file found")
        exit(1)

    print(f"Loading data: {data_path}")
    df = pd.read_csv(data_path).tail(100000).copy()
    df.reset_index(drop=True, inplace=True)
    print(f"Loaded {len(df):,} candles")

    # Test genome
    test_genome = {
        "entry_rules": [
            {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30}},
            {"left": {"field": "close"}, "op": ">", "right": {"indicator": "SMA", "period": 50}}
        ],
        "params": {"sl_pct": 0.03, "tp_pct": 0.06}
    }

    print(f"\nTest genome: RSI_14 < 30 AND close > SMA_50, SL=3%, TP=6%")

    # JIT Warmup
    print("\nWarming up JIT compiler...")
    warmup_jit()

    # Validate against original
    print("\nRunning validation...")
    match, orig, numba = validate_against_original(df, test_genome)

    if match:
        print("\nVALIDATION PASSED - Results match!")
    else:
        print("\nWARNING: Results differ (small differences may be due to trailing stop rounding)")

    # Benchmark: evaluate a population of 20 genomes
    print("\n" + "="*60)
    print("BENCHMARK: 20-genome population evaluation")
    print("="*60)

    from strategy_miner import StrategyMiner
    miner = StrategyMiner(df, population_size=20, generations=1, risk_level="LOW", force_local=True)
    population = [miner.generate_random_genome() for _ in range(20)]

    # Numba timing
    t0 = time.time()
    numba_results = numba_evaluate_population(df, population, risk_level="LOW")
    t_numba = time.time() - t0

    print(f"\nNumba: {t_numba:.2f}s for 20 genomes ({t_numba/20:.3f}s per genome)")

    # Show results
    print(f"\nResults summary:")
    pnls = [r['metrics']['Total PnL'] for r in numba_results]
    trades_list = [r['metrics']['Total Trades'] for r in numba_results]
    print(f"  PnL range: ${min(pnls):,.2f} to ${max(pnls):,.2f}")
    print(f"  Trades range: {min(trades_list)} to {max(trades_list)}")
    print(f"  Genomes with trades: {sum(1 for t in trades_list if t > 0)}/20")

    print("\nDone!")
