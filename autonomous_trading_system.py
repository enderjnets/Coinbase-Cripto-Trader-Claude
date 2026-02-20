#!/usr/bin/env python3
"""
🚀 AUTONOMOUS TRADING SYSTEM v1.0
Capital: $500 | Meta: Doblar mensualmente (~5% diario)
Risk: 2% por trade | Stop Loss: 5% | Take Profit: 10%
"""

import sqlite3
import requests
import time
import json
import os
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass

COORDINATOR_URL = "http://localhost:5006"
DATABASE = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db"

# Configuración de Trading
CONFIG = {
    'capital_base': 500.0,
    'meta_mensual': 1.0,  # Doblar
    'risk_per_trade': 0.02,  # 2% por trade
    'stop_loss': 0.05,  # 5%
    'take_profit': 0.10,  # 10%
    'max_positions': 5,
    'min_confidence': 0.6,  # 60% confianza mínima
}

@dataclass
class Position:
    symbol: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    entry_time: datetime

class TradingSystem:
    """Sistema de trading autónomo"""
    
    def __init__(self):
        self.capital = CONFIG['capital_base']
        self.positions: List[Position] = []
        self.trades = []
        self.wins = 0
        self.losses = 0
        
    def get_market_status(self) -> Dict:
        """Obtener estado del mercado"""
        try:
            r = requests.get(f"{COORDINATOR_URL}/api/status", timeout=5)
            return r.json()
        except:
            return {'workers': {'active': 0}, 'best_strategy': {'pnl': 0}}
    
    def get_best_strategies(self) -> List[Dict]:
        """Obtener mejores estrategias del genetic algorithm"""
        try:
            r = requests.get(f"{COORDINATOR_URL}/api/leaderboard", timeout=5)
            return r.json().get('leaderboard', [])[:10]
        except:
            return []
    
    def calculate_position_size(self, confidence: float) -> float:
        """Calcular tamaño de posición basado en confianza"""
        # Más confianza = posición más grande
        base_size = self.capital * CONFIG['risk_per_trade']
        multiplier = confidence / 0.6  # Normalizar
        return min(self.capital * 0.1, base_size * multiplier)  # Max 10% del capital
    
    def execute_trade(self, strategy: Dict, price: float):
        """Ejecutar trade basado en estrategia"""
        if not strategy:
            return None
        
        symbol = strategy.get('symbol', 'BTC-USD')
        pnl = strategy.get('pnl', 0)
        confidence = strategy.get('confidence', 0.5)
        
        # Solo operar si confianza alta
        if confidence < CONFIG['min_confidence']:
            return None
        
        position_size = self.calculate_position_size(confidence)
        stop_loss_price = price * (1 - CONFIG['stop_loss'])
        take_profit_price = price * (1 + CONFIG['take_profit'])
        
        trade = {
            'symbol': symbol,
            'entry_price': price,
            'quantity': position_size / price,
            'stop_loss': stop_loss_price,
            'take_profit': take_profit_price,
            'confidence': confidence,
            'pnl': pnl,
            'timestamp': datetime.now().isoformat()
        }
        
        self.trades.append(trade)
        return trade
    
    def calculate_metrics(self) -> Dict:
        """Calcular métricas de rendimiento"""
        wins = len([t for t in self.trades if t.get('pnl', 0) > 0]
        losses = len(self.trades) - wins
        total = len(self.trades)
        
        win_rate = wins / total * 100 if total > 0 else 0
        avg_win = sum([t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) > 0]) / wins if wins > 0 else 0
        avg_loss = abs(sum([t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) < 0]) / losses if losses > 0 else 0
        
        return {
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss > 0 else 0,
            'capital_actual': self.capital + sum(t.get('pnl', 0) for t in self.trades)
        }
    
    def run_autonomous(self):
        """Ejecutar sistema autónomo"""
        print("\n" + "="*60)
        print("🚀 AUTONOMOUS TRADING SYSTEM v1.0")
        print("="*60)
        print(f"Capital: ${CONFIG['capital_base']}")
        print(f"Meta: Doblar mensualmente")
        print(f"Risk: {CONFIG['risk_per_trade']*100}% por trade")
        print(f"Stop Loss: {CONFIG['stop_loss']*100}%")
        print(f"Take Profit: {CONFIG['take_profit']*100}%")
        
        while True:
            # Obtener estrategias
            strategies = self.get_best_strategies()
            
            # Mostrar métricas
            metrics = self.calculate_metrics()
            
            print(f"\n📊 Métricas: {metrics['total_trades']} trades | Win Rate: {metrics['win_rate']:.1f}%")
            print(f"💰 Ganancias: {metrics['wins']} | Pérdidas: {metrics['losses']}")
            print(f"🎯 Promedio win: ${metrics['avg_win']:.2f} | Pérdida: ${metrics['avg_loss']:.2f}")
            
            # Mostrar mejores estrategias
            print(f"\n🏆 Top Estrategias:")
            for i, s in enumerate(strategies[:5]):
                print(f"   {i+1}. {s.get('friendly_name', 'N/A'):20s} | PnL: ${s.get('work_units', 0)} | CPU: {s.get('execution_time_hours', 0):.1f}h")
            
            time.sleep(60)

if __name__ == '__main__':
    system = TradingSystem()
    system.run_autonomous()
