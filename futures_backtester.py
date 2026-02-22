#!/usr/bin/env python3
"""
🔬 Backtester de Estrategias para Futuros
=========================================

Backtestea estrategias con datos históricos para validar
antes de operar en tiempo real.

Uso:
    python futures_backtester.py
    python futures_backtester.py --contracts BIT-27FEB26-CDE
    python futures_backtester.py --compare
"""

import os
import sys
import json
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict

# Configuración
PROJECT_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
DATA_DIR = f"{PROJECT_DIR}/data_futures"

# Tamaño de contratos
CONTRACT_SIZES = {
    "BIT": 0.01, "BIP": 0.01,
    "ET": 0.10, "ETP": 0.10,
    "SOL": 5.0, "SLP": 5.0, "SLR": 5.0,
    "XRP": 500.0, "XPP": 500.0,
}


class Strategy:
    """Estrategia de trading."""
    
    def __init__(self, name: str, params: Dict):
        self.name = name
        self.params = params
        
        # Parámetros
        self.rsi_oversold = params.get("rsi_oversold", 30)
        self.rsi_overbought = params.get("rsi_overbought", 70)
        self.sma_fast = params.get("sma_fast", 20)
        self.sma_slow = params.get("sma_slow", 50)
        self.stop_loss = params.get("stop_loss", 0.02)
        self.take_profit = params.get("take_profit", 0.05)
        self.leverage = params.get("leverage", 3)
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos."""
        df = df.copy()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # SMAs
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # EMAs
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Volatilidad
        df['volatility'] = df['close'].pct_change().rolling(window=20).std()
        
        # Price momentum
        df['momentum_5'] = df['close'].pct_change(5)
        df['momentum_1'] = df['close'].pct_change(1)
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera señales de trading."""
        df = self.calculate_indicators(df)
        
        # Inicializar señales
        df['signal'] = 'hold'
        df['signal_strength'] = 0
        
        # Estrategia 1: RSI Oversold/Overbought
        if self.name == "rsi_reversal":
            df.loc[df['rsi'] < self.rsi_oversold, 'signal'] = 'long'
            df.loc[df['rsi'] < self.rsi_oversold, 'signal_strength'] = (30 - df['rsi']) / 30
            df.loc[df['rsi'] > self.rsi_overbought, 'signal'] = 'short'
            df.loc[df['rsi'] > self.rsi_overbought, 'signal_strength'] = (df['rsi'] - 70) / 30
        
        # Estrategia 2: SMA Crossover
        elif self.name == "sma_crossover":
            df['sma_cross'] = np.where(df['sma_20'] > df['sma_50'], 1, -1)
            df['sma_cross_prev'] = df['sma_cross'].shift(1)
            df.loc[(df['sma_cross'] == 1) & (df['sma_cross_prev'] == -1), 'signal'] = 'long'
            df.loc[(df['sma_cross'] == -1) & (df['sma_cross_prev'] == 1), 'signal'] = 'short'
            df.loc[df['signal'] != 'hold', 'signal_strength'] = 0.7
        
        # Estrategia 3: MACD
        elif self.name == "macd_cross":
            df['macd_cross'] = np.where(df['macd'] > df['macd_signal'], 1, -1)
            df['macd_cross_prev'] = df['macd_cross'].shift(1)
            df.loc[(df['macd_cross'] == 1) & (df['macd_cross_prev'] == -1), 'signal'] = 'long'
            df.loc[(df['macd_cross'] == -1) & (df['macd_cross_prev'] == 1), 'signal'] = 'short'
            df.loc[df['signal'] != 'hold', 'signal_strength'] = 0.6
        
        # Estrategia 4: Breakout
        elif self.name == "breakout":
            df['high_20'] = df['high'].rolling(20).max()
            df['low_20'] = df['low'].rolling(20).min()
            df.loc[df['close'] > df['high_20'].shift(1), 'signal'] = 'long'
            df.loc[df['close'] < df['low_20'].shift(1), 'signal'] = 'short'
            df.loc[df['signal'] != 'hold', 'signal_strength'] = 0.8
        
        # Estrategia 5: Mean Reversion
        elif self.name == "mean_reversion":
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            df.loc[(df['close'] < df['bb_lower']) & (df['rsi'] < 40), 'signal'] = 'long'
            df.loc[(df['close'] > df['bb_upper']) & (df['rsi'] > 60), 'signal'] = 'short'
            df.loc[df['signal'] != 'hold', 'signal_strength'] = 0.7
        
        # Estrategia 6: Momentum
        elif self.name == "momentum":
            df.loc[df['momentum_5'] > 0.03, 'signal'] = 'long'
            df.loc[df['momentum_5'] < -0.03, 'signal'] = 'short'
            df.loc[df['signal'] != 'hold', 'signal_strength'] = abs(df['momentum_5']) * 10
        
        # Estrategia 7: Multi-timeframe
        elif self.name == "mtf_trend":
            df.loc[(df['ema_12'] > df['ema_26']) & (df['sma_20'] > df['sma_50']), 'signal'] = 'long'
            df.loc[(df['ema_12'] < df['ema_26']) & (df['sma_20'] < df['sma_50']), 'signal'] = 'short'
            df.loc[df['signal'] != 'hold', 'signal_strength'] = 0.8
        
        # Default: combinar indicadores
        else:
            # Long signals
            long_condition = (
                (df['rsi'] < 35) | 
                ((df['close'] < df['bb_lower']) & (df['rsi'] < 45)) |
                ((df['sma_20'] > df['sma_50']) & (df['momentum_5'] > 0.02))
            )
            df.loc[long_condition, 'signal'] = 'long'
            df.loc[long_condition, 'signal_strength'] = 0.5
            
            # Short signals
            short_condition = (
                (df['rsi'] > 65) |
                ((df['close'] > df['bb_upper']) & (df['rsi'] > 55)) |
                ((df['sma_20'] < df['sma_50']) & (df['momentum_5'] < -0.02))
            )
            df.loc[short_condition, 'signal'] = 'short'
            df.loc[short_condition, 'signal_strength'] = 0.5
        
        return df


