#!/usr/bin/env python3
"""
Backtester OPTIMIZADO - Usa TODOS los datos disponibles
Corrige los problemas de merge_asof y iteración limitada
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

# Fees
TRADING_FEE_MAKER = 0.000  # 0% para evitar doble fee

class BacktesterOptimized:
    def __init__(self):
        self.strategy = None
    
    def run_backtest(self, df, strategy_params=None, initial_balance=10000, risk_level="MEDIUM"):
        """
        Backtest CORREGIDO - USA TODOS LOS DATOS
        """
        # Limpiar datos
        df = df.dropna().copy()
        df = df.reset_index(drop=True)
        
        # Configuración
        balance = initial_balance
        trades = []
        equity_curve = [initial_balance]
        active_position = None
        
        # Parámetros
        sl_pct = strategy_params.get('sl_pct', 0.02) if strategy_params else 0.02
        tp_pct = strategy_params.get('tp_pct', 0.04) if strategy_params else 0.04
        entry_rules = strategy_params.get('entry_rules', []) if strategy_params else []
        
        fee_rate = 0.000  # 0% fee
        
        # Iterar TODAS las velas
        position = None
        
        for i in range(len(df)):
            close = df['close'].iloc[i]
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            volume = df['volume'].iloc[i]
            timestamp = df['timestamp'].iloc[i] if 'timestamp' in df.columns else df['index'].iloc[i]
            
            # Verificar posición activa
            if position:
                # SL/TP
                if position['type'] == 'long':
                    if low <= position['sl']:
                        # SL/TP hit
                        exit_price = position['sl']
                        pnl = (close - position['entry']) * position['size'] - (close * position['size'] * fee_rate)
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': timestamp,
                            'entry_price': position['entry'],
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'pnl_pct': pnl / position['entry'] * 100,
                            'reason': 'STOP_LOSS'
                        })
                        balance += position['size'] * exit_price * (1 - fee_rate)
                        position = None
                        
                elif high >= position['tp']:
                    exit_price = position['tp']
                    pnl = (position['entry'] - close) * position['size'] - (close * position['size'] * fee_rate)
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': timestamp,
                        'entry_price': position['entry'],
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl / position['entry'] * 100,
                        'reason': 'TAKE_PROFIT'
                    })
                    balance += position['size'] * exit_price * (1 - fee_rate)
                    position = None
                    
            # Nueva posición
            if not position:
                # Evaluar reglas del genome
                should_buy, should_sell = self._evaluate_genome(df.iloc[:i+1], strategy_params)
                
                if should_buy and balance > 100:
                    # Entrar largo
                    size = min(balance * 0.1, balance)  # 10% del capital
                    position = {
                        'type': 'long',
                        'entry': close,
                        'sl': close * (1 - sl_pct),
                        'tp': close * (1 + tp_pct),
                        'entry_time': timestamp,
                        'size': size / close
                    }
                    balance -= size
                    
                elif should_sell and balance > 100:
                    # Entrar corto
                    size = min(balance * 0.1, balance)
                    position = {
                        'type': 'short',
                        'entry': close,
                        'sl': close * (1 + sl_pct),
                        'tp': close * (1 - tp_pct),
                        'entry_time': timestamp,
                        'size': size / close
                    }
                    balance -= size
            
            # Equity
            if position:
                curr_val = abs(position['size']) * close * (1 if position['type'] == 'long' else -1)
                equity = balance + curr_val
            else:
                equity = balance
            equity_curve.append(equity)
        
        # Calcular métricas
        if trades:
            df_trades = pd.DataFrame(trades)
            total_pnl = df_trades['pnl'].sum()
            win_rate = (df_trades['pnl'] > 0).mean()
            avg_pnl = df_trades['pnl'].mean()
        else:
            total_pnl = 0
            win_rate = 0
            avg_pnl = 0
            df_trades = pd.DataFrame()
        
        return {
            'Total PnL': total_pnl,
            'Total Trades': len(trades),
            'Win Rate': win_rate * 100 if trades else 0,
            'Avg PnL': avg_pnl
        }, df_trades

    def _evaluate_genome(self, df, genome):
        """Evalúa genome completo"""
        if not genome or 'entry_rules' not in genome:
            # Default: random strategy
            return True, False
        
        rules = genome['entry_rules']
        if not rules:
            return True, False
        
        current = df.iloc[-1]
        current_close = current['close']
        current_rsi = current.get('rsi', 50)
        current_sma = current.get('sma_20', current_close)
        current_ema = current.get('ema_50', current_close)
        
        buy_signals = 0
        sell_signals = 0
        
        for rule in rules:
            left = rule['left']
            op = rule['op']
            right = rule['right']
            
            left_val = current.get(left.get('indicator', left.get('field', 'close'))
            right_val = right.get('indicator', right.get('value', right.get('period'))
            
            if isinstance(right_val, dict):
                right_val = current.get(right_val.get('indicator', current_close)
            
            if op == '<' and left_val < right_val:
                buy_signals += 1
            elif op == '>' and left_val > right_val:
                sell_signals += 1
        
        return buy_signals >= 1, sell_signals >= 1


def evaluate_population_genomes(genomes, df, risk_level="MEDIUM"):
    """Evalúa población de genomes"""
    results = []
    
    for genome in genomes:
        try:
            bt = BacktesterOptimized()
            metrics, trades = bt.run_backtest(df, genome)
            results.append({
                'metrics': metrics
            })
        except Exception as e:
            results.append({
                'metrics': {'Total PnL': -9999, 'Total Trades': 0}
            })
    
    return results


# Test
if __name__ == "__main__":
    import pandas as pd
    
    # Cargar datos
    df = pd.read_csv('data/BTC-USD_FIVE_MINUTE.csv')
    print(f"Datos: {len(df)} velas")
    print(f"Balance: ${10000 + sum([m['metrics']['Total PnL'] for m in results])}")
