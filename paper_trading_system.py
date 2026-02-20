#!/usr/bin/env python3
"""
📈 SISTEMA DE PAPER TRADING
Paper Trading con el Agente IA y Estrategias del Algoritmo Genético

Capital: $10,000 virtuales
Objetivo: Validar estrategias antes de live trading
Métricas: Win rate, Sharpe, Drawdown, PnL

Autor: Ultimate Trading System
Fecha: Febrero 2026
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import json
import sqlite3
from pathlib import Path

class PositionType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"

@dataclass
class Order:
    """Orden de trading"""
    symbol: str
    position_type: PositionType
    size: float  # Porcentaje del capital
    entry_price: float = 0
    exit_price: float = 0
    stop_loss: float = 0
    take_profit: float = 0
    status: OrderStatus = OrderStatus.PENDING
    timestamp: int = 0
    fill_timestamp: int = 0
    pnl: float = 0
    commission: float = 0

@dataclass
class Position:
    """Posición abierta"""
    symbol: str
    position_type: PositionType
    size: float
    entry_price: float
    entry_timestamp: int
    stop_loss: float
    take_profit: float
    orders: List[Order] = field(default_factory=list)

@dataclass
class Trade:
    """Trade cerrado"""
    symbol: str
    position_type: PositionType
    entry_price: float
    exit_price: float
    size: float
    entry_timestamp: int
    exit_timestamp: int
    pnl: float
    pnl_pct: float
    commission: float
    duration_hours: float
    strategy: str = "Unknown"

class PaperTrader:
    """Simulador de trading"""
    
    def __init__(self, 
                 initial_capital: float = 10000,
                 fee_percent: float = 0.001,  # 0.1% por trade
                 slippage: float = 0.0005):    # 0.05%
        
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.fee_percent = fee_percent
        self.slippage = slippage
        
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.orders: List[Order] = []
        
        self.daily_pnl: Dict[str, float] = {}
        self.equity_curve: List[Dict] = []
        
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
    def get_equity(self) -> float:
        """Calcular capital actual"""
        unrealized = 0
        
        for symbol, pos in self.positions.items():
            # Precio actual sería proporcionado por feed
            current_price = self._get_current_price(symbol)
            if current_price:
                if pos.position_type == PositionType.LONG:
                    pnl_pct = (current_price - pos.entry_price) / pos.entry_price
                else:
                    pnl_pct = (pos.entry_price - current_price) / pos.entry_price
                unrealized += self.capital * pos.size * pnl_pct
        
        return self.capital + unrealized
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Obtener precio actual (en simulación, usar último close)"""
        # En paper trading real, esto vendría del feed
        return None
    
    def open_position(self, symbol: str, position_type: PositionType,
                      size_percent: float, entry_price: float,
                      stop_loss: float = None, take_profit: float = None,
                      strategy: str = "Unknown") -> Order:
        """Abrir posición"""
        
        # Calcular tamaño
        position_size = self.capital * size_percent
        
        # Calcular stop loss y take profit
        if stop_loss is None:
            if position_type == PositionType.LONG:
                stop_loss = entry_price * 0.98  # 2% stop
            else:
                stop_loss = entry_price * 1.02   # 2% stop
        
        if take_profit is None:
            if position_type == PositionType.LONG:
                take_profit = entry_price * 1.04  # 4% target
            else:
                take_profit = entry_price * 0.96  # 4% target
        
        # Crear orden
        order = Order(
            symbol=symbol,
            position_type=position_type,
            size=size_percent,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=OrderStatus.FILLED,
            timestamp=int(datetime.now().timestamp()),
            fill_timestamp=int(datetime.now().timestamp())
        )
        
        # Aplicar slippage
        if position_type == PositionType.LONG:
            order.entry_price *= (1 + self.slippage)
        else:
            order.entry_price *= (1 - self.slippage)
        
        # Cobrar comisión
        commission = position_size * self.fee_percent
        order.commission = commission
        self.capital -= commission
        
        # Crear posición
        position = Position(
            symbol=symbol,
            position_type=position_type,
            size=size_percent,
            entry_price=order.entry_price,
            entry_timestamp=order.fill_timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,
            orders=[order]
        )
        
        self.positions[symbol] = position
        self.orders.append(order)
        
        return order
    
    def close_position(self, symbol: str, exit_price: float, 
                       reason: str = "Manual") -> Trade:
        """Cerrar posición"""
        
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        
        # Calcular PnL
        if position.position_type == PositionType.LONG:
            pnl = (exit_price - position.entry_price) / position.entry_price
        else:
            pnl = (position.entry_price - exit_price) / position.entry_price
        
        pnl_value = self.capital * position.size * pnl
        
        # Comisión de salida
        commission = abs(pnl_value) * self.fee_percent
        
        # Actualizar capital
        self.capital += pnl_value - commission
        
        # Crear trade
        trade = Trade(
            symbol=symbol,
            position_type=position.position_type,
            entry_price=position.entry_price,
            exit_price=exit_price,
            size=position.size,
            entry_timestamp=position.entry_timestamp,
            exit_timestamp=int(datetime.now().timestamp()),
            pnl=pnl_value - commission,
            pnl_pct=pnl * 100,
            commission=commission,
            duration_hours=(int(datetime.now().timestamp()) - position.entry_timestamp) / 3600,
            strategy=position.orders[0].strategy if position.orders else "Unknown"
        )
        
        # Estadísticas
        self.trades.append(trade)
        self.total_trades += 1
        if trade.pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # Remover posición
        del self.positions[symbol]
        
        return trade
    
    def check_stops(self, current_prices: Dict[str, float]) -> List[Trade]:
        """Verificar stops y take profits"""
        closed_trades = []
        
        for symbol, position in self.positions.items():
            if symbol not in current_prices:
                continue
            
            price = current_prices[symbol]
            
            # Check stop loss
            if position.position_type == PositionType.LONG and price <= position.stop_loss:
                trade = self.close_position(symbol, position.stop_loss, "Stop Loss")
                if trade:
                    closed_trades.append(trade)
            
            elif position.position_type == PositionType.SHORT and price >= position.stop_loss:
                trade = self.close_position(symbol, position.stop_loss, "Stop Loss")
                if trade:
                    closed_trades.append(trade)
            
            # Check take profit
            elif position.position_type == PositionType.LONG and price >= position.take_profit:
                trade = self.close_position(symbol, position.take_profit, "Take Profit")
                if trade:
                    closed_trades.append(trade)
            
            elif position.position_type == PositionType.SHORT and price <= position.take_profit:
                trade = self.close_position(symbol, position.take_profit, "Take Profit")
                if trade:
                    closed_trades.append(trade)
        
        return closed_trades
    
    def run_backtest(self, data: pd.DataFrame, strategy: Dict) -> Dict:
        """Ejecutar backtest con estrategia"""
        # Simplified backtest implementation
        results = {
            'total_return': 0,
            'win_rate': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'total_trades': 0,
            'avg_trade': 0,
            'profit_factor': 0
        }
        return results
    
    def get_stats(self) -> Dict:
        """Obtener estadísticas"""
        if not self.trades:
            return {}
        
        winning = [t for t in self.trades if t.pnl > 0]
        losing = [t for t in self.trades if t.pnl <= 0]
        
        gross_profit = sum(t.pnl for t in winning) if winning else 0
        gross_loss = abs(sum(t.pnl for t in losing)) if losing else 0
        
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_return': total_return,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.winning_trades / self.total_trades * 100 if self.total_trades > 0 else 0,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': gross_profit / gross_loss if gross_loss > 0 else float('inf'),
            'avg_win': gross_profit / len(winning) if winning else 0,
            'avg_loss': gross_loss / len(losing) if losing else 0,
            'avg_trade': (self.capital - self.initial_capital) / self.total_trades if self.total_trades > 0 else 0
        }


