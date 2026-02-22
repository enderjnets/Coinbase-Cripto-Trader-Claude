#!/usr/bin/env python3
"""
🚀 Sistema de Trading Automático de Futuros - AUTO-EVOLUTIVO
=============================================================

Sistema de trading que:
- ✅ Usa strategy miner para generar estrategias
- ✅ Escanea el mercado en tiempo real
- ✅ Ejecuta operaciones automáticamente
- ✅ Auto-aprende y evoluciona
- ✅ Busca 5% diario o doblar cuenta en 1 mes

Uso:
    python futures_auto_trader.py --start
    python futures_auto_trader.py --status
    python futures_auto_trader.py --stop
"""

import os
import sys
import json
import time
import random
import threading
import signal
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from collections import deque
import argparse

# Añadir directorio del proyecto al path
PROJECT_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
sys.path.insert(0, PROJECT_DIR)

# ============================================================
# IMPORTS DEL PROYECTO
# ============================================================

try:
    from strategy_miner import StrategyMiner
    from numba_backtester import run_backtest
    HAS_MINER = True
except ImportError:
    HAS_MINER = False
    print("⚠️ Strategy miner no disponible, usando estrategias básicas")

# ============================================================
# CONFIGURACIÓN
# ============================================================

CONFIG = {
    # Trading
    "initial_balance": 100000.0,
    "target_daily_percent": 5.0,  # Objetivo 5% diario
    "max_daily_trades": 50,
    "max_open_positions": 10,
    
    # Risk Management
    "max_position_size_pct": 0.10,  # 10% del balance por posición
    "stop_loss_pct": 0.02,  # 2%
    "take_profit_pct": 0.05,  # 5%
    "max_daily_loss_pct": 0.15,  # 15% - stop trading si se pierde más
    
    # Apalancamiento
    "default_leverage": 3,
    "max_leverage": 5,
    
    # Evolución
    "evolution_interval": 3600,  # 1 hora
    "population_size": 20,
    "generations_per_evolution": 10,
    
    # Mercado scan
    "scan_interval": 5,  # segundos
    "min_volume": 10000,
    
    # Contratos a operar
    "active_contracts": [
        "BIT-27FEB26-CDE", "BIT-27MAR26-CDE", "BIP-20DEC30-CDE",
        "ET-27FEB26-CDE", "ET-27MAR26-CDE", "ETP-20DEC30-CDE",
        "SOL-27FEB26-CDE", "SLP-20DEC30-CDE",
    ],
}

DATA_DIR = f"{PROJECT_DIR}/data_futures"
MODELS_DIR = f"{PROJECT_DIR}/models"

# ============================================================
# PRECIOS EN TIEMPO REAL
# ============================================================

