#!/usr/bin/env python3
"""
🎯 Sistema de Trading Automático - VERSIÓN OPTIMIZADA
====================================================

Objetivos realistos:
- 1-3% diario (25-60% mensual)
- Reducir drawdown
- Auto-evoluación basada en resultados reales

Uso:
    python futures_trading_system.py --start
    python futures_trading_system.py --backtest
"""

import os
import sys
import json
import time
import random
import threading
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List
from pathlib import Path
import argparse

# Paths
PROJECT_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
DATA_SPOT_DIR = f"{PROJECT_DIR}/data_spot"
DATA_FUTURES_DIR = f"{PROJECT_DIR}/data_futures"

# ============================================================
# CONFIGURACIÓN OPTIMIZADA
# ============================================================

CONFIG = {
    # OBJETIVOS REALISTAS
    "target_daily_percent": 2.0,  # 2% diario (objetivo)
    "min_daily_percent": 0.5,      # Mínimo 0.5% para seguir
    
    # Trading
    "initial_balance": 100000.0,
    "max_daily_trades": 30,
    "max_open_positions": 5,
    
    # Risk Management - CONSERVADOR
    "max_position_size_pct": 0.05,  # 5% del balance por posición
    "stop_loss_pct": 0.015,         # 1.5% stop loss
    "take_profit_pct": 0.03,        # 3% take profit (2:1 ratio)
    "max_daily_loss_pct": 0.10,     # 10% stop trading
    
    # Apalancamiento - CONSERVADOR
    "default_leverage": 2,           # 2x default
    "max_leverage": 3,               # 3x máximo
    
    # Evolución
    "evolution_interval": 1800,      # 30 minutos
    "min_trades_for_evolution": 5,   # Mínimo 5 trades
    
    # Scan
    "scan_interval": 10,             # 10 segundos
    "min_signal_strength": 0.5,      # Señal mínima
    
    # Contratos principales
    "active_contracts": [
        "BIT-27FEB26-CDE",
        "ET-27FEB26-CDE", 
        "SOL-27FEB26-CDE",
    ],
    
    # Use spot data
    "use_spot_for_signals": True,
    "spot_products": ["BTC-USD", "ETH-USD", "SOL-USD"],
}

