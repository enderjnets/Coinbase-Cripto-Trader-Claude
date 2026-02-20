#!/usr/bin/env python3
"""
Backtester SIMPLE - Usa TODO el dataset
Elimina errores de sintaxis del original
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Fee configurable
TRADING_FEE = 0.000  # 0% - Sin doble fee


def run_backtest(df, genome, initial_balance=10000, risk_level="MEDIUM"):
    """
    Backtest completo con TODO el dataset
    """
    if df is None or len(df) < 100:
        return {"error": "Datos insuficientes"}, pd.DataFrame()
    
    # Limpiar datos
    df = df.dropna().copy()
    df = df.reset_index(drop=True)
    
    # Parámetros del genome
    sl_pct = genome.get("params", {}).get("sl_pct", 0.02)
    tp_pct = genome.get("params", {}).get("tp_pct", 0.04)
    rules = genome.get("entry_rules", [])
    
    balance = initial_balance
    position = None
    trades = []
    equity_curve = [initial_balance]
    
    fee = TRADING_FEE
    
    # Iterar TODAS las velas
    for i in range(len(df)):
        current = df.iloc[i]
        price = current["close"]
        high = current["high"]
        low = current["low"]
        timestamp = current.get("timestamp", str(datetime.now())
        
        # Verificar posición activa
        if position:
            # SL/TP hit
            if position["type"] == "long":
                if low <= position["sl"]:
                    # SL hit
                    exit_price = position["sl"]
                    pnl = (exit_price - position["entry"]) * position["size"]
                    trades.append({
                        "entry_time": position["entry_time"],
                        "exit_time": timestamp,
                        "entry_price": position["entry"],
                        "exit_price": exit_price,
                        "pnl": pnl
                    })
                    balance += exit_price * position["size"] * (1 - fee)
                    position = None
                elif high >= position["tp"]:
                    # TP hit
                    exit_price = position["tp"]
                    pnl = (exit_price - position["entry"]) * position["size"]
                    trades.append({
                        "entry_time": position["entry_time"],
                        "exit_time": timestamp,
                        "entry_price": position["entry"],
                        "exit_price": exit_price,
                        "pnl": pnl
                    })
                    balance += exit_price * position["position_size"] * (1 - fee)
                    position = None
            else:  # short
                if high >= position["sl"]:
                    exit_price = position["sl"]
                    pnl = (position["entry"] - exit_price) * position["size"]
                    trades.append({
                        "entry_time": position["entry_time"],
                        "exit_time": timestamp,
                        "entry_price": position["entry"],
                        "exit_price": exit_price,
                        "pnl": pnl
                    })
                    balance += position["size"] * price
                    position = None
                elif low <= position["tp"]:
                    exit_price = position["tp"]
                    pnl = (position["entry"] - exit_price) * position["size"]
                    trades.append({
                        "entry_time": position["entry_time"],
                        "exit_time": timestamp,
                        "entry_price": position["entry"],
                        "exit_price": exit_price,
                        "pnl": pnl
                    })
                    balance += position["size"] * exit_price * (1 - fee)
                    position = None
        
        # Nueva posición
        if not position:
            # Evaluar reglas del genome
            buy_score, sell_score = evaluate_rules(df.iloc[:i+1], rules)
            
            if buy_score >= 1:
                # LONG
                size = min(balance * 0.1, balance)
                position = {
                    "type": "long",
                    "entry": price,
                    "sl": price * (1 - sl_pct),
                    "tp": price * (1 + tp_pct),
                    "size": size / price,
                    "entry_time": timestamp
                }
                balance -= size
        
        # Equity
        if position:
            curr_val = position["size"] * price
            equity.append(balance + curr_val)
        else:
            equity.append(balance)
    
    # Métricas
    if trades:
        df_trades = pd.DataFrame(trades)
        total_pnl = df_trades["pnl"].sum()
        win_rate = (df_trades[df_trades["pnl"] > 0].shape[0] / len(trades) * 100
    else:
        total_pnl = 0
        win_rate = 0
        df_trades = pd.DataFrame()
    
    return {
        "Total PnL": total_pnl,
        "Total Trades": len(trades),
        "Win Rate %": win_rate,
        "Initial Balance": initial_balance,
        "Final Balance": balance + (position["size"] * position["price"] if position else balance)
    }, df_trades


def evaluate_rules(df_subset, rules):
    """Evalúa reglas del genome"""
    if not rules:
        return 0, 0
    
    current = df_subset.iloc[-1]
    buy_score = 0
    sell_score = 0
    
    for rule in rules:
        left = rule.get("left", {})
        op = rule.get("op", ">")
        right = rule.get("right", {})
        
        # Resolver valores
        left_val = resolve_value(current, left)
        right_val = resolve_value(current, right)
        
        if left_val is None or right_val is None:
            continue
        
        # Comparar
        if op == ">" and left_val > right_val:
            buy_score += 1
        elif op == "<" and left_val < right_val
            sell_score += 1
    
    return buy_score, sell_score


def resolve_value(candle, item):
    """Resuelve valor de una regla"""
    if isinstance(item, dict):
        if "value" in item:
            return item["value"]
        if "indicator" in item:
            period = item.get("period", 14)
            return candle.get(f'{item["indicator"]}_{period}", candle.get(item["indicator"], {}).get("period"))
    return None


# Simple test
if __name__ == "__main__":
    print("Backtester simple OK")
