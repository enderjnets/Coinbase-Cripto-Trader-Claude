import pandas as pd
from config import Config

class Strategy:
    def __init__(self):
        pass

    def calculate_support_resistance(self, df, period=50):
        """
        Calculates dynamic S/R based on rolling Max/Min.
        """
        if df is None or df.empty:
            return None, None
            
        # Resistance = Max High of last N periods
        # Support = Min Low of last N periods
        # Shift 1 to avoid look-ahead bias (current candle shouldn't set the level for itself)
        df['resistance'] = df['high'].rolling(window=period).max().shift(1)
        df['support'] = df['low'].rolling(window=period).min().shift(1)
        
        return df

    def check_trend(self, df_1h):
        """
        Determines overall trend from 1H timeframe.
        Simple logic: Close > EMA 50 = Uptrend, else Downtrend.
        """
        if df_1h is None or len(df_1h) < 55:
            return "NEUTRAL"
        
        # Calculate EMA 50
        ema50 = df_1h['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        current_price = df_1h['close'].iloc[-1]
        
        if current_price > ema50:
            return "UP"
        elif current_price < ema50:
            return "DOWN"
        
        return "NEUTRAL"

    def detect_signal(self, df_5m, trend_direction, risk_level="LOW"):
        """
        Checks for Breakout with variable strictness based on Risk Level.
        Returns: (Signal, Reason)
            Signal: 'BUY', 'SELL', or None
            Reason: String explaining the result
        """
        if df_5m is None or len(df_5m) < 5:
            return None, "Insufficient data"
            
        # Get last 3 candles
        c1 = df_5m.iloc[-3] # Breakout Candidate
        c2 = df_5m.iloc[-2] # Confirmation 1
        c3 = df_5m.iloc[-1] # Confirmation 2 (Just closed)
        
        # Check Long
        if trend_direction == "UP":
            res_at_c1 = c1['resistance']
            
            if pd.isna(res_at_c1):
                return None, "Resistance invalid (NaN)"
            
            # 1. Breakout Check
            if c1['close'] > res_at_c1:
                # HIGH RISK: Breakout Only (Immediate Entry)
                if risk_level == "HIGH":
                     return "BUY", "HIGH RISK: Breakout Verified (No confirmation needed)"
                
                # 2. Confirmations Checks
                is_c2_bullish = c2['close'] > c2['open']
                is_c3_bullish = c3['close'] > c3['open']
                
                # MEDIUM RISK: Breakout + 1 Candle Confirmation
                if risk_level == "MEDIUM":
                    if is_c2_bullish and c2['close'] > res_at_c1:
                        return "BUY", "MEDIUM RISK: Breakout + 1 Confirmation Verified"
                    else:
                        return None, f"Breakout detected but C2 confirmation failed (C2_Bull:{is_c2_bullish})"

                # LOW RISK (Standard): Breakout + 2 Candle Confirmations
                # Validation: Close above breakout level 
                valid_level = c2['close'] > res_at_c1 and c3['close'] > res_at_c1
                
                if is_c2_bullish and is_c3_bullish and valid_level:
                    return "BUY", "LOW RISK: Breakout + 2 Confirmations Verified"
                else:
                    return None, f"Breakout detected but confirmatons failed (C2_Bull:{is_c2_bullish}, C3_Bull:{is_c3_bullish})"
            else:
                 return None, f"No Breakout (Close {c1['close']:.4f} <= Res {res_at_c1:.4f})"

        # Check Short
        elif trend_direction == "DOWN":
            sup_at_c1 = c1['support']
            if pd.isna(sup_at_c1):
                return None, "Support invalid (NaN)"
                
            if c1['close'] < sup_at_c1:
                 # HIGH RISK: Breakout Only
                if risk_level == "HIGH":
                     return "SELL", "HIGH RISK: Breakout Verified (No confirmation needed)"

                is_c2_bearish = c2['close'] < c2['open']
                is_c3_bearish = c3['close'] < c3['open']
                
                # MEDIUM RISK: Breakout + 1 Candle Confirmation
                if risk_level == "MEDIUM":
                    if is_c2_bearish and c2['close'] < sup_at_c1:
                        return "SELL", "MEDIUM RISK: Breakout + 1 Confirmation Verified"
                    else:
                        return None, f"Breakout detected but C2 confirmation failed (C2_Bear:{is_c2_bearish})"

                # LOW RISK (Standard)
                valid_level = c2['close'] < sup_at_c1 and c3['close'] < sup_at_c1
                
                if is_c2_bearish and is_c3_bearish and valid_level:
                    return "SELL", "LOW RISK: Breakout + 2 Confirmations Verified"
                else:
                    return None, f"Breakout detected but confirmatons failed (C2_Bear:{is_c2_bearish}, C3_Bear:{is_c3_bearish})"
            else:
                return None, f"No Breakout (Close {c1['close']:.4f} >= Sup {sup_at_c1:.4f})"
                    
        return None, f"Trend is {trend_direction}, awaiting setup"