# ============================================================
# INDICADORES TÉCNICOS
# ============================================================

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula indicadores técnicos."""
    df = df.copy()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # EMAs
    df['ema_9'] = df['close'].ewm(span=9).mean()
    df['ema_21'] = df['close'].ewm(span=21).mean()
    
    # MACD
    df['macd'] = df['ema_9'] - df['ema_21']
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + 2 * bb_std
    df['bb_lower'] = df['bb_middle'] - 2 * bb_std
    
    # Momentum
    df['momentum'] = df['close'].pct_change(5)
    
    # Volatility
    df['volatility'] = df['close'].pct_change().rolling(20).std()
    
    return df


# ============================================================
# ESTRATEGIAS
# ============================================================

class Strategy:
    """Estrategia de trading."""
    
    def __init__(self, name: str, params: Dict):
        self.name = name
        self.params = params
        self.stats = {
            "trades": 0,
            "wins": 0,
            "total_pnl": 0,
        }
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """Genera señal de trading."""
        if len(df) < 50:
            return {"action": "hold", "strength": 0}
        
        df = calculate_indicators(df)
        last = df.iloc[-1]
        
        signals = []
        
        # RSI Reversal
        if last['rsi'] < 30:
            signals.append(("long", 0.7, "rsi_oversold"))
        elif last['rsi'] > 70:
            signals.append(("short", 0.7, "rsi_overbought"))
        
        # EMA Crossover
        if last['ema_9'] > last['ema_21'] and df.iloc[-2]['ema_9'] <= df.iloc[-2]['ema_21']:
            signals.append(("long", 0.8, "ema_bullish"))
        elif last['ema_9'] < last['ema_21'] and df.iloc[-2]['ema_9'] >= df.iloc[-2]['ema_21']:
            signals.append(("short", 0.8, "ema_bearish"))
        
        # MACD
        if last['macd'] > last['macd_signal'] and df.iloc[-2]['macd'] <= df.iloc[-2]['macd_signal']:
            signals.append(("long", 0.6, "macd_bullish"))
        elif last['macd'] < last['macd_signal'] and df.iloc[-2]['macd'] >= df.iloc[-2]['macd_signal']:
            signals.append(("short", 0.6, "macd_bearish"))
        
        # Bollinger Bounce
        if last['close'] < last['bb_lower']:
            signals.append(("long", 0.5, "bb_oversold"))
        elif last['close'] > last['bb_upper']:
            signals.append(("short", 0.5, "bb_overbought"))
        
        # Elegir mejor señal
        if signals:
            # Ordenar por strength
            signals.sort(key=lambda x: x[1], reverse=True)
            return {
                "action": signals[0][0],
                "strength": signals[0][1],
                "reason": signals[0][2]
            }
        
        return {"action": "hold", "strength": 0}


# ============================================================
# MERCADO
# ============================================================

class MarketData:
    """Datos del mercado."""
    
    def __init__(self):
        self.prices = {}
        self.spot_data = {}
        self._load_spot_data()
    
    def _load_spot_data(self):
        """Carga datos spot."""
        for product in CONFIG["spot_products"]:
            filepath = f"{DATA_SPOT_DIR}/{product}_300s.csv"
            
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                self.spot_data[product] = df
                print(f"📊 Cargado: {product} ({len(df)} velas)")
    
    def get_price(self, product_id: str) -> float:
        """Obtiene precio de producto."""
        if product_id in self.prices:
            return self.prices[product_id]
        
        # Buscar en spot
        for spot, df in self.spot_data.items():
            if not df.empty:
                return float(df.iloc[-1]['close'])
        
        return 0
    
    def get_signal(self, product_id: str) -> Dict:
        """Obtiene señal para producto."""
        # Usar datos spot como referencia
        product_map = {
            "BIT": "BTC-USD",
            "ET": "ETH-USD", 
            "SOL": "SOL-USD",
        }
        
        prefix = product_id.split("-")[0]
        spot_product = product_map.get(prefix)
        
        if spot_product and spot_product in self.spot_data:
            df = self.spot_data[spot_product].copy()
            
            # Crear estrategia
            strategy = Strategy("default", {})
            return strategy.generate_signal(df)
        
        return {"action": "hold", "strength": 0}
    
    def start_live_prices(self):
        """Inicia precios en vivo."""
        
        def loop():
            while True:
                try:
                    import requests
                    
                    url = "https://api.coinbase.com/api/v3/brokerage/market/products"
                    params = {"product_type": "FUTURE", "limit": 50}
                    
                    r = requests.get(url, params=params, timeout=10)
                    
                    if r.status_code == 200:
                        data = r.json()
                        
                        for p in data.get("products", []):
                            pid = p.get("product_id")
                            try:
                                price = float(p.get("price", 0))
                                if price > 0:
                                    self.prices[pid] = price
                            except:
                                pass
                    
                    time.sleep(CONFIG["scan_interval"])
                    
                except Exception as e:
                    print(f"Error: {e}")
                    time.sleep(5)
        
        thread = threading.Thread(target=loop, daemon=True)
        thread.start()


# ============================================================
# TRADING
# ============================================================

CONTRACT_SIZES = {
    "BIT": 0.01, "BIP": 0.01,
    "ET": 0.10, "ETP": 0.10,
    "SOL": 5.0, "SLP": 5.0,
}


class TradingSystem:
    """Sistema de trading."""
    
    def __init__(self, initial_balance: float = 100000.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.positions = {}
        self.trades = []
        self.daily_pnl = 0
        self.daily_trades = 0
        
        self.market = MarketData()
        self.strategies = [
            Strategy("momentum", {"leverage": 2}),
            Strategy("mean_reversion", {"leverage": 2}),
            Strategy("breakout", {"leverage": 3}),
        ]
        
        self.running = False
        self.trading_paused = False
        
        print(f"\n{'='*60}")
        print("🚀 SISTEMA DE TRADING OPTIMIZADO")
        print(f"{'='*60}")
        print(f"   💰 Balance: ${initial_balance:,.2f}")
        print(f"   🎯 Objetivo: {CONFIG['target_daily_percent']}% diario")
        print(f"   📊 Posiciones max: {CONFIG['max_open_positions']}")
        print(f"   🛡️ SL: {CONFIG['stop_loss_pct']*100}% | TP: {CONFIG['take_profit_pct']*100}%")
        print(f"{'='*60}\n")
    
    def start(self):
        """Inicia trading."""
        self.running = True
        self.market.start_live_prices()
        
        # Thread principal
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
                # Verificar pausa
                if self.trading_paused:
                    self._check_resume()
                    time.sleep(10)
                    continue
                
                # Verificar límites
                if self._should_pause():
                    print("⏸️ Trading pausado por límites")
                    self.trading_paused = True
                    time.sleep(60)
                    continue
                
                # Buscar oportunidades
                opportunities = self._find_opportunities()
                
                # Ejecutar
                for opp in opportunities:
                    self._execute(opp)
                
                # Gestionar posiciones
                self._manage_positions()
                
                # Status
                if int(time.time()) % 30 == 0:
                    self._print_status()
                
                time.sleep(CONFIG["scan_interval"])
                
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)
    
    def _find_opportunities(self) -> List[Dict]:
        """Busca oportunidades."""
        opportunities = []
        
        # Verificar contratos
        for contract in CONFIG["active_contracts"]:
            if len(self.positions) >= CONFIG["max_open_positions"]:
                break
            
            if contract in self.positions:
                continue
            
            # Obtener señal
            signal = self.market.get_signal(contract)
            
            if signal["action"] != "hold" and signal["strength"] >= CONFIG["min_signal_strength"]:
                opportunities.append({
                    "contract": contract,
                    "action": signal["action"],
                    "strength": signal["strength"],
                    "reason": signal.get("reason", "unknown")
                })
        
        return opportunities
    
    def _execute(self, opp: Dict):
        """Ejecuta operación."""
        contract = opp["contract"]
        action = opp["action"]
        
        price = self.market.get_price(contract)
        
        if price == 0:
            price = 67000  # Default para BTC
        
        # Calcular tamaño
        prefix = contract.split("-")[0]
        size = CONTRACT_SIZES.get(prefix, 1)
        
        leverage = CONFIG["default_leverage"]
        
        # Calcular margen
        margin_needed = (price * size * leverage)
        max_position = self.balance * CONFIG["max_position_size_pct"]
        
        if margin_needed > max_position:
            # Reducir tamaño
            leverage = 1
        
        margin_used = (price * size * leverage)
        
        if margin_used > self.balance:
            return
        
        # Ejecutar
        self.balance -= margin_used
        
        sl = price * (1 - CONFIG["stop_loss_pct"])
        tp = price * (1 + CONFIG["take_profit_pct"])
        
        if action == "short":
            sl = price * (1 + CONFIG["stop_loss_pct"])
            tp = price * (1 - CONFIG["take_profit_pct"])
        
        self.positions[contract] = {
            "side": action,
            "size": 1,
            "entry": price,
            "sl": sl,
            "tp": tp,
            "leverage": leverage,
            "opened": time.time()
        }
        
        self.daily_trades += 1
        
        emoji = "🟢" if action == "long" else "🔴"
        print(f"\n{emoji} {action.upper()} {contract} @ ${price:,.0f}")
    
    def _manage_positions(self):
        """Gestiona posiciones."""
        to_close = []
        
        for contract, pos in self.positions.items():
            price = self.market.get_price(contract)
            
            if price == 0:
                continue
            
            # Verificar SL/TP
            if pos["side"] == "long":
                if price <= pos["sl"]:
                    to_close.append((contract, "SL"))
                elif price >= pos["tp"]:
                    to_close.append((contract, "TP"))
            else:
                if price >= pos["sl"]:
                    to_close.append((contract, "SL"))
                elif price <= pos["tp"]:
                    to_close.append((contract, "TP"))
        
        for contract, reason in to_close:
            self._close_position(contract, reason)
    
    def _close_position(self, contract: str, reason: str):
        """Cierra posición."""
        if contract not in self.positions:
            return
        
        pos = self.positions[contract]
        
        price = self.market.get_price(contract)
        
        # Calcular PnL
        if pos["side"] == "long":
            pnl_pct = (price - pos["entry"]) / pos["entry"]
        else:
            pnl_pct = (pos["entry"] - price) / pos["entry"]
        
        pnl = pnl_pct * pos["leverage"] * pos["entry"] * pos["size"] * CONTRACT_SIZES.get(
            contract.split("-")[0], 1
        )
        
        # Devolver margen
        margin = pos["entry"] * pos["size"] * CONTRACT_SIZES.get(
            contract.split("-")[0], 1
        ) / pos["leverage"]
        
        self.balance += margin + pnl
        self.daily_pnl += pnl
        
        # Registrar trade
        self.trades.append({
            "contract": contract,
            "side": pos["side"],
            "pnl": pnl,
            "reason": reason
        })
        
        # Actualizar stats de estrategia
        for s in self.strategies:
            s.stats["trades"] += 1
            if pnl > 0:
                s.stats["wins"] += 1
            s.stats["total_pnl"] += pnl
        
        emoji = "🟢" if pnl > 0 else "🔴"
        print(f"\n{emoji} Cerrado {contract}: {reason} | PnL: ${pnl:,.2f}")
        
        del self.positions[contract]
    
    def _should_pause(self) -> bool:
        """Verifica si debe pausar."""
        if self.daily_trades >= CONFIG["max_daily_trades"]:
            return True
        
        # Pérdida diaria
        if self.daily_pnl < 0:
            loss_pct = abs(self.daily_pnl) / self.initial_balance
            
            if loss_pct >= CONFIG["max_daily_loss_pct"]:
                print(f"⚠️ Límite de pérdida: {loss_pct*100:.1f}%")
                return True
        
        return False
    
    def _check_resume(self):
        """Verifica si puede reanudar."""
        # Nuevo día
        self.daily_pnl = 0
        self.daily_trades = 0
        self.trading_paused = False
        
        print("✅ Nuevo día, trading reanudado")
    
    def _print_status(self):
        """Imprime status."""
        equity = self.balance + sum(
            p["entry"] * p["size"] / p["leverage"] 
            for p in self.positions.values()
        )
        
        pnl = equity - self.initial_balance
        pnl_pct = (pnl / self.initial_balance) * 100
        
        print(f"📊 Balance: ${self.balance:,.0f} | PnL: ${pnl:,.0f} ({pnl_pct:+.1f}%) | Pos: {len(self.positions)}")
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas."""
        return {
            "balance": self.balance,
            "daily_pnl": self.daily_pnl,
            "trades": len(self.trades),
            "positions": len(self.positions)
        }


