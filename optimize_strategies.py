#!/usr/bin/env python3
"""
🧬 Optimizador de Estrategias - VERSIÓN CORREGIDA
==================================================
"""

import os
import pandas as pd
import numpy as np
import json
import argparse

PROJECT_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
DATA_DIR = f"{PROJECT_DIR}/data_spot"

INITIAL_BALANCE = 100000


def load_data():
    """Carga datos."""
    data = {}
    
    for coin in ['BTC', 'ETH', 'SOL']:
        filepath = f"{DATA_DIR}/{coin}-USDC_1d.csv"
        
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            
            # Normalizar columnas
            df.columns = [c.lower() for c in df.columns]
            df = df.rename(columns={
                'date': 'date',
                'open': 'open', 
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Convertir a numérico
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.dropna().sort_values('date').reset_index(drop=True)
            
            data[coin] = df
    
    return data


def calculate_indicators(df):
    """Calcula indicadores."""
    df = df.copy()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # EMAs
    for span in [9, 12, 21, 26]:
        df[f'ema_{span}'] = df['close'].ewm(span=span).mean()
    
    # MACD
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    
    # Bollinger
    df['bb_mid'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * bb_std
    df['bb_lower'] = df['bb_mid'] - 2 * bb_std
    
    # Momentum
    df['mom_5'] = df['close'].pct_change(5)
    
    return df


def generate_signal(df, params):
    """Genera señal."""
    if len(df) < 50:
        return 'hold'
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    signals = 0
    
    # RSI
    if last['rsi'] < params.get('rsi_oversold', 30):
        signals += 1
    elif last['rsi'] > params.get('rsi_overbought', 70):
        signals -= 1
    
    # EMA
    if last['ema_9'] > last['ema_21'] and prev['ema_9'] <= prev['ema_21']:
        signals += 2
    elif last['ema_9'] < last['ema_21'] and prev['ema_9'] >= prev['ema_21']:
        signals -= 2
    
    # MACD
    if last['macd'] > last['macd_signal']:
        signals += 1
    elif last['macd'] < last['macd_signal']:
        signals -= 1
    
    # Bollinger
    if last['close'] < last['bb_lower']:
        signals += 1
    elif last['close'] > last['bb_upper']:
        signals -= 1
    
    threshold = params.get('threshold', 2)
    
    if signals >= threshold:
        return 'long'
    elif signals <= -threshold:
        return 'short'
    
    return 'hold'


def backtest(df, params):
    """Backtest."""
    df = calculate_indicators(df)
    
    sl = params.get('stop_loss', 0.02)
    tp = params.get('take_profit', 0.04)
    lev = params.get('leverage', 2)
    
    balance = INITIAL_BALANCE
    position = None
    trades = []
    
    for i in range(50, len(df)):
        price = df.iloc[i]['close']
        
        if position:
            if position['side'] == 'long':
                pnl_pct = (price - position['entry']) / position['entry']
            else:
                pnl_pct = (position['entry'] - price) / position['entry']
            
            pnl_pct *= lev
            
            if pnl_pct <= -sl:
                balance -= balance * sl * lev
                trades.append(-1)
                position = None
            elif pnl_pct >= tp:
                balance += balance * tp * lev
                trades.append(1)
                position = None
        
        if not position:
            signal = generate_signal(df.iloc[:i+1], params)
            if signal != 'hold':
                position = {'side': signal, 'entry': price}
    
    if not trades:
        return {'return': 0, 'trades': 0, 'win_rate': 0}
    
    wins = sum(1 for t in trades if t > 0)
    return_pct = (balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100
    
    return {
        'return': return_pct,
        'trades': len(trades),
        'win_rate': wins / len(trades) * 100
    }


def optimize(data, coin, n_combos=100):
    """Optimiza."""
    print(f"\n🔄 {coin}: ", end="")
    
    if coin not in data:
        print("Sin datos")
        return None
    
    df = data[coin]
    
    # Parámetros a probar
    rsi_o = [25, 30, 35]
    rsi_ub = [65, 70, 75]
    ema_f = [9, 12]
    ema_s = [21, 26]
    sl = [0.01, 0.015, 0.02]
    tp = [0.03, 0.04, 0.05]
    lev = [1, 2, 3]
    thresh = [1, 2]
    
    import random
    random.seed(42)
    
    best = None
    best_result = None
    
    for _ in range(n_combos):
        params = {
            'rsi_oversold': random.choice(rsi_o),
            'rsi_overbought': random.choice(rsi_ub),
            'ema_fast': random.choice(ema_f),
            'ema_slow': random.choice(ema_s),
            'stop_loss': random.choice(sl),
            'take_profit': random.choice(tp),
            'leverage': random.choice(lev),
            'threshold': random.choice(thresh)
        }
        
        result = backtest(df, params)
        
        if best_result is None or result['return'] > best_result['return']:
            best_result = result
            best = params
    
    print(f"{best_result['return']:.1f}% ({best_result['trades']} trades, {best_result['win_rate']:.0f}% win rate)")
    
    return {'params': best, 'result': best_result}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coins", type=str, default="BTC,ETH,SOL")
    parser.add_argument("--n", type=int, default=100)
    args = parser.parse_args()
    
    coins = args.coins.split(',')
    
    print("\n" + "="*50)
    print("🧬 OPTIMIZADOR DE ESTRATEGIAS")
    print("="*50)
    
    data = load_data()
    print(f"\n📊 Datos: {', '.join(data.keys())}")
    
    results = {}
    
    for coin in coins:
        r = optimize(data, coin, args.n)
        if r:
            results[coin] = r
    
    # Guardar mejor
    if results:
        best = max(results.items(), key=lambda x: x[1]['result']['return'])
        
        print(f"\n🏆 MEJOR: {best[0]} = {best[1]['result']['return']:.1f}%")
        
        with open('best_strategy.json', 'w') as f:
            json.dump({
                'coin': best[0],
                'params': best[1]['params'],
                'result': best[1]['result']
            }, f, indent=2)
        
        print("💾 Guardado en best_strategy.json")


if __name__ == "__main__":
    main()
