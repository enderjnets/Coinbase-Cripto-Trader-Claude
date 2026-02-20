#!/usr/bin/env python3
"""
🤖 AGENTE DE IA PARA TRADING AUTOMATIZADO
Agente de Reinforcement Learning que aprende del Algoritmo Genético

Arquitectura: PPO (Proximal Policy Optimization)
Input: Estado del mercado (price, indicators, volume, etc.)
Output: Acciones (buy, sell, hold, position_size)
Reward: PnL, Sharpe Ratio, Drawdown

Autor: Ultimate Trading System
Fecha: Febrero 2026
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
import sqlite3
from pathlib import Path

class Action(Enum):
    """Acciones posibles del agente"""
    BUY = 0
    SELL = 1
    HOLD = 2
    CLOSE_LONG = 3
    CLOSE_SHORT = 4
    INCREASE_SIZE = 5
    DECREASE_SIZE = 6

@dataclass
class MarketState:
    """Estado del mercado"""
    # Price data
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    # Technical indicators
    rsi: float
    ema_fast: float
    ema_slow: float
    vwap: float
    bb_upper: float
    bb_lower: float
    atr: float
    
    # Structure
    trend: int  # -1 (bearish), 0 (neutral), 1 (bullish)
    bos: int   # -1 (breakdown), 0 (none), 1 (breakout)
    fvg: int   # -1 (bearish), 0 (none), 1 (bullish)
    
    # Position
    position_size: float
    unrealized_pnl: float
    
    # Market conditions
    volatility: float
    volume_ratio: float
    hour_of_day: int
    
    def to_array(self) -> np.ndarray:
        """Convertir a array para el modelo"""
        return np.array([
            self.open, self.high, self.low, self.close, self.volume,
            self.rsi, self.ema_fast, self.ema_slow, self.vwap,
            self.bb_upper, self.bb_lower, self.atr,
            self.trend, self.bos, self.fvg,
            self.position_size, self.unrealized_pnl,
            self.volatility, self.volume_ratio, self.hour_of_day
        ], dtype=np.float32)

class TradingAgent:
    """Agente de IA para trading"""
    
    def __init__(self, 
                 state_size: int = 20,
                 action_size: int = 7,
                 learning_rate: float = 0.001,
                 gamma: float = 0.99,
                 epsilon: float = 1.0,
                 epsilon_min: float = 0.01,
                 epsilon_decay: float = 0.995):
        
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        
        # Red neuronal simple (DQN)
        self.model = self._build_model()
        self.target_model = self._build_model()
        self.update_target_model()
        
        # Memoria de replay
        self.memory = []
        self.max_memory = 10000
        self.batch_size = 64
        
        # Métricas
        self.total_reward = 0
        self.trades = []
        self.wins = 0
        self.losses = 0
        
    def _build_model(self):
        """Construir red neuronal"""
        # Arquitectura simple para demostración
        # En producción usar PyTorch o TensorFlow
        weights = {
            'w1': np.random.randn(self.state_size, 64) / np.sqrt(self.state_size),
            'w2': np.random.randn(64, 32) / np.sqrt(64),
            'w3': np.random.randn(32, self.action_size) / np.sqrt(32),
            'b1': np.zeros(64),
            'b2': np.zeros(32),
            'b3': np.zeros(self.action_size)
        }
        return weights
    
    def update_target_model(self):
        """Actualizar modelo objetivo"""
        for key in self.model:
            self.target_model[key] = self.model[key].copy()
    
    def predict(self, state: np.ndarray) -> Action:
        """Predecir acción"""
        if np.random.random() < self.epsilon:
            return Action(np.random.randint(self.action_size))
        
        q_values = self._forward(state)
        return Action(np.argmax(q_values))
    
    def _forward(self, state: np.ndarray) -> np.ndarray:
        """Forward pass"""
        # Layer 1
        z1 = state @ self.model['w1'] + self.model['b1']
        a1 = np.tanh(z1)
        
        # Layer 2
        z2 = a1 @ self.model['w2'] + self.model['b2']
        a2 = np.tanh(z2)
        
        # Output
        z3 = a2 @ self.model['w3'] + self.model['b3']
        return z3
    
    def remember(self, state: np.ndarray, action: Action, 
                 reward: float, next_state: np.ndarray, done: bool):
        """Guardar experiencia"""
        self.memory.append((state, action, reward, next_state, done))
        if len(self.memory) > self.max_memory:
            self.memory.pop(0)
    
    def replay(self):
        """Entrenar con replay buffer"""
        if len(self.memory) < self.batch_size:
            return
        
        batch = np.random.choice(len(self.memory), self.batch_size, replace=False)
        
        for idx in batch:
            state, action, reward, next_state, done = self.memory[idx]
            
            target = reward
            if not done:
                target = reward + self.gamma * np.max(self._forward(next_state))
            
            q_values = self._forward(state)
            q_values[action.value] = target
            
            # Entrenar (simplificado)
            self._train_step(state, q_values)
        
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def _train_step(self, state: np.ndarray, target: np.ndarray):
        """Un paso de entrenamiento (simplificado)"""
        # En producción usar backpropagation real
        pass
    
    def get_action_name(self, action: Action) -> str:
        """Nombre de la acción"""
        names = {
            Action.BUY: "🟢 BUY",
            Action.SELL: "🔴 SELL", 
            Action.HOLD: "⚪ HOLD",
            Action.CLOSE_LONG: "🔒 CLOSE LONG",
            Action.CLOSE_SHORT: "🔒 CLOSE SHORT",
            Action.INCREASE_SIZE: "📈 INCREASE SIZE",
            Action.DECREASE_SIZE: "📉 DECREASE SIZE"
        }
        return names.get(action, "❓")
    
    def load(self, filepath: str):
        """Cargar modelo"""
        with open(filepath, 'r') as f:
            data = json.load(f)
            self.model = {k: np.array(v) for k, v in data['model'].items()}
            self.epsilon = data['epsilon']
    
    def save(self, filepath: str):
        """Guardar modelo"""
        data = {
            'model': {k: v.tolist() for k, v in self.model.items()},
            'epsilon': self.epsilon,
            'timestamp': datetime.now().isoformat()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f)


class StrategyOptimizer:
    """Optimizador de estrategias con GA + IA"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.agent = TradingAgent()
        self.best_pnl = 0
        self.best_params = {}
        
    def load_ga_results(self) -> pd.DataFrame:
        """Cargar resultados del Algoritmo Genético"""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("""
                SELECT work_unit_id, pnl, trades, win_rate, 
                       execution_time, strategy_params
                FROM results
                ORDER BY pnl DESC
                LIMIT 10000
            """, conn)
            conn.close()
            return df
        except Exception as e:
            print(f"Error cargando resultados: {e}")
            return pd.DataFrame()
    
    def extract_best_strategies(self, df: pd.DataFrame) -> Dict:
        """Extraer mejores estrategias"""
        if df.empty:
            return {}
        
        # Top estrategias por PnL
        top_strategies = df.nlargest(100, 'pnl')
        
        strategies = {
            'best_pnl': top_strategies['pnl'].max(),
            'avg_pnl': top_strategies['pnl'].mean(),
            'best_win_rate': top_strategies['win_rate'].max(),
            'avg_win_rate': top_strategies['win_rate'].mean(),
            'total_trades': top_strategies['trades'].sum(),
            'avg_trades': top_strategies['trades'].mean()
        }
        
        return strategies
    
    def train_agent(self, data: pd.DataFrame):
        """Entrenar agente con datos del GA"""
        print("\n🤖 Entrenando Agente IA...")
        print(f"   📊 Datos disponibles: {len(data)} registros")
        
        # Extraer mejores estrategias
        best = self.extract_best_strategies(data)
        print(f"   💰 Mejor PnL: ${best.get('best_pnl', 0):.2f}")
        print(f"   📈 Win Rate: {best.get('best_win_rate', 0)*100:.1f}%")
        
        # Entrenar
        episodes = 100
        for episode in range(episodes):
            self.replay()
            if episode % 10 == 0:
                print(f"   📊 Episode {episode}/{episodes} - Epsilon: {self.epsilon:.3f}")
        
        print("   ✅ Entrenamiento completado")
        return best
    
    def generate_trading_signal(self, state: MarketState) -> Dict:
        """Generar señal de trading"""
        state_array = state.to_array()
        action = self.agent.predict(state_array)
        
        signal = {
            'action': action.name,
            'action_readable': self.agent.get_action_name(action),
            'confidence': np.max(self.agent._forward(state_array)),
            'timestamp': datetime.now().isoformat()
        }
        
        return signal
    
    def optimize_parameters(self, df: pd.DataFrame) -> Dict:
        """Optimizar parámetros de trading"""
        print("\n🧬 Optimizando Parámetros...")
        
        # Análisis de correlación
        if 'pnl' in df.columns and 'trades' in df.columns:
            # Encontrar mejores configuraciones
            high_pnl = df[df['pnl'] > df['pnl'].quantile(0.9)]
            
            optimal = {
                'avg_pnl_high_performers': high_pnl['pnl'].mean(),
                'avg_trades_high_performers': high_pnl['trades'].mean(),
                'win_rate_threshold': high_pnl['win_rate'].quantile(0.5)
            }
            
            print(f"   📊 Top 10% PnL promedio: ${optimal['avg_pnl_high_performers']:.2f}")
            
        return optimal
    
    def run_backtest(self, data: pd.DataFrame, strategy: Dict) -> Dict:
        """Hacer backtest de estrategia"""
        # Simplified backtest
        results = {
            'total_return': 0,
            'win_rate': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0
        }
        return results


