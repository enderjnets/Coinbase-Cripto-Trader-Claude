#!/usr/bin/env python3
"""
Backtester CORREGIDO - USA TODOS LOS DATOS
"""
import pandas as pd
import numpy as np
from datetime import datetime

TRADING_FEE = 0.000

def run_backtest(df, genome, initial_balance=10000):
    """Backtest completo"""
    if df is None or len(df) < 100:
        return {"Total PnL": 0, "Total Trades": 0, "Win Rate %": 0}
    
    # Limpiar datos
    df = df.dropna().reset_index(drop=True)
    sl_pct = genome.get("params", {}).get("sl_pct", 0.02)
    tp_pct = genome.get("params", {}).get("tp_pct", 0.04)
    rules = genome.get("entry_rules", [])
    balance = 10000
    position = None
    trades = []
    
    for i in range(len(df)):
        price = df.iloc[i]["close"]
        high = df.iloc[i]["high"]
        low = df.iloc[i]["low"]
        
        # SL/TP
        if position:
            if position["tipo"] == "long":
                if low <= position["sl"]:
                    exit_price = position["sl"]
                    pnl = (exit_price - position["entry"]) * position["size"]
                    trades.append({"pnl": pnl})
                    balance += exit_price * position["size"] * (1 - TRADING_FEE)
                    position = None
                elif high >= position["tp"]:
                    exit_price = position["tp"]
                    pnl = (exit_price - position["entry"]) * position["size"]
                    trades.append({"pnl": pnl})
                    balance += exit_price * position["size"] * (1 - TRADING_FEE)
                    position = None
            else:  # short
                if high >= position["sl"]:
                    pnl = (position["entry"] - position["sl"]) * position["size"]
                    trades.append({"pnl": pnl})
                    balance += position["size"] * position["entry"]
                    position = None
                elif low <= position["tp"]:
                    pnl = (position["entry"] - position["tp"]) * position["size"]
                    trades.append({"pnl": pnl})
                    balance += position["size"] * position["tp"])
        
        # Nueva posición
        if not position:
            score = score_rules(df.iloc[:i+1], rules)
            if score >= 1:
                size = balance * 0.1
                position = {"tipo": "long", "entry": price, "sl": price * (1 - sl_pct), "tp": price * (1 + tp_pct), "size": size / price}
                balance -= size
    
    if trades:
        df_t = pd.DataFrame(trades)
        total_pnl = df_t["pnl"].sum()
        wins = (df_t["pnl"] > 0).sum()
        win_rate = wins / len(df_t) * 100
    else:
        total_pnl = 0
        win_rate = 0
        df_t = pd.DataFrame()
    
    return {
        "Total PnL": total_pnl,
        "Total Trades": len(trades),
        "Win Rate %": win_rate
    }


def score_rules(df_slice, rules):
    """Score del genome"""
    if not rules:
        return 0
    current = df_slice.iloc[-1]
    score = 0
    for r in rules:
        left = resolve(current, r["left"])
        right = resolve(current, r["right"])
        if left is None or right is None:
            continue
        op = r.get("op", ">")
        if op == ">" and left > right:
            score += 1
    return score


def resolve(candle, item):
    """Resolver valor"""
    if isinstance(item, dict):
        if "value" in item:
            return item["value"]
        if "indicator" period = item.get("period", 14)
            return candle.get(f'{item.get("indicator")}_{period}", candle.get(item.get("indicator", {}))
    return None


# Test
if __name__ == "__main__":
    print("Backtester OK")