class Backtester:
    """Backtester de estrategias."""
    
    def __init__(self, initial_balance: float = 100000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = []
        self.trades = []
        
    def run_backtest(self, df: pd.DataFrame, strategy: Strategy, 
                    contract: str) -> Dict:
        """Ejecuta backtest."""
        
        df = strategy.generate_signals(df)
        
        # Reset
        self.balance = self.initial_balance
        self.positions = []
        self.trades = []
        
        prefix = contract.split("-")[0]
        contract_size = CONTRACT_SIZES.get(prefix, 1)
        
        # Simular trading
        for i in range(100, len(df)):
            row = df.iloc[i]
            signal = row['signal']
            strength = row.get('signal_strength', 0)
            
            price = row['close']
            
            # Verificar posiciones existentes
            if self.positions:
                # Check exits
                for j, pos in enumerate(self.positions):
                    entry = pos['entry']
                    side = pos['side']
                    pos_sl = pos['stop_loss']
                    pos_tp = pos['take_profit']
                    
                    # Check stop loss / take profit
                    should_close = False
                    exit_reason = ""
                    
                    if side == "long":
                        if price <= entry * (1 - pos_sl):
                            should_close = True
                            exit_reason = "SL"
                        elif price >= entry * (1 + pos_tp):
                            should_close = True
                            exit_reason = "TP"
                    else:
                        if price >= entry * (1 + pos_sl):
                            should_close = True
                            exit_reason = "SL"
                        elif price <= entry * (1 - pos_tp):
                            should_close = True
                            exit_reason = "TP"
                    
                    if should_close:
                        # Calculate PnL
                        if side == "long":
                            pnl_pct = (price - entry) / entry
                        else:
                            pnl_pct = (entry - price) / entry
                        
                        pnl = pnl_pct * pos['leverage'] * entry * contract_size * pos['size']
                        
                        self.balance += entry * contract_size * pos['size'] / pos['leverage'] + pnl
                        
                        self.trades.append({
                            'side': side,
                            'entry': entry,
                            'exit': price,
                            'size': pos['size'],
                            'pnl': pnl,
                            'pnl_pct': pnl_pct * 100,
                            'duration': i - pos['entry_bar'],
                            'exit_reason': exit_reason,
                            'strategy': strategy.name
                        })
                        
                        self.positions.pop(j)
            
            # Abrir nuevas posiciones
            if signal != 'hold' and strength > 0.3 and not self.positions:
                # Calcular tamaño
                position_size = int(self.balance * 0.1 / (price * contract_size))
                
                if position_size > 0:
                    self.positions.append({
                        'side': signal,
                        'entry': price,
                        'size': position_size,
                        'stop_loss': strategy.stop_loss,
                        'take_profit': strategy.take_profit,
                        'leverage': strategy.leverage,
                        'entry_bar': i
                    })
        
        # Cerrar posiciones restantes
        final_price = df.iloc[-1]['close']
        
        for pos in self.positions:
            if pos['side'] == 'long':
                pnl_pct = (final_price - pos['entry']) / pos['entry']
            else:
                pnl_pct = (pos['entry'] - final_price) / pos['entry']
            
            pnl = pnl_pct * pos['leverage'] * pos['entry'] * contract_size * pos['size']
            
            self.trades.append({
                'side': pos['side'],
                'entry': pos['entry'],
                'exit': final_price,
                'size': pos['size'],
                'pnl': pnl,
                'pnl_pct': pnl_pct * 100,
                'duration': len(df) - pos['entry_bar'],
                'exit_reason': 'EOD',
                'strategy': strategy.name
            })
        
        # Calcular métricas
        return self._calculate_metrics()
    
    def _calculate_metrics(self) -> Dict:
        """Calcula métricas del backtest."""
        
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        wins = [t['pnl'] for t in self.trades if t['pnl'] > 0]
        losses = [t['pnl'] for t in self.trades if t['pnl'] < 0]
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        win_rate = len(wins) / len(self.trades) * 100
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 1
        
        profit_factor = sum(wins) / abs(sum(losses)) if losses else 0
        
        # Calculate drawdown
        equity = self.initial_balance
        max_equity = equity
        max_drawdown = 0
        
        for trade in self.trades:
            equity += trade['pnl']
            max_equity = max(max_equity, equity)
            drawdown = (max_equity - equity) / max_equity
            max_drawdown = max(max_drawdown, drawdown)
        
        return {
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown * 100,
            'final_balance': self.initial_balance + total_pnl,
            'return_pct': (total_pnl / self.initial_balance) * 100,
            'trades': self.trades
        }


# ============================================================
# ESTRATEGIAS PREDEFINIDAS
# ============================================================

def get_strategies() -> List[Strategy]:
    """Obtiene lista de estrategias."""
    
    strategies = [
        # RSI Reversal
        Strategy("rsi_reversal", {
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "stop_loss": 0.02,
            "take_profit": 0.05,
            "leverage": 3
        }),
        
        # SMA Crossover
        Strategy("sma_crossover", {
            "sma_fast": 20,
            "sma_slow": 50,
            "stop_loss": 0.025,
            "take_profit": 0.06,
            "leverage": 3
        }),
        
        # MACD
        Strategy("macd_cross", {
            "stop_loss": 0.02,
            "take_profit": 0.05,
            "leverage": 3
        }),
        
        # Breakout
        Strategy("breakout", {
            "stop_loss": 0.03,
            "take_profit": 0.08,
            "leverage": 4
        }),
        
        # Mean Reversion
        Strategy("mean_reversion", {
            "stop_loss": 0.015,
            "take_profit": 0.04,
            "leverage": 2
        }),
        
        # Momentum
        Strategy("momentum", {
            "stop_loss": 0.025,
            "take_profit": 0.07,
            "leverage": 4
        }),
        
        # Multi-timeframe
        Strategy("mtf_trend", {
            "stop_loss": 0.025,
            "take_profit": 0.06,
            "leverage": 3
        }),
    ]
    
    return strategies


# ============================================================
# MAIN
# ============================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Backtester de Estrategias")
    parser.add_argument("--contracts", type=str, help="Contratos a testear (separados por coma)")
    parser.add_argument("--compare", action="store_true", help="Comparar estrategias")
    parser.add_argument("--balance", type=float, default=100000, help="Balance inicial")
    parser.add_argument("--leverage", type=int, default=3, help="Apalancamiento por defecto")
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("🔬 BACKTESTER DE ESTRATEGIAS - FUTUROS")
    print("="*60 + "\n")
    
    # Cargar datos
    data_path = DATA_DIR
    contracts = args.contracts.split(",") if args.contracts else ["BIT-27FEB26-CDE", "ET-27FEB26-CDE", "SOL-27FEB26-CDE"]
    
    print(f"📊 Cargando datos de: {data_path}")
    print(f"📋 Contratos: {contracts}\n")
    
    # Estrategias
    strategies = get_strategies()
    
    # Run backtests
    results = []
    
    for contract in contracts:
        # Cargar datos
        filename = f"{contract}_ONE_MINUTE.csv"
        filepath = f"{data_path}/{filename}"
        
        if not os.path.exists(filepath):
            print(f"⚠️ No se encontró: {filepath}")
            continue
        
        print(f"\n🔄 {contract}:")
        
        df = pd.read_csv(filepath)
        
        # Usar último mes
        if len(df) > 43200:  # 30 días
            df = df.tail(43200)
        
        print(f"   Datos: {len(df)} velas")
        
        # Testear cada estrategia
        for strategy in strategies:
            backtester = Backtester(args.balance)
            
            # Ajustar leverage
            strategy.leverage = args.leverage
            
            metrics = backtester.run_backtest(df, strategy, contract)
            
            result = {
                'contract': contract,
                'strategy': strategy.name,
                **metrics
            }
            
            results.append(result)
            
            # Mostrar resultados
            print(f"   {strategy.name}:")
            print(f"      Trades: {metrics['total_trades']}")
            print(f"      Win Rate: {metrics['win_rate']:.1f}%")
            print(f"      PnL: ${metrics['total_pnl']:,.2f} ({metrics['return_pct']:+.2f}%)")
            print(f"      Profit Factor: {metrics['profit_factor']:.2f}")
    
    # Comparar estrategias
    if args.compare and results:
        print("\n" + "="*60)
        print("📊 RANKING DE ESTRATEGIAS")
        print("="*60)
        
        # Agrupar por estrategia
        by_strategy = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0, 'count': 0})
        
        for r in results:
            s = r['strategy']
            by_strategy[s]['trades'] += r['total_trades']
            by_strategy[s]['wins'] += int(r['total_trades'] * r['win_rate'] / 100)
            by_strategy[s]['pnl'] += r['total_pnl']
            by_strategy[s]['count'] += 1
        
        # Calcular promedio
        ranking = []
        for s, data in by_strategy.items():
            win_rate = data['wins'] / data['trades'] * 100 if data['trades'] > 0 else 0
            avg_pnl = data['pnl'] / data['count']
            
            ranking.append({
                'strategy': s,
                'total_trades': data['trades'],
                'win_rate': win_rate,
                'total_pnl': data['pnl'],
                'avg_pnl': avg_pnl
            })
        
        # Ordenar por PnL
        ranking.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        print(f"\n{'Estrategia':<20} {'Trades':>8} {'Win%':>8} {'PnL Total':>12} {'Avg PnL':>12}")
        print("-" * 60)
        
        for r in ranking:
            print(f"{r['strategy']:<20} {r['total_trades']:>8} {r['win_rate']:>7.1f}% ${r['total_pnl']:>10,.0f} ${r['avg_pnl']:>10,.0f}")
        
        # Mejor estrategia
        if ranking:
            best = ranking[0]
            print(f"\n🏆 MEJOR ESTRATEGIA: {best['strategy']}")
            print(f"   PnL Total: ${best['total_pnl']:,.2f}")
            print(f"   Win Rate: {best['win_rate']:.1f}%")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