class PaperTradingEngine:
    """Motor de paper trading"""
    
    def __init__(self, capital: float = 10000):
        self.trader = PaperTrader(initial_capital=capital)
        self.data_source = None
        
    def load_data(self, filepath: str):
        """Cargar datos históricos"""
        self.data_source = pd.read_csv(filepath)
        self.data_source['datetime'] = pd.to_datetime(self.data_source['timestamp'], unit='s')
        
    def run_simulation(self, strategy_func) -> Dict:
        """Ejecutar simulación"""
        if self.data_source is None:
            print("   ⚠️ No hay datos cargados")
            return {}
        
        print(f"\n📈 Ejecutando simulación...")
        print(f"   📊 Velas: {len(self.data_source)}")
        
        # Simular cada vela
        for idx, row in self.data_source.iterrows():
            current_prices = {row['symbol']: row['close']}
            
            # Verificar stops
            self.trader.check_stops(current_prices)
            
            # Ejecutar estrategia
            signal = strategy_func(row)
            if signal and signal['action'] in ['BUY', 'SELL']:
                # Abrir posición según señal
                pass
        
        return self.trader.get_stats()
    
    def display_results(self, stats: Dict):
        """Mostrar resultados"""
        print("\n" + "="*60)
        print("📈 RESULTADOS DE PAPER TRADING")
        print("="*60)
        
        if not stats:
            print("   ⚠️ No hay resultados")
            return
        
        print(f"\n💰 CAPITAL:")
        print(f"   Inicial: ${stats.get('initial_capital', 0):,.2f}")
        print(f"   Final: ${stats.get('final_capital', 0):,.2f}")
        print(f"   Retorno: {stats.get('total_return', 0):.2f}%")
        
        print(f"\n📊 TRADING:")
        print(f"   Total Trades: {stats.get('total_trades', 0)}")
        print(f"   Winners: {stats.get('winning_trades', 0)}")
        print(f"   Losers: {stats.get('losing_trades', 0)}")
        print(f"   Win Rate: {stats.get('win_rate', 0):.1f}%")
        
        print(f"\n💵 PROFIT:")
        print(f"   Gross Profit: ${stats.get('gross_profit', 0):,.2f}")
        print(f"   Gross Loss: ${stats.get('gross_loss', 0):,.2f}")
        print(f"   Profit Factor: {stats.get('profit_factor', 0):.2f}")
        print(f"   Avg Trade: ${stats.get('avg_trade', 0):,.2f}")
        
        print("\n" + "="*60)
        
        # Evaluar si pasar a live
        win_rate = stats.get('win_rate', 0)
        profit_factor = stats.get('profit_factor', 0)
        total_return = stats.get('total_return', 0)
        
        if win_rate >= 55 and profit_factor >= 1.5 and total_return > 10:
            print("   🟢 RESULTADO: APROBADO PARA LIVE TRADING")
        else:
            print("   🟡 RESULTADO: NECESITA MÁS OPTIMIZACIÓN")
        
        print("="*60)


def main():
    """Función principal"""
    print("\n" + "="*60)
    print("📈 SISTEMA DE PAPER TRADING")
    print("="*60)
    
    engine = PaperTradingEngine(capital=10000)
    
    print("\n📊 Opciones:")
    print("   [1] Ejecutar simulación rápida")
    print("   [2] Ver estadísticas actuales")
    print("   [3] Configurar capital")
    print("   [0] Salir")
    
    choice = input("\n👉 Opción: ").strip()
    
    if choice == "1":
        print("\n📥 Cargando datos...")
        # Aquí se cargarían los datos históricos
        print("   ⚠️ Requiere datos históricos")
    
    elif choice == "2":
        stats = engine.trader.get_stats()
        engine.display_results(stats)
    
    elif choice == "3":
        capital = input("\n💰 Capital inicial ($): ").strip()
        try:
            engine = PaperTradingEngine(capital=float(capital))
            print(f"   ✅ Capital configurado: ${float(capital):,}")
        except:
            print("   ❌ Capital inválido")


if __name__ == "__main__":
    main()