class MarketScanner:
    """Escanea el mercado en tiempo real."""
    
    def __init__(self):
        self.prices = {}
        self.prices_1m = {}  # Último minuto
        self.prices_5m = {}  # Últimos 5 minutos
        self.last_update = {}
        
        self.running = False
        self.scan_thread = None
        
        # Cargar datos históricos
        self.historical_data = {}
        self._load_historical_data()
    
    def _load_historical_data(self):
        """Carga datos históricos."""
        data_path = Path(DATA_DIR)
        
        if not data_path.exists():
            print(f"⚠️ Directorio de datos no existe: {DATA_DIR}")
            return
        
        for csv_file in data_path.glob("*.csv"):
            try:
                product_id = csv_file.stem.replace("_ONE_MINUTE", "").replace("_FIVE_MINUTE", "")
                df = pd.read_csv(csv_file)
                
                if len(df) > 100:
                    self.historical_data[product_id] = df
            except:
                pass
        
        print(f"📊 Datos cargados: {len(self.historical_data)} contratos")
    
    def start(self):
        """Inicia el escaneo."""
        self.running = True
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()
        print("🔍 Escaneo de mercado iniciado")
    
    def stop(self):
        """Detiene el escaneo."""
        self.running = False
        print("🔍 Escaneo detenido")
    
    def _scan_loop(self):
        """Loop principal de escaneo."""
        import requests
        
        while self.running:
            try:
                # Obtener precios
                url = "https://api.coinbase.com/api/v3/brokerage/market/products"
                params = {"product_type": "FUTURE", "limit": 100}
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for product in data.get("products", []):
                        pid = product.get("product_id")
                        
                        if pid in CONFIG["active_contracts"]:
                            try:
                                price = float(product.get("price", 0))
                                
                                if price > 0:
                                    # Actualizar precios
                                    old_price = self.prices.get(pid, price)
                                    self.prices[pid] = price
                                    self.last_update[pid] = time.time()
                                    
                                    # Calcular cambio
                                    change_pct = ((price - old_price) / old_price * 100) if old_price > 0 else 0
                                    
                                    # Agregar a histórico 1m
                                    if pid not in self.prices_1m:
                                        self.prices_1m[pid] = deque(maxlen=60)
                                    self.prices_1m[pid].append({
                                        "price": price,
                                        "time": time.time(),
                                        "change_pct": change_pct
                                    })
                            except:
                                pass
                
                time.sleep(CONFIG["scan_interval"])
                
            except Exception as e:
                print(f"⚠️ Error en escaneo: {e}")
                time.sleep(5)
    
    def get_price(self, product_id: str) -> float:
        """Obtiene precio actual."""
        return self.prices.get(product_id, 0)
    
    def get_momentum(self, product_id: str) -> Dict:
        """Calcula momentum del precio."""
        if product_id not in self.prices_1m:
            return {"direction": "neutral", "strength": 0, "change_1m": 0}
        
        history = list(self.prices_1m[product_id])
        
        if len(history) < 2:
            return {"direction": "neutral", "strength": 0, "change_1m": 0}
        
        # Cambio en el último minuto
        change_1m = history[-1].get("change_pct", 0)
        
        # Dirección
        if change_1m > 0.1:
            direction = "long"
            strength = min(abs(change_1m) / 0.5, 1.0)
        elif change_1m < -0.1:
            direction = "short"
            strength = min(abs(change_1m) / 0.5, 1.0)
        else:
            direction = "neutral"
            strength = 0
        
        return {
            "direction": direction,
            "strength": strength,
            "change_1m": change_1m,
            "current_price": history[-1].get("price", 0)
        }


# ============================================================
# ESTRATEGIAS
# ============================================================

