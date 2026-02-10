import pandas as pd
import numpy as np
import time
from datetime import datetime

class BitcoinSpotStrategy:
    """
    Bitcoin Spot Pro Strategy.
    Optimized for Coinbase Advanced Fees (Maker 0.4%, Taker 0.6%).
    
    Modes:
    1. Swing Reversion (H1/H4): Bollinger Bands + RSI Divergence.
    2. Geometric Grid (Passive): Fee-aware grid trading for lateral markets.
    """
    
    def check_trend(self, df):
        """
        Compatibility method for TradingBot.
        Returns 'UP', 'DOWN', or 'NEUTRAL'.
        For this strategy, we might want to check SMA20 slope or just return NEUTRAL if we trade ranges.
        """
        if df is None or len(df) < 20: return "NEUTRAL"
        
        # Simple Logic: Price > SMA50 ?
        # But for range trading (this strategy), we actually prefer NEUTRAL.
        # Let's calculate simple trend.
        current = df['close'].iloc[-1]
        sma20 = df['close'].rolling(window=20).mean().iloc[-1]
        
        if current > sma20 * 1.01: return "UP"
        if current < sma20 * 0.99: return "DOWN"
        return "NEUTRAL"
        
    def prepare_data(self, df):
        """
        Vectorized Indicator Calculation.
        Calculates all indicators for the entire DataFrame at once.
        """
        return self.calculate_indicators(df)

    def detect_signal(self, df_5m, trend, risk_level):
        """
        Compatibility wrapper for TradingBot loop.
        Arg 'trend' comes from check_trend.
        Returns: (Signal, Reason)
        """
        # Ensure indicators are present
        # In Vectorized Backtest, df_5m is a SLICE of the full DF which already has indicators.
        # But for Live Bot, validation is needed.
        if 'BB_LOWER' not in df_5m.columns:
             df = self.calculate_indicators(df_5m)
        else:
             df = df_5m
        
        # Use Swing Setup logic
        setup = self.analyze_swing_setup(df, risk_level)
        
        if setup == 'BUY_SETUP':
            return 'BUY', 'Range Reversion Buy (RSI < 30 + Lower BB)'
        elif setup == 'TAKE_PROFIT_1' or setup == 'TAKE_PROFIT_2':
             return 'SELL', f'Take Profit ({setup})'
             
        return None, ''

    def get_signal(self, df, index, risk_level="LOW"):
        """
        Standard Backtester Interface.
        df: DataFrame with at least 'close' and required indicators (calculated inside if needed)
        index: Current candle index
        """
        # Slice window (e.g. last 100 for safety)
        start = max(0, index - 100)
        window = df.iloc[start:index+1].copy()
        
        # Check Trend (provided by Backtester or calculated)
        trend = "NEUTRAL"
        if 'trend' in window.columns:
            trend = window.iloc[-1]['trend']
            
        # Call internal logic
        # Note: detect_signal expects a DataFrame, and returns (Signal, Reason)
        signal, reason = self.detect_signal(window, trend, risk_level)
        
        # Calculate SL/TP (Simple defaults for Backtester if not provided by logic)
        sl = None
        tp = None
        
        if signal == "BUY":
            price = window.iloc[-1]['close']
            
            # Use configurable multipliers from params
            sl_mult = self.params.get('sl_multiplier', 1.5)
            tp_mult = self.params.get('tp_multiplier', 3.0)
            
            # Calculate ATR if available, else use % based
            if 'ATR' in window.columns and not pd.isna(window.iloc[-1]['ATR']):
                atr = window.iloc[-1]['ATR']
                sl = price - (atr * sl_mult)
                tp = price + (atr * tp_mult)
            elif 'BB_LOWER' in window.columns:
                # Fallback: use BB as reference
                bb_width = window.iloc[-1]['BB_UPPER'] - window.iloc[-1]['BB_LOWER']
                sl = price - (bb_width * sl_mult * 0.5)
                tp = price + (bb_width * tp_mult * 0.5)
            else:
                # Simple percentage fallback
                sl = price * (1 - 0.02 * sl_mult)
                tp = price * (1 + 0.02 * tp_mult)
            
        return {
            'signal': signal,
            'reason': reason,
            'sl': sl,
            'tp': tp
        }

    
    def __init__(self, broker_client):
        self.broker = broker_client
        self.position = None # {entry_price, size, stop_loss, target}
        
        # --- Configurable Parameters (for Optimization) ---
        self.params = {
            'rsi_period': 14,
            'rsi_oversold': 30,   # Buy when RSI < this
            'rsi_overbought': 70, # Sell when RSI > this
            'sl_multiplier': 1.5, # SL = Entry - (ATR * multiplier)
            'tp_multiplier': 3.0, # TP = Entry + (ATR * multiplier)
            'resistance_period': 20,
        }
        
        # --- Constants & Risk ---
        self.MAKER_FEE = 0.0040 # 0.40%
        self.TAKER_FEE = 0.0060 # 0.60%
        self.MIN_PROFIT_NET = 0.005 # 0.5% Net Profit desired per trade
        
        # Calculated threshold for Grid Spacing
        # Round trip cost = Maker Buy + Maker Sell = ~0.8%
        # Spacing must be > 0.8% + Min Profit
        self.MIN_GRID_SPACING = self.MAKER_FEE * 2 + 0.002 # At least 1.0%
        
        # Target Pairs for specific execution mode
        # This tells the bot to ONLY trade this, skipping the scanner.
        self.target_pairs = ["BTC-USD"] # Default to BTC-USD

        
    def calculate_indicators(self, df):
        """
        Adds BB(20, 2), RSI(14), MACD to DataFrame.
        """
        if df is None or df.empty: return df
        
        # RSI 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands (20, 2)
        df['SMA20'] = df['close'].rolling(window=20).mean()
        df['STD20'] = df['close'].rolling(window=20).std()
        df['BB_UPPER'] = df['SMA20'] + (df['STD20'] * 2)
        df['BB_LOWER'] = df['SMA20'] - (df['STD20'] * 2)
        
        # MACD (12, 26, 9)
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # ATR (14) - for SL/TP calculation
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = high_low.combine(high_close, max).combine(low_close, max)
        df['ATR'] = tr.rolling(window=14).mean()
        
        return df

    def analyze_swing_setup(self, df_h1, risk_level="MEDIUM"):
        """
        Mode 1: Swing Reversion Analysis.
        Returns: 'BUY', 'SELL', or None
        """
        if df_h1 is None or len(df_h1) < 20: return None
        
        last = df_h1.iloc[-1]
        prev = df_h1.iloc[-2]
        
        # Get RSI threshold from params (configurable via optimization)
        rsi_threshold = self.params.get('rsi_oversold', 30)
        require_volume = True
        
        # Adjust by risk level
        if risk_level == "LOW": # Strict
            rsi_threshold = max(20, rsi_threshold - 5)
            require_volume = True
        elif risk_level == "HIGH": # Aggressive
            rsi_threshold = min(45, rsi_threshold + 10)
            require_volume = False
            
        # Logic: Price touches Lower BB AND RSI < Threshold
        # Buy Signal
        if last['close'] <= last['BB_LOWER'] or last['low'] <= last['BB_LOWER']:
            if last['RSI'] < rsi_threshold:
                 return 'BUY_SETUP'
                 
        # Sell Signal (Mean Reversion to SMA20 or Upper Band)
        if self.position:
            if last['close'] >= last['SMA20']:
                return 'TAKE_PROFIT_1'
            if last['close'] >= last['BB_UPPER']:
                return 'TAKE_PROFIT_2'
                
        return None

    def calculate_position_size(self, capital, risk_percent, entry_price, stop_loss_price):
        """
        Math: (Total Capital * Risk%) / (Entry - Stop) * Entry
        """
        if entry_price <= stop_loss_price: return 0.0
        
        risk_amount = capital * (risk_percent / 100.0)
        price_diff = entry_price - stop_loss_price
        
        # Shares to buy = Risk / Diff
        shares = risk_amount / price_diff
        
        # Total Position Size in USD
        position_size_usd = shares * entry_price
        
        # Capped at Total Capital
        return min(position_size_usd, capital)

    def generate_grid_levels(self, current_price, lower_range, upper_range, grids=10):
        """
        Generates Geometric Grid levels (Equal % spacing).
        Ensures spacing covers fees.
        """
        # Geometric ratio
        # upper = lower * r^n
        # r = (upper/lower)^(1/n)
        
        if lower_range >= upper_range: return []
        
        ratio = (upper_range / lower_range) ** (1/grids)
        percentage_gap = (ratio - 1) * 100
        
        if percentage_gap < (self.MIN_GRID_SPACING * 100):
            print(f"⚠️ Warning: Grid spacing {percentage_gap:.2f}% is too tight for fees (~0.8%). Recommended: >1.2%")
            
        levels = []
        price = lower_range
        for _ in range(grids + 1):
            levels.append(price)
            price *= ratio
            
        return levels, percentage_gap

