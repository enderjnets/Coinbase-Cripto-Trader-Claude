#!/usr/bin/env python3
"""
🔬 Backtester con Datos Reales - Yahoo Finance
===============================================

Backtest completo con 1 año de datos reales.

Uso:
    python backtest_real.py
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import argparse

PROJECT_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
DATA_DIR = f"{PROJECT_DIR}/data_spot"

# Configuración
INITIAL_BALANCE = 100000
STOP_LOSS = 0.02  # 2%
TAKE_PROFIT = 0.04  # 4%
LEVERAGE = 2


def load_data():
    """Carga datos."""
    data = {}
    
    for coin in ['BTC', 'ETH', 'SOL']:
        filepath = f"{DATA_DIR}/{coin}-USDC_1d.csv"
        
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            
            # Buscar columna de fecha
            date_col = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()]
            
            if date_col:
                df['Date'] = pd.to_datetime(df[date_col[0]])
            elif 'Datetime' in df.columns:
                df['Date'] = pd.to_datetime(df['Datetime'])
            else:
                df['Date'] = pd.to_datetime(df.index, unit='d')
            
            # Buscar columnas OHLC
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high', 
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            df = df[['Date', 'open', 'high', 'low', 'close', 'volume']].dropna()
            df = df.sort_values('Date').reset_index(drop=True)
            
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
    
    # EMA
    df['ema_9'] = df['close'].ewm(span=9).mean()
    df['ema_21'] = df['close'].ewm(span=21).mean()
    
    # MACD
    df['macd'] = df['ema_9'] - df['ema_21']
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    
    # Bollinger
    df['bb_mid'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * bb_std
    df['bb_lower'] = df['bb_mid'] - 2 * bb_std
    
    # Momentum
    df['mom'] = df['close'].pct_change(5)
    
    return df


def generate_signal(df):
    """Genera señal."""
    if len(df) < 50:
        return 'hold'
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    signals = 0
    
    # RSI
    if last['rsi'] < 30:
        signals += 1
    elif last['rsi'] > 70:
        signals -= 1
    
    # EMA crossover
    if last['ema_9'] > last['ema_21'] and prev['ema_9'] <= prev['ema_21']:
        signals += 2
    elif last['ema_9'] < last['ema_21'] and prev['ema_9'] >= prev['ema_21']:
        signals -= 2
    
    # MACD
    if last['macd'] > last['macd_signal']:
        signals += 1
    elif last['macd'] < last['macd_signal']:
        signals -= 1
    
    if signals >= 2:
        return 'long'
    elif signals <= -2:
        return 'short'
    
    return 'hold'


def run_backtest(data, coin_name, coin_symbol):
    """Ejecuta backtest."""
    
    if coin_name not in data:
        print(f"⚠️ No hay datos para {coin_name}")
        return None
    
    df = data[coin_name].copy()
    df = calculate_indicators(df)
    
    balance = INITIAL_BALANCE
    position = None
    trades = []
    
    print(f"\n🔄 {coin_name} ({coin_symbol}): {len(df)} días")
    
    for i in range(50, len(df)):
        price = df.iloc[i]['close']
        
        # Verificar posición existente
        if position:
            # Calcular PnL
            if position['side'] == 'long':
                pnl_pct = (price - position['entry']) / position['entry']
            else:
                pnl_pct = (position['entry'] - price) / position['entry']
            
            pnl_pct *= position['leverage']
            
            # Check exit
            if pnl_pct <= -STOP_LOSS:
                # Stop loss
                pnl = balance * STOP_LOSS * position['leverage']
                balance -= pnl
                trades.append({'side': position['side'], 'pnl': -pnl, 'reason': 'SL'})
                position = None
                
            elif pnl_pct >= TAKE_PROFIT:
                # Take profit
                pnl = balance * TAKE_PROFIT * position['leverage']
                balance += pnl
                trades.append({'side': position['side'], 'pnl': pnl, 'reason': 'TP'})
                position = None
        
        # Nueva señal
        if not position:
            signal = generate_signal(df.iloc[:i+1])
            
            if signal != 'hold':
                # Abrir posición
                position = {
                    'side': signal,
                    'entry': price,
                    'leverage': LEVERAGE
                }
    
    # Cerrar posición final
    if position:
        price = df.iloc[-1]['close']
        
        if position['side'] == 'long':
            pnl_pct = (price - position['entry']) / position['entry']
        else:
            pnl_pct = (position['entry'] - price) / position['entry']
        
        pnl = balance * pnl_pct * position['leverage']
        balance += pnl
        trades.append({'side': position['side'], 'pnl': pnl, 'reason': 'EOD'})
    
    # Calcular métricas
    if trades:
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        
        win_rate = len(wins) / len(trades) * 100
        total_pnl = sum(t['pnl'] for t in trades)
        total_return = (balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100
        
        print(f"   Trades: {len(trades)} | Wins: {len(wins)} | Losses: {len(losses)}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   PnL: ${total_pnl:,.2f} ({total_return:+.2f}%)")
        
        return {
            'coin': coin_name,
            'trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return
        }
    
    return None


def main():
    print("\n" + "="*60)
    print("🔬 BACKTEST CON DATOS REALES (1 AÑO)")
    print("="*60)
    print(f"\nConfiguración:")
    print(f"   Balance: ${INITIAL_BALANCE:,}")
    print(f"   Stop Loss: {STOP_LOSS*100}%")
    print(f"   Take Profit: {TAKE_PROFIT*100}%")
    print(f"   Leverage: {LEVERAGE}x")
    
    # Cargar datos
    data = load_data()
    
    print(f"\n📊 Datos cargados:")
    for coin, df in data.items():
        print(f"   {coin}: {len(df)} días ({df['Date'].min().date()} a {df['Date'].max().date()})")
    
    # Run backtests
    results = []
    
    for coin in ['BTC', 'ETH', 'SOL']:
        result = run_backtest(data, coin, coin)
        if result:
            results.append(result)
    
    # Resumen
    if results:
        print("\n" + "="*60)
        print("📊 RESUMEN TOTAL")
        print("="*60)
        
        total_pnl = sum(r['total_pnl'] for r in results)
        total_return = total_pnl / INITIAL_BALANCE * 100
        total_trades = sum(r['trades'] for r in results)
        
        print(f"\n{'Moneda':<8} {'Trades':>8} {'Wins':>6} {'Win%':>8} {'PnL':>12} {'Return':>10}")
        print("-" * 54)
        
        for r in results:
            print(f"{r['coin']:<8} {r['trades']:>8} {r['wins']:>6} {r['win_rate']:>7.1f}% ${r['total_pnl']:>10,.0f} {r['total_return']:>+9.1f}%")
        
        print("-" * 54)
        
        total_wins = sum(r['wins'] for r in results)
        total_losses = sum(r['losses'] for r in results)
        total_win_rate = total_wins / total_trades * 100 if total_trades > 0 else 0
        
        print(f"{'TOTAL':<8} {total_trades:>8} {total_wins:>6} {total_win_rate:>7.1f}% ${total_pnl:>10,.0f} {total_return:>+9.1f}%")
        
        print("\n" + "="*60)
        
        if total_return > 0:
            print(f"✅ BACKTEST EXITOSO: {total_return:.1f}% en {total_trades} trades")
        else:
            print(f"❌ BACKTEST FALLIDO: {total_return:.1f}%")
        
        print("="*60)


if __name__ == "__main__":
    main()