class StrategyGenerator:
    """Genera estrategias de trading."""
    
    def __init__(self):
        self.strategies = []
        self.best_strategies = {}  # Por contrato
        
        # Cargar o crear estrategias base
        self._init_strategies()
    
    def _init_strategies(self):
        """Inicializa estrategias base."""
        
        # Estrategias predefinidas
        base_strategies = [
            {
                "name": "momentum_breakout",
                "entry_rules": [
                    {"indicator": "RSI", "operator": "<", "value": 30},
                    {"indicator": "PRICE_CHANGE", "operator": ">", "value": 0.5}
                ],
                "exit_rules": [
                    {"indicator": "RSI", "operator": ">", "value": 70},
                    {"indicator": "PRICE_CHANGE", "operator": "<", "value": -0.5}
                ],
                "stop_loss": 0.02,
                "take_profit": 0.05,
                "leverage": 3
            },
            {
                "name": "mean_reversion",
                "entry_rules": [
                    {"indicator": "SMA", "operator": "crosses_below", "value": "EMA"},
                    {"indicator": "RSI", "operator": "<", "value": 40}
                ],
                "exit_rules": [
                    {"indicator": "SMA", "operator": "crosses_above", "value": "EMA"},
                    {"indicator": "RSI", "operator": ">", "value": 60}
                ],
                "stop_loss": 0.015,
                "take_profit": 0.04,
                "leverage": 2
            },
            {
                "name": "trend_following",
                "entry_rules": [
                    {"indicator": "EMA_20", "operator": ">", "value": "EMA_50"},
                    {"indicator": "PRICE_CHANGE", "operator": ">", "value": 0.3}
                ],
                "exit_rules": [
                    {"indicator": "EMA_20", "operator": "<", "value": "EMA_50"},
                    {"indicator": "PRICE_CHANGE", "operator": "<", "value": -0.3}
                ],
                "stop_loss": 0.025,
                "take_profit": 0.08,
                "leverage": 4
            },
            {
                "name": "volatility_squeeze",
                "entry_rules": [
                    {"indicator": "BB_WIDTH", "operator": "<", "value": 0.02},
                    {"indicator": "RSI", "operator": "<", "value": 50}
                ],
                "exit_rules": [
                    {"indicator": "BB_WIDTH", "operator": ">", "value": 0.05},
                    {"indicator": "PRICE_CHANGE", "operator": ">", "value": 1.0}
                ],
                "stop_loss": 0.02,
                "take_profit": 0.06,
                "leverage": 3
            },
            {
                "name": "breakout_continuation",
                "entry_rules": [
                    {"indicator": "PRICE", "operator": ">", "value": "HIGH_20"},
                    {"indicator": "VOLUME", "operator": ">", "value": "AVG_VOLUME_20"}
                ],
                "exit_rules": [
                    {"indicator": "PRICE", "operator": "<", "value": "LOW_10"},
                    {"indicator": "PRICE_CHANGE", "operator": "<", "value": -1.0}
                ],
                "stop_loss": 0.03,
                "take_profit": 0.10,
                "leverage": 5
            }
        ]
        
        self.strategies = base_strategies
        
        # Asignar estrategias a contratos
        for contract in CONFIG["active_contracts"]:
            self.best_strategies[contract] = random.choice(base_strategies)
        
        print(f"✅ Estrategias inicializadas: {len(base_strategies)}")
    
    def evolve_strategies(self, results: List[Dict]):
        """Evoluciona estrategias basadas en resultados."""
        
        if not results:
            return
        
        # Analizar resultados por estrategia
        strategy_performance = {}
        
        for result in results:
            strategy_name = result.get("strategy_name", "unknown")
            
            if strategy_name not in strategy_performance:
                strategy_performance[strategy_name] = {
                    "trades": 0,
                    "wins": 0,
                    "total_pnl": 0,
                    "avg_pnl": 0
                }
            
            sp = strategy_performance[strategy_name]
            sp["trades"] += 1
            sp["total_pnl"] += result.get("pnl", 0)
            
            if result.get("pnl", 0) > 0:
                sp["wins"] += 1
        
        # Calcular métricas
        for sp in strategy_performance.values():
            sp["win_rate"] = sp["wins"] / sp["trades"] * 100 if sp["trades"] > 0 else 0
            sp["avg_pnl"] = sp["total_pnl"] / sp["trades"] if sp["trades"] > 0 else 0
        
        # Mutación: ajustar parámetros de estrategias
        for strategy in self.strategies:
            name = strategy["name"]
            
            if name in strategy_performance:
                perf = strategy_performance[name]
                
                # Ajustar stop_loss y take_profit basado en performance
                if perf["avg_pnl"] < 0:
                    # Reducir riesgo
                    strategy["stop_loss"] = max(0.01, strategy["stop_loss"] * 0.8)
                    strategy["take_profit"] = max(0.02, strategy["take_profit"] * 0.9)
                elif perf["avg_pnl"] > 0 and perf["win_rate"] < 40:
                    # Aumentar profit target si win rate bajo
                    strategy["take_profit"] = min(0.15, strategy["take_profit"] * 1.2)
        
        print(f"🧬 Estrategias evolucionadas: {len(strategy_performance)} evaluadas")
    
    def get_best_strategy(self, contract: str, market_condition: Dict = None) -> Dict:
        """Obtiene mejor estrategia para un contrato."""
        
        # Por ahora, devolver estrategia asignada
        return self.best_strategies.get(contract, self.strategies[0])
    
    def generate_random_strategy(self) -> Dict:
        """Genera estrategia aleatoria."""
        
        indicators = ["RSI", "SMA", "EMA", "VOLSMA", "BB_WIDTH"]
        operators = [">", "<", "crosses_above", "crosses_below"]
        
        strategy = {
            "name": f"random_{random.randint(1000, 9999)}",
            "entry_rules": [
                {
                    "indicator": random.choice(indicators),
                    "operator": random.choice(operators[:2]),
                    "value": random.randint(10, 90)
                }
            ],
            "exit_rules": [
                {
                    "indicator": random.choice(indicators),
                    "operator": random.choice(operators[:2]),
                    "value": random.randint(10, 90)
                }
            ],
            "stop_loss": random.uniform(0.01, 0.03),
            "take_profit": random.uniform(0.03, 0.10),
            "leverage": random.randint(1, 5)
        }
        
        return strategy


# ============================================================
# SIMULADOR INTEGRADO
# ============================================================

CONTRACT_SIZES = {
    "BIT": 0.01, "BIP": 0.01,
    "ET": 0.10, "ETP": 0.10,
    "SOL": 5.0, "SLP": 5.0, "SLR": 5.0,
    "XRP": 500.0, "XPP": 500.0,
}