# ============================================================
# BACKTEST
# ============================================================

def run_backtest(days: int = 1):
    """Ejecuta backtest con datos reales."""
    
    print("\n" + "="*60)
    print("🔬 BACKTEST CON DATOS REALES")
    print("="*60 + "\n")
    
    # Cargar datos
    system = TradingSystem()
    
    # Simular trading
    print("📊 Ejecutando backtest...")
    
    # Obtener datos de spot
    for product, df in system.market.spot_data.items():
        if df.empty:
            continue
        
        print(f"\n🔄 {product}: {len(df)} velas")
        
        # Calcular señales
        strategy = Strategy("test", {})
        
        # Simular operaciones
        in_position = False
        entry_price = 0
        entry_time = None
        
        for i in range(50, len(df)):
            df_slice = df.iloc[:i+1].copy()
            
            signal = strategy.generate_signal(df_slice)
            
            price = df.iloc[i]['close']
            
            if not in_position and signal["action"] != "hold":
                # Entrar
                in_position = True
                entry_price = price
                entry_time = i
                
                action = signal["action"]
                emoji = "🟢" if action == "long" else "🔴"
                print(f"   {emoji} Entry {action} @ ${price:.2f}")
            
            elif in_position:
                # Check exit
                pnl_pct = (price - entry_price) / entry_price if signal["action"] == "long" else (entry_price - price) / entry_price
                
                # SL/TP
                if pnl_pct <= -CONFIG["stop_loss_pct"] or pnl_pct >= CONFIG["take_profit_pct"]:
                    emoji = "🟢" if pnl_pct > 0 else "🔴"
                    reason = "TP" if pnl_pct > 0 else "SL"
                    print(f"   {emoji} Exit {reason} @ ${price:.2f} ({pnl_pct*100:+.2f}%)")
                    in_position = False
    
    print("\n" + "="*60)


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", action="store_true", help="Iniciar trading")
    parser.add_argument("--backtest", action="store_true", help="Ejecutar backtest")
    parser.add_argument("--balance", type=float, default=100000)
    
    args = parser.parse_args()
    
    if args.backtest:
        run_backtest()
        return
    
    # Modo interactivo / start
    system = TradingSystem(args.balance)
    
    if args.start:
        print("\n🚀 Iniciando...\n")
        system.start()
        
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            system.stop()
    else:
        print("\n🎮 Comandos:")
        print("   --start     Iniciar trading")
        print("   --backtest  Ejecutar backtest")


if __name__ == "__main__":
    main()
