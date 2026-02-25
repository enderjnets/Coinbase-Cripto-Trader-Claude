import pandas as pd
import numpy as np

class DynamicStrategy:
    """
    Interpreter for Genetically Evolved Strategies.
    Compatible with Backtester interface.
    
    INDICADORES SOPORTADOS:
    - Básicos: RSI, SMA, EMA, VOLSMA
    - MACD: MACD, MACD_Signal, MACD_Hist
    - ATR: ATR, ATR_Pct
    - Bollinger: BB_Upper, BB_Lower, BB_Width, BB_Position
    - ADX: ADX, DI_Plus, DI_Minus
    - Stochastic: STOCH_K, STOCH_D
    - Ichimoku: ICHIMOKU_Conv, ICHIMOKU_Base, ICHIMOKU_SpanA, ICHIMOKU_SpanB
    - Volume: OBV, VWAP
    - Momentum: ROC, CCI, WILLIAMS_R
    """
    def __init__(self, genome=None):
        self.genome = genome if genome else {}
        self.params = {}
        self.indicators_calculated = False
        
        if not self.genome:
            self.genome = {
                "entry_rules": [],
                "exit_rules": [],
                "params": {"sl": 0.02, "tp": 0.04}
            }

    def set_genome(self, genome):
        self.genome = genome
        if 'params' in genome:
            self.params.update(genome['params'])

    def prepare_data(self, df):
        """Pre-calculate all indicators required by the genome."""
        df = df.copy()
        
        rules = self.genome.get("entry_rules", []) + self.genome.get("exit_rules", [])
        required_indicators = set()
        
        for rule in rules:
            if isinstance(rule.get('left'), dict):
                self._add_requirement(rule['left'], required_indicators)
            if isinstance(rule.get('right'), dict):
                self._add_requirement(rule['right'], required_indicators)
        
        for ind in required_indicators:
            self._calculate_indicator(df, ind)
            
        return df

    def _add_requirement(self, item, req_set):
        if 'indicator' in item:
            sig = f"{item['indicator']}_{item.get('period', 14)}"
            req_set.add(sig)

    def _calculate_indicator(self, df, signature):
        """Computes indicator and adds column to df"""
        parts = signature.split('_')
        name = parts[0]
        period = int(parts[1]) if len(parts) > 1 else 14
        
        col_name = signature
        if col_name in df.columns:
            return

        # === INDICADORES BÁSICOS ===
        if name == "RSI":
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            df[col_name] = 100 - (100 / (1 + rs))
            df[col_name] = df[col_name].fillna(50)
            
        elif name == "SMA":
            df[col_name] = df['close'].rolling(window=period).mean()
            
        elif name == "EMA":
            df[col_name] = df['close'].ewm(span=period, adjust=False).mean()
            
        elif name == "VOLSMA":
            df[col_name] = df['volume'].rolling(window=period).mean()

        # === MACD ===
        elif name == "MACD":
            exp12 = df['close'].ewm(span=12, adjust=False).mean()
            exp26 = df['close'].ewm(span=26, adjust=False).mean()
            df[col_name] = exp12 - exp26
            
        elif name == "MACD_Signal":
            exp12 = df['close'].ewm(span=12, adjust=False).mean()
            exp26 = df['close'].ewm(span=26, adjust=False).mean()
            macd = exp12 - exp26
            df[col_name] = macd.ewm(span=9, adjust=False).mean()
            
        elif name == "MACD_Hist":
            exp12 = df['close'].ewm(span=12, adjust=False).mean()
            exp26 = df['close'].ewm(span=26, adjust=False).mean()
            macd = exp12 - exp26
            signal = macd.ewm(span=9, adjust=False).mean()
            df[col_name] = macd - signal

        # === ATR ===
        elif name == "ATR":
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df[col_name] = tr.rolling(window=period).mean()
            
        elif name == "ATR_Pct":
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            df[col_name] = (atr / close) * 100

        # === BOLLINGER BANDS ===
        elif name == "BB_Upper":
            sma = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            df[col_name] = sma + (std * 2)
            
        elif name == "BB_Lower":
            sma = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            df[col_name] = sma - (std * 2)
            
        elif name == "BB_Width":
            sma = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            upper = sma + (std * 2)
            lower = sma - (std * 2)
            df[col_name] = (upper - lower) / sma * 100
            
        elif name == "BB_Position":
            sma = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            upper = sma + (std * 2)
            lower = sma - (std * 2)
            df[col_name] = (df['close'] - lower) / (upper - lower) * 100

        # === ADX ===
        elif name == "ADX":
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            plus_dm = high.diff()
            minus_dm = -low.diff()
            
            plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
            minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
            
            atr = tr.rolling(window=period).mean()
            plus_di = (plus_dm / atr) * 100
            minus_di = (minus_dm / atr) * 100
            
            dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
            df[col_name] = dx.rolling(window=period).mean()
            
        elif name == "DI_Plus":
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            plus_dm = high.diff()
            minus_dm = -low.diff()
            
            plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
            minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
            
            atr = tr.rolling(window=period).mean()
            df[col_name] = (plus_dm / atr) * 100
            
        elif name == "DI_Minus":
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            plus_dm = high.diff()
            minus_dm = -low.diff()
            
            plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
            minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
            
            atr = tr.rolling(window=period).mean()
            df[col_name] = (minus_dm / atr) * 100

        # === STOCHASTIC ===
        elif name == "STOCH_K":
            low_min = df['low'].rolling(window=period).min()
            high_max = df['high'].rolling(window=period).max()
            df[col_name] = ((df['close'] - low_min) / (high_max - low_min)) * 100
            
        elif name == "STOCH_D":
            low_min = df['low'].rolling(window=period).min()
            high_max = df['high'].rolling(window=period).max()
            stoch_k = ((df['close'] - low_min) / (high_max - low_min)) * 100
            df[col_name] = stoch_k.rolling(window=3).mean()

        # === ICHIMOKU ===
        elif name == "ICHIMOKU_Conv":
            high_9 = df['high'].rolling(window=9).max()
            low_9 = df['low'].rolling(window=9).min()
            df[col_name] = (high_9 + low_9) / 2
            
        elif name == "ICHIMOKU_Base":
            high_26 = df['high'].rolling(window=26).max()
            low_26 = df['low'].rolling(window=26).min()
            df[col_name] = (high_26 + low_26) / 2
            
        elif name == "ICHIMOKU_SpanA":
            conv = df['close'].rolling(window=9).max() + df['close'].rolling(window=9).min()
            base = df['close'].rolling(window=26).max() + df['close'].rolling(window=26).min()
            df[col_name] = (conv + base) / 2
            
        elif name == "ICHIMOKU_SpanB":
            high_52 = df['high'].rolling(window=52).max()
            low_52 = df['low'].rolling(window=52).min()
            df[col_name] = (high_52 + low_52) / 2

        # === VOLUME INDICATORS ===
        elif name == "OBV":
            df[col_name] = (np.sign(df['close'].diff()) * df['volume']).cumsum()
            
        elif name == "VWAP":
            df['pv'] = df['close'] * df['volume']
            df['v'] = df['volume']
            df[col_name] = df['pv'].cumsum() / df['v'].cumsum()
            df.drop(['pv', 'v'], axis=1, inplace=True)

        # === MOMENTUM INDICATORS ===
        elif name == "ROC":
            df[col_name] = ((df['close'] - df['close'].shift(period)) / df['close'].shift(period)) * 100
            
        elif name == "CCI":
            tp = (df['high'] + df['low'] + df['close']) / 3
            sma_tp = tp.rolling(window=period).mean()
            mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
            df[col_name] = (tp - sma_tp) / (0.015 * mad)
            
        elif name == "WILLIAMS_R":
            high_n = df['high'].rolling(window=period).max()
            low_n = df['low'].rolling(window=period).min()
            df[col_name] = -100 * (high_n - df['close']) / (high_n - low_n)

    def get_signal(self, window, current_index, risk_level=None):
        """Evaluate rules at specific index."""
        row = window.iloc[-1]
        
        entry_signal = True
        entry_rules = self.genome.get("entry_rules", [])

        if not entry_rules:
            entry_signal = False

        for rule in entry_rules:
            val_a = self._get_value(row, rule.get('left'))
            val_b = self._get_value(row, rule.get('right'))
            op = rule.get('op', '>')

            if not self._compare(val_a, val_b, op):
                entry_signal = False
                break
        
        signal = None
        if entry_signal:
            signal = "BUY"
            
        # Risk Management desde genome params
        sl_pct = self.genome.get("params", {}).get("sl_pct", 0.05)
        tp_pct = self.genome.get("params", {}).get("tp_pct", 0.10)
        
        # Trailing stop
        trailing_stop = self.genome.get("params", {}).get("trailing_stop_pct", 0)
        # Breakeven
        breakeven_after = self.genome.get("params", {}).get("breakeven_after", 0)
        
        price = row['close']
        
        return {
            "signal": signal,
            "sl": price * (1 - sl_pct),
            "tp": price * (1 + tp_pct),
            "trailing_stop": trailing_stop,
            "breakeven_after": breakeven_after,
            "reason": "GENETIC_ENTRY"
        }

    def _get_value(self, row, item):
        """Resolve value from row (indicator) or constant."""
        if not isinstance(item, dict):
            return float(item)
        
        if 'value' in item:
            return float(item['value'])
            
        if 'indicator' in item:
            sig = f"{item['indicator']}_{item.get('period', 14)}"
            return row.get(sig, 0)
            
        if 'field' in item:
            return row.get(item['field'], 0)
            
        return 0

    def _compare(self, a, b, op):
        if op == "<": return a < b
        if op == ">": return a > b
        if op == "<=": return a <= b
        if op == ">=": return a >= b
        if op == "==": return a == b
        return False