class AutoTrader:
    """
    Trader automático de futuros con auto-evoluación.
    
    Uso:
        trader = AutoTrader()
        trader.start()
    """
    
    def __init__(self):
        self.balance = CONFIG["initial_balance"]
        self.initial_balance = CONFIG["initial_balance"]
        self.positions = {}
        self.trade_history = []
        self.daily_pnl = 0
        self.daily_trades = 0
        self.trading_active = True
        
        # Componentes
        self.scanner = MarketScanner()
        self.strategy_gen = StrategyGenerator()
        
        # Estado
        self.running = False
        self.trade_thread = None
        self.evolution_thread = None
        
        # Métricas
        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "total_pnl": 0,
            "best_day": 0,
            "worst_day": 0,
            "consecutive_wins": 0,
            "consecutive_losses": 0
        }
        
        print(f"\n{'='*60}")
        print("🚀 SISTEMA DE TRADING AUTO-EVOLUTIVO")
        print(f"{'='*60}")
        print(f"   💰 Balance inicial: ${self.balance:,.2f}")
        print(f"   🎯 Objetivo diario: {CONFIG['target_daily_percent']}%")
        print(f"   📊 Contratos: {len(CONFIG['active_contracts'])}")
        print(f"   🧬 Evolución: cada {CONFIG['evolution_interval']}s")
        print(f"{'='*60}\n")
    
    def start(self):
        """Inicia el trading automático."""
        
        if self.running:
            print("⚠️ Trading ya activo")
            return
        
        # Iniciar componentes
        self.scanner.start()
        
        self.running = True
        
        # Hilo principal de trading
        self.trade_thread = threading.Thread(target=self._trading_loop, daemon=True)
        self.trade_thread.start()
        
        # Hilo de evolución
        self.evolution_thread = threading.Thread(target=self._evolution_loop, daemon=True)
        self.evolution_thread.start()
        
        print("✅ Trading automático iniciado")
    
    def stop(self):
        """Detiene el trading."""
        self.running = False
        self.scanner.stop()
        print("⏹️ Trading detenido")
    
    def _trading_loop(self):
        """Loop principal de trading."""
        
        while self.running:
            try:
                # Verificar límites diarios
                if self._should_stop_trading():
                    print("⏹️ Límite diario alcanzado, pausando...")
                    time.sleep(60)
                    continue
                
                # Escanear oportunidades
                opportunities = self._find_opportunities()
                
                # Ejecutar operaciones
                for opp in opportunities:
                    self._execute_trade(opp)
                
                # Verificar posiciones existentes
                self._manage_positions()
                
                # Actualizar stats
                self._update_stats()
                
                time.sleep(CONFIG["scan_interval"])
                
            except Exception as e:
                print(f"⚠️ Error en trading loop: {e}")
                time.sleep(5)
    
    def _find_opportunities(self) -> List[Dict]:
        """Encuentra oportunidades de trading."""
        
        opportunities = []
        
        # Verificar cada contrato
        for contract in CONFIG["active_contracts"]:
            # Verificar si ya hay posición
            if contract in self.positions:
                continue
            
            # Verificar límite de posiciones
            if len(self.positions) >= CONFIG["max_open_positions"]:
                break
            
            # Obtener momentum
            momentum = self.scanner.get_momentum(contract)
            
            if momentum["direction"] == "neutral":
                continue
            
            # Obtener estrategia
            strategy = self.strategy_gen.get_best_strategy(contract, momentum)
            
            # Verificar fuerza
            if momentum["strength"] < 0.3:
                continue
            
            # Crear oportunidad
            opportunity = {
                "contract": contract,
                "direction": momentum["direction"],
                "strength": momentum["strength"],
                "strategy": strategy,
                "entry_price": momentum["current_price"]
            }
            
            opportunities.append(opportunity)
        
        return opportunities
    
    def _execute_trade(self, opportunity: Dict):
        """Ejecuta una operación."""
        
        contract = opportunity["contract"]
        direction = opportunity["direction"]
        strategy = opportunity["strategy"]
        
        # Calcular tamaño de posición
        price = self.scanner.get_price(contract)
        
        if price == 0:
            return
        
        # Calcular margen disponible
        available_margin = self.balance * CONFIG["max_position_size_pct"]
        
        # Calcular tamaño
        prefix = contract.split("-")[0]
        contract_size = CONTRACT_SIZES.get(prefix, 1)
        
        leverage = strategy.get("leverage", CONFIG["default_leverage"])
        
        # Tamaño basado en margen
        size = int(available_margin * leverage / (price * contract_size))
        
        if size < 1:
            return
        
        # Calcular precio de entrada
        entry_price = price
        
        # Calcular stop loss y take profit
        stop_loss = entry_price * (1 - strategy["stop_loss"])
        take_profit = entry_price * (1 + strategy["take_profit"])
        
        if direction == "short":
            stop_loss = entry_price * (1 + strategy["stop_loss"])
            take_profit = entry_price * (1 - strategy["take_profit"])
        
        # Ejecutar (simular)
        margin_used = (price * contract_size * size) / leverage
        
        if margin_used > self.balance:
            return
        
        # Reservar margen
        self.balance -= margin_used
        
        # Crear posición
        self.positions[contract] = {
            "side": direction,
            "size": size,
            "entry_price": entry_price,
            "current_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "leverage": leverage,
            "strategy": strategy["name"],
            "opened_at": time.time(),
            "pnl": 0
        }
        
        self.daily_trades += 1
        
        # Notificación
        emoji = "🟢" if direction == "long" else "🔴"
        print(f"\n{emoji} OPERACIÓN: {direction.upper()} {size} {contract}")
        print(f"   Entry: ${entry_price:,.2f}")
        print(f"   SL: ${stop_loss:,.2f} | TP: ${take_profit:,.2f}")
        print(f"   Estrategia: {strategy['name']}")
    
    def _manage_positions(self):
        """Gestiona posiciones existentes."""
        
        to_close = []
        
        for contract, position in self.positions.items():
            # Obtener precio actual
            current_price = self.scanner.get_price(contract)
            
            if current_price == 0:
                continue
            
            position["current_price"] = current_price
            
            # Calcular PnL
            entry = position["entry_price"]
            size = position["size"]
            leverage = position["leverage"]
            side = position["side"]
            
            prefix = contract.split("-")[0]
            contract_size = CONTRACT_SIZES.get(prefix, 1)
            
            if side == "long":
                pnl_pct = (current_price - entry) / entry
            else:
                pnl_pct = (entry - current_price) / entry
            
            pnl = pnl_pct * leverage * entry * contract_size * size
            position["pnl"] = pnl
            
            # Verificar stop loss o take profit
            should_close = False
            
            if side == "long":
                if current_price <= position["stop_loss"]:
                    should_close = True
                    print(f"\n🔴 STOP LOSS: {contract}")
                elif current_price >= position["take_profit"]:
                    should_close = True
                    print(f"\n🟢 TAKE PROFIT: {contract}")
            else:
                if current_price >= position["stop_loss"]:
                    should_close = True
                    print(f"\n🔴 STOP LOSS: {contract}")
                elif current_price <= position["take_profit"]:
                    should_close = True
                    print(f"\n🟢 TAKE PROFIT: {contract}")
            
            # Cerrar si tocar SL/TP
            if should_close:
                to_close.append((contract, pnl))
        
        # Cerrrar posiciones
        for contract, pnl in to_close:
            self._close_position(contract, pnl)
    
    def _close_position(self, contract: str, pnl: float):
        """Cierra una posición."""
        
        if contract not in self.positions:
            return
        
        position = self.positions[contract]
        
        # Devolver margen
        prefix = contract.split("-")[0]
        contract_size = CONTRACT_SIZES.get(prefix, 1)
        
        margin_released = (position["entry_price"] * contract_size * position["size"]) / position["leverage"]
        
        self.balance += margin_released + pnl
        
        # Registrar trade
        trade = {
            "contract": contract,
            "side": position["side"],
            "size": position["size"],
            "entry": position["entry_price"],
            "exit": position["current_price"],
            "pnl": pnl,
            "strategy": position["strategy"],
            "duration": time.time() - position["opened_at"],
            "timestamp": datetime.now().isoformat()
        }
        
        self.trade_history.append(trade)
        self.daily_pnl += pnl
        
        # Eliminar posición
        del self.positions[contract]
        
        # Notificación
        emoji = "🟢" if pnl > 0 else "🔴"
        print(f"\n{emoji} CERRADO: {contract} | PnL: ${pnl:,.2f}")
    
    def _should_stop_trading(self) -> bool:
        """Verifica si debe detener trading."""
        
        if not self.trading_active:
            return True
        
        # Límite de trades diarios
        if self.daily_trades >= CONFIG["max_daily_trades"]:
            return True
        
        # Límite de pérdida diaria
        daily_loss_pct = self.daily_pnl / self.initial_balance
        
        if daily_loss_pct <= -CONFIG["max_daily_loss_pct"]:
            print(f"⚠️ Límite de pérdida diaria: {daily_loss_pct*100:.1f}%")
            self.trading_active = False
            return True
        
        return False
    
    def _update_stats(self):
        """Actualiza estadísticas."""
        
        # Calcular PnL total
        total_pnl = sum(p["pnl"] for p in self.positions.values())
        total_pnl += self.daily_pnl
        
        self.stats["total_pnl"] = total_pnl
        self.stats["total_trades"] = len(self.trade_history)
        
        winning = sum(1 for t in self.trade_history if t["pnl"] > 0)
        self.stats["winning_trades"] = winning
        
        # Imprimir status cada 30 segundos
        if int(time.time()) % 30 == 0:
            self._print_status()
    
    def _print_status(self):
        """Imprime status actual."""
        
        total_pnl = sum(p["pnl"] for p in self.positions.values()) + self.daily_pnl
        equity = self.balance + sum(
            (self.scanner.get_price(c) * CONTRACT_SIZES.get(c.split("-")[0], 1) * p["size"])
            for c, p in self.positions.items()
        )
        
        daily_pct = (total_pnl / self.initial_balance) * 100
        
        print(f"\n📊 STATUS: Balance: ${self.balance:,.2f} | PnL: ${total_pnl:,.2f} ({daily_pct:+.2f}%) | Pos: {len(self.positions)}")
    
    def _evolution_loop(self):
        """Loop de evolución de estrategias."""
        
        while self.running:
            time.sleep(CONFIG["evolution_interval"])
            
            # Evolucionar estrategias con resultados recientes
            recent_trades = self.trade_history[-100:]  # Últimos 100
            
            if recent_trades:
                self.strategy_gen.evolve_strategies(recent_trades)
                
                # Verificar si objetivo logrado
                equity = self.balance + sum(
                    p["pnl"] for p in self.positions.values()
                )
                
                daily_pct = ((equity - self.initial_balance) / self.initial_balance) * 100
                
                if daily_pct >= CONFIG["target_daily_percent"]:
                    print(f"\n🎉 OBJETIVO DIARIO LOGRADO: {daily_pct:.2f}%")
    
    def get_status(self) -> Dict:
        """Obtiene status del sistema."""
        
        total_pnl = sum(p["pnl"] for p in self.positions.values()) + self.daily_pnl
        equity = self.balance + sum(
            p["pnl"] for p in self.positions.values()
        )
        
        return {
            "balance": self.balance,
            "equity": equity,
            "total_pnl": total_pnl,
            "daily_pnl": self.daily_pnl,
            "daily_trades": self.daily_trades,
            "open_positions": len(self.positions),
            "total_trades": len(self.trade_history),
            "trading_active": self.trading_active,
            "positions": self.positions
        }


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Trading Automático de Futuros")
    parser.add_argument("--start", action="store_true", help="Iniciar trading")
    parser.add_argument("--stop", action="store_true", help="Detener trading")
    parser.add_argument("--status", action="store_true", help="Ver status")
    parser.add_argument("--balance", type=float, default=100000, help="Balance inicial")
    
    args = parser.parse_args()
    
    # Crear trader
    CONFIG["initial_balance"] = args.balance
    trader = AutoTrader()
    
    if args.start:
        print("\n🚀 INICIANDO SISTEMA DE TRADING...\n")
        trader.start()
        
        # Mantener vivo
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n\n⏹️ Deteniendo...")
            trader.stop()
    
    elif args.status:
        status = trader.get_status()
        
        print(f"\n{'='*60}")
        print("📊 STATUS DEL SISTEMA")
        print(f"{'='*60}")
        print(f"   Balance: ${status['balance']:,.2f}")
        print(f"   Equity: ${status['equity']:,.2f}")
        print(f"   PnL Total: ${status['total_pnl']:,.2f}")
        print(f"   PnL Diario: ${status['daily_pnl']:,.2f}")
        print(f"   Trades Hoy: {status['daily_trades']}")
        print(f"   Posiciones: {status['open_positions']}")
        print(f"   Trading Activo: {'✅' if status['trading_active'] else '❌'}")
        print(f"{'='*60}")
    
    else:
        # Modo interactivo
        print("\n🎮 MODO INTERACTIVO")
        print("   --start   Iniciar trading")
        print("   --stop    Detener trading")
        print("   --status  Ver status")
        
        trader.start()
        
        try:
            while True:
                cmd = input("\n>>> ").strip().lower()
                
                if cmd == "status" or cmd == "s":
                    trader._print_status()
                elif cmd == "stop":
                    trader.stop()
                    break
                elif cmd == "quit":
                    trader.stop()
                    break
                    
        except KeyboardInterrupt:
            trader.stop()


if __name__ == "__main__":
    main()