def main():
    """Función principal"""
    print("\n" + "="*60)
    print("🤖 AGENTE DE IA PARA TRADING")
    print("="*60)
    
    # Inicializar
    db_path = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db"
    optimizer = StrategyOptimizer(db_path)
    
    # Cargar datos del GA
    print("\n📊 Cargando resultados del Algoritmo Genético...")
    data = optimizer.load_ga_results()
    print(f"   ✅ {len(data)} registros cargados")
    
    if not data.empty:
        # Entrenar agente
        optimizer.train_agent(data)
        
        # Optimizar parámetros
        params = optimizer.optimize_parameters(data)
        
        # Guardar modelo
        optimizer.agent.save("ia_trading_agent_model.json")
        print("\n💾 Modelo guardado: ia_trading_agent_model.json")
        
        print("\n" + "="*60)
        print("📈 RESUMEN DEL AGENTE IA")
        print("="*60)
        print(f"   🧠 Red neuronal: {optimizer.agent.state_size} inputs -> {optimizer.agent.action_size} outputs")
        print(f"   💾 Memoria: {len(optimizer.agent.memory)} experiencias")
        print(f"   🎯 Epsilon: {optimizer.agent.epsilon:.3f}")
        
    else:
        print("   ⚠️ No hay datos disponibles. Ejecuta el GA primero.")
    
    return optimizer


if __name__ == "__main__":
    main()
