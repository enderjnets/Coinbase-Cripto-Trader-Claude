#!/usr/bin/env python3
"""
🚀 Sistema de Trading Optimizado
================================

Basado en parámetros optimizados para maximizar retornos.

Uso:
    python trading_optimized.py --start
    python trading_optimized.py --paper
"""

import os
import sys
import time
import threading
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List
import argparse

# Configuración
PROJECT_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
DATA_DIR = f"{PROJECT_DIR}/data_spot"

# Parámetros OPTIMIZADOS (basados en backtest)
PARAMS = {
    # Estrategia
    "rsi_oversold": 30,
    "rsi_overbought": 75,
    "ema_fast": 12,
    "ema_slow": 26,
    "threshold": 1,
    
    # Risk
    "stop_loss": 0.01,    # 1%
    "take_profit": 0.05,  # 5%
    "leverage": 3,         # 3x
    
    # Trading
    "max_positions": 3,
    "max_daily_trades": 20,
    "max_daily_loss": 0.10,  # 10%
    "target_daily": 0.03,     # 3%
}

CONTRACT_SIZES = {"BIT": 0.01, "ET": 0.10, "SOL": 5.0}


class OptimizedTrader:
    """Trader con parámetros optimizados."""
    
    def __init__(self, initial_balance=100000, paper=True):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.paper = paper
        self.positions = {}
        self.trades = []
        self.daily_pnl = 0
        self.daily_trades = 0
        
        self.running = False
        
        print(f"\n{'='*50}")
        print("🚀 SISTEMA DE TRADING OPTIMIZADO")
        print(f"{'='*50}")
        print(f"   💰 Balance: ${initial_balance:,}")
        print(f"   📊 Modo: {'PAPER TRADING' if paper else 'REAL'}")
        print(f"   🎯 SL: {PARAMS['stop_loss']*100}% | TP: {PARAMS['take_profit']*100}%")
        print(f"   💪 Leverage: {PARAMS['leverage']}x")
        print(f"{'='*50}\n")
    
    def get_prices(self) -> Dict:
        """Obtiene precios."""
        prices = {}
        
        # Contratos de futuros
        try:
            url = "https://api.coinbase.com/api/v3/brokerage/market/products"
            r = requests.get(url, params={"product_type": "FUTURE", "limit": 50}, timeout=10)
            
            if r.status_code == 200:
                data = r.json()
                
                for p in data.get("products", []):
                    pid = p.get("product_id")
                    
                    # Solo BTC, ETH, SOL
                    if pid in ["BIT-27FEB26-CDE", "ET-27FEB26-CDE", "SOL-27FEB26-CDE"]:
                        try:
                            prices[pid] = float(p.get("price", 0))
                        except:
                            pass
        except:
            pass
        
        return prices
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores."""
        df = df.copy()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMA
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Bollinger
        df['bb_mid'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * bb_std
        df['bb_lower'] = df['bb_mid'] - 2 * bb_std
        
        return df
    
    def generate_signal(self, df: pd.DataFrame) -> str:
        """Genera señal."""
        if len(df) < 30:
            return "hold"
        
        df = self.calculate_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        signals = 0
        
        # RSI
        if last['rsi'] < PARAMS['rsi_oversold']:
            signals += 1
        elif last['rsi'] > PARAMS['rsi_overbought']:
            signals -= 1
        
        # EMA Cross
        if last['ema_12'] > last['ema_26'] and prev['ema_12'] <= prev['ema_26']:
            signals += 2
        elif last['ema_12'] < last['ema_26'] and prev['ema_12'] >= prev['ema_26']:
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
        
        if signals >= PARAMS['threshold']:
            return "long"
        elif signals <= -PARAMS['threshold']:
            return "short"
        
        return "hold"
    
    def start(self):
        """Inicia trading."""
        self.running = True
        
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()
        
        print("✅ Trading iniciado")
    
    def stop(self):
        """Detiene trading."""
        self.running = False
        print("⏹️ Trading detenido")
    
    def _loop(self):
        """Loop principal."""
        while self.running:
            try:
                prices = self.get_prices()
                
                if not prices:
                    time.sleep(10)
                    continue
                
                # Ver posiciones
                self._check_positions(prices)
                
                # Nuevas señales
                if len(self.positions) < PARAMS["max_positions"]:
                    # Obtener datos de spot para señales
                    self._check_signals()
                
                # Status
                if int(time.time()) % 30 == 0:
                    self._print_status()
                
                time.sleep(15)
                
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)
    
    def _check_positions(self, prices):
        """Verifica posiciones."""
        to_close = []
        
        for contract, pos in self.positions.items():
            price = prices.get(contract, 0)
            
            if price == 0:
                continue
            
            entry = pos['entry']
            side = pos['side']
            lev = pos['leverage']
            
            # Calcular PnL
            if side == "long":
                pnl_pct = (price - entry) / entry
            else:
                pnl_pct = (entry - price) / entry
            
            pnl_pct *= lev
            
            # Check SL/TP
            if pnl_pct <= -PARAMS['stop_loss']:
                to_close.append((contract, "SL", pnl_pct))
            elif pnl_pct >= PARAMS['take_profit']:
                to_close.append((contract, "TP", pnl_pct))
        
        for contract, reason, pnl_pct in to_close:
            self._close_position(contract, pnl_pct)
    
    def _close_position(self, contract: str, pnl_pct: float):
        """Cierra posición."""
        if contract not in self.positions:
            return
        
        pos = self.positions[contract]
        
        # Calcular PnL
        pnl = self.balance * abs(pnl_pct) * pos['leverage']
        
        if pnl_pct > 0:
            self.balance += pnl
        else:
            self.balance -= pnl
        
        self.daily_pnl += pnl if pnl_pct > 0 else -pnl
        self.daily_trades += 1
        
        emoji = "🟢" if pnl_pct > 0 else "🔴"
        print(f"\n{emoji} Cerrado {contract}: {reason} | PnL: {pnl_pct*100:+.2f}%")
        
        del self.positions[contract]
    
    def _check_signals(self):
        """Busca señales."""
        # En modo real, esto tomaría datos de la API
        # Por ahora, simulamos con datos históricos
        
        if self.paper:
            # Simular señales aleatorias basadas en tiempo
            if np.random.random() < 0.1:  # 10% chance cada check
                contracts = ["BIT-27FEB26-CDE", "ET-27FEB26-CDE", "SOL-27FEB26-CDE"]
                contract = np.random.choice(contracts)
                
                if contract not in self.positions:
                    signal = np.random.choice(["long", "short"])
                    
                    # Ejecutar (simulado)
                    print(f"\n🔔 Señal: {signal.upper()} {contract}")
    
    def _print_status(self):
        """Imprime status."""
        pnl = self.balance - self.initial_balance
        pnl_pct = (pnl / self.initial_balance) * 100
        
        print(f"📊 Balance: ${self.balance:,.0f} | PnL: ${pnl:,.0f} ({pnl_pct:+.2f}%) | Pos: {len(self.positions)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--paper", action="store_true", default=True)
    parser.add_argument("--balance", type=float, default=100000)
    
    args = parser.parse_args()
    
    trader = OptimizedTrader(args.balance, args.paper)
    
    if args.start:
        trader.start()
        
        try:
            while True:
                time.sleep(10)
        except:
            trader.stop()
    else:
        print("\n📋 Comandos:")
        print("   --start    Iniciar trading")
        print("   --paper    Modo paper (default)")
        print("   --balance  Balance inicial")


if __name__ == "__main__":
    main()
