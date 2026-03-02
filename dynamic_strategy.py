import pandas as pd
import numpy as np

class DynamicStrategy:
    """
    Interpreter for Genetically Evolved Strategies.
    Accepts a 'genome' (configuration dict) to apply trading rules.
    Compatible with Backtester interface.
    """
    def __init__(self, genome=None):
        self.genome = genome if genome else {}
        self.params = {} # Backtester compat
        self.indicators_calculated = False
        
        # Default Genome Structure if None (Empty)
        if not self.genome:
            self.genome = {
                "entry_rules": [],
                "exit_rules": [], # Logic exits (indicators)
                "params": {"sl": 0.02, "tp": 0.04} 
            }

    def set_genome(self, genome):
        self.genome = genome
        # Extract fixed params from genome to self.params for backtester to see
        if 'params' in genome:
            self.params.update(genome['params'])

    def prepare_data(self, df):
        """
        Pre-calculate all indicators required by the genome.
        Vectorized operation for speed.
        """
        df = df.copy()
        
        # Parse Rules to find required indicators
        rules = self.genome.get("entry_rules", []) + self.genome.get("exit_rules", [])
        
        required_indicators = set()
        
        for rule in rules:
            # Rule format: {"type": "A < B", "left": "RSI", "l_params": {14}, ...}
            # Simplified for now: String based or structured
            # We assume structured: 
            # { "left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30} }
            
            # Extract Left Side
            if isinstance(rule.get('left'), dict):
                self._add_requirement(rule['left'], required_indicators)
                
            # Extract Right Side
            if isinstance(rule.get('right'), dict):
                self._add_requirement(rule['right'], required_indicators)

        # Calculate Indicators
        for ind in required_indicators:
            self._calculate_indicator(df, ind)
            
        return df

    def _add_requirement(self, item, req_set):
        if 'indicator' in item:
            # Create a unique signature string for the key
            # e.g. "RSI_14", "SMA_200"
            sig = f"{item['indicator']}_{item.get('period', 14)}"
            req_set.add(sig)

    def _calculate_indicator(self, df, signature):
        """Computes indicator and adds column to df"""
        parts = signature.split('_')
        name = parts[0]
        period = int(parts[1]) if len(parts) > 1 else 14
        
        col_name = signature
        if col_name in df.columns:
            return # Already done

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
            
        elif name == "MACD":
            # Hardcoded standard 12,26,9 for simplicity or encoded in signature?
            # For Miner, let's keep MACD simple or parameterized later.
            # Let's support MACD_Line and MACD_Signal
            pass # TODO

    def get_signal(self, window, current_index, risk_level=None):
        """
        Evaluate rules at specific index.
        """
        # "window" is strict slice of df, last row is 'current'
        # But we already pre-calculated indicators in prepare_data on the global df?
        # NO. Backtester splits df first, then calls prepare_data?
        # Re-check Backtester:
        # 1. prepare_data(df) -> df with indicators
        # 2. Iterates and passes 'window' (slice of prepared df)
        # So window IS prepared.

        row = window.iloc[-1]

        # 1. ENTRY LOGIC
        entry_signal = True
        entry_rules = self.genome.get("entry_rules", [])

        # DEBUG: Log first time
        if not hasattr(self, '_debug_logged'):
            print(f"🔍 GENOME DEBUG: {len(entry_rules)} entry rules")
            for i, rule in enumerate(entry_rules):
                print(f"   Rule {i+1}: {rule}")
            self._debug_logged = True

        if not entry_rules:
            entry_signal = False

        for rule in entry_rules:
            # { "left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30} }
            val_a = self._get_value(row, rule.get('left'))
            val_b = self._get_value(row, rule.get('right'))
            op = rule.get('op', '>')

            if not self._compare(val_a, val_b, op):
                entry_signal = False
                break
        
        signal = None
        if entry_signal:
            direction = self.genome.get("params", {}).get("direction", "LONG")
            if direction == "SHORT":
                signal = "SHORT"
            else:
                signal = "BUY"

        # 2. EXIT LOGIC (Optional, Backtester handles TP/SL usually, but we can force exit)
        # ...

        # 3. PARAMS for SL/TP
        # Copied from genome params
        sl_pct = self.genome.get("params", {}).get("sl_pct", 0.05)
        tp_pct = self.genome.get("params", {}).get("tp_pct", 0.10)
        direction = self.genome.get("params", {}).get("direction", "LONG")

        price = row['close']

        if direction == "SHORT":
            sl = price * (1 + sl_pct)   # SL above for shorts
            tp = price * (1 - tp_pct)   # TP below for shorts
        else:
            sl = price * (1 - sl_pct)   # SL below for longs
            tp = price * (1 + tp_pct)   # TP above for longs

        return {
            "signal": signal,
            "sl": sl,
            "tp": tp,
            "reason": "GENETIC_ENTRY"
        }

    def _get_value(self, row, item):
        """Resolve value from row (indicator) or constant."""
        if not isinstance(item, dict):
            return float(item) # Constant
        
        if 'value' in item:
            return float(item['value'])
            
        if 'indicator' in item:
            sig = f"{item['indicator']}_{item.get('period', 14)}"
            return row.get(sig, 0)
            
        if 'field' in item:
            # Price, Volume
            return row.get(item['field'], 0)
            
        return 0

    def _compare(self, a, b, op):
        if op == "<": return a < b
        if op == ">": return a > b
        if op == "<=": return a <= b
        if op == ">=": return a >= b
        if op == "==": return a == b
        return False
