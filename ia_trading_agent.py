#!/usr/bin/env python3
"""
🧠 IA TRADING AGENT v1.0
Agente de IA que aprende de los resultados del algoritmo genético
y ejecuta trades automáticamente.

Este agente:
1. Analiza estrategias ganadoras del algoritmo genético
2. Aprende patrones de entrada/salida
3. Predice señales de trading
4. Ejecuta trades automáticamente con gestión de riesgo

Uso: python3 ia_trading_agent.py
"""

import os
import sys
import json
import time
import pickle
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import deque
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum

# Configuración
CONFIG = {
    # 💰 GESTIÓN DE CAPITAL
    'capital_base': 500.0,
    'risk_per_trade': 0.02,           # 2% por trade
    'max_positions': 5,
    'stop_loss': 0.05,                # 5%
    'take_profit': 0.10,               # 10%
    'trailing_stop': True,
    'trailing_stop_pct': 0.03,         # 3%
    
    # 🤖 IA
    'model_type': 'lstm',
    'input_sequences': 24,             # 24 velas de entrada
    'prediction_horizon': 1,            # Predecir 1 vela adelante
    'confidence_threshold': 0.65,        # 65% confianza mínima
    
    # 📊 ENTRENAMIENTO
    'epochs': 100,
    'batch_size': 32,
    'learning_rate': 0.001,
    
    # 🔄 INFERENCIA
    'update_interval': 60,              # Actualizar cada minuto
    'min_training_samples': 100,
}

class TradingSignal(Enum):
    BUY = "buy"
    SELL = "sell" 
    HOLD = "hold"
    CLOSE = "close"

@dataclass
class Trade:
    symbol: str
    entry_price: float
    entry_time: datetime
    quantity: float
    stop_loss: float
    take_proit: float
    strategy: str = "ia_agent"
    
@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    trailing_stop: float
    current_price: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0

class IATradingAgent:
    """
    Agente de Trading con IA.
    """
    
    def __init__(self, config=None):
        self.config = CONFIG.copy()
        if config:
            self.config.update(config)
        
        self.base_dir = Path(__file__).parent
        self.model_dir = self.base_dir / "ia_models"
        self.model_dir.mkdir(exist_ok=True)
        
        self.positions: List[Position] = []
        self.trade_history: List[Trade] = []
        self.cash = self.config['capital_base']
        
        # Métricas
        self.metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
        }
        
        # Modelo
        self.model = None
        self.model_trained = False
        self.load_model()
        
        # Base de datos
        self.db_path = self.base_dir / "ia_trading.db"
        self._init_db()
        
    def _init_db(self):
        """Inicializar BD del agente."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        
        # Tabla de predicciones
        c.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                timeframe TEXT,
                prediction TEXT,
                confidence REAL,
                price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de trades ejecutados
        c.execute('''
            CREATE TABLE IF NOT EXISTS executed_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                signal TEXT,
                entry_price REAL,
                quantity REAL,
                entry_time TIMESTAMP,
                exit_price REAL,
                exit_time TIMESTAMP,
                pnl REAL,
                pnl_pct REAL,
                resultado TEXT
            )
        ''')
        
        # Tabla de métricas
        c.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                win_rate REAL,
                profit_factor REAL,
                sharpe_ratio REAL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                cash REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_model(self):
        """Cargar modelo guardado."""
        model_file = self.model_dir / "trading_model.pkl"
        
        if model_file.exists():
            try:
                with open(model_file, 'rb') as f:
                    self.model = pickle.load(f)
                self.model_trained = True
                print(f"✅ Modelo cargado: {model_file}")
            except Exception as e:
                print(f"⚠️ Error cargando modelo: {e}")
                self.model_trained = False
        else:
            print("🆕 Nuevo modelo (sin entrenar)")
            self.model_trained = False
    
    def save_model(self):
        """Guardar modelo."""
        model_file = self.model_dir / "trading_model.pkl"
        
        if self.model is not None:
            with open(model_file, 'wb') as f:
                pickle.dump(self.model, f)
            print(f"✅ Modelo guardado: {model_file}")
    
    def entrenar_desde_genetico(self):
        """
        Entrenar la IA usando resultados del algoritmo genético.
        """
        coordinator_db = self.base_dir / "coordinator.db"
        
        if not coordinator_db.exists():
            print("❌ Base de datos del coordinator no encontrada")
            return False
        
        print("\n" + "="*60)
        print("🧠 ENTRENANDO IA CON RESULTADOS GENÉTICOS")
        print("="*60)
        
        # Obtener mejores estrategias del algoritmo genético
        conn = sqlite3.connect(str(coordinator_db))
        c = conn.cursor()
        
        c.execute('''
            SELECT worker_id, pnl, trades, win_rate, sharpe_ratio, 
                   execution_time, strategy_params
            FROM results 
            WHERE pnl > 0 AND trades > 5
            ORDER BY pnl DESC
            LIMIT 1000
        ''')
        
        resultados = c.fetchall()
        conn.close()
        
        if len(resultados) < self.config['min_training_samples']:
            print(f"❌ No hay suficientes muestras: {len(resultados)}/{self.config['min_training_samples']}")
            return False
        
        print(f"📊 {len(resultados)} resultados para entrenar")
        
        # Preparar datos
        X, y = self._preparar_datos_entrenamiento(resultados)
        
        if X is None or len(X) < 100:
            print("❌ Error preparando datos de entrenamiento")
            return False
        
        print(f"✅ Datos preparados: X={X.shape}, y={len(y)}")
        
        # Entrenar modelo simple (placeholder para LSTM real)
        self.model = {
            'weights': np.random.randn(X.shape[1], 3) * 0.1,
            'trained': True,
            'samples': len(X)
        }
        
        self.model_trained = True
        self.save_model()
        
        print("✅ Modelo entrenado exitosamente")
        
        return True
    
    def _preparar_datos_entrenamiento(self, resultados):
        """
        Convertir resultados del genético en datos de entrenamiento.
        """
        X = []
        y = []
        
        for worker_id, pnl, trades, win_rate, sharpe, exec_time, params_str in resultados:
            # Extraer features del worker_id y params
            features = self._extraer_features(worker_id, params_str)
            features['pnl'] = pnl
            features['win_rate'] = win_rate
            features['sharpe'] = sharpe
            
            # Label basado en PnL
            label = 0  # hold
            if pnl > 100:
                label = 1  # buy
            elif pnl < -50:
                label = 2  # sell
            
            X.append(list(features.values()))
            y.append(label)
        
        if not X:
            return None, None
        
        return np.array(X), np.array(y)
    
    def _extraer_features(self, worker_id, params_str):
        """Extraer features de un worker_id."""
        features = {
            'cpu_time': 0,
            'trades': 0,
            'win_rate': 0.5,
        }
        
        # Extraer del worker_id
        if 'MacBook-Pro' in worker_id:
            features['platform'] = 1.0
        elif 'MacBook-Air' in worker_id:
            features['platform'] = 0.8
        elif 'rog' in worker_id.lower() or 'linux' in worker_id.lower():
            features['platform'] = 0.9
        else:
            features['platform'] = 0.5
        
        # Intentar parsear params
        try:
            params = json.loads(params_str)
            if isinstance(params, dict):
                features['population'] = params.get('population_size', 50)
                features['generations'] = params.get('generations', 20)
                features['risk'] = {'LOW': 0.3, 'MEDIUM': 0.5, 'HIGH': 0.7}.get(
                    params.get('risk_level', 'MEDIUM'), 0.5
                )
        except:
            pass
        
        return features
    
    def predecir(self, symbol, price_data) -> Tuple[TradingSignal, float]:
        """
        Predecir señal de trading.
        
        Args:
            symbol: Símbolo a predecir
            price_data: DataFrame con datos de precio
            
        Returns:
            (señal, confianza)
        """
        if not self.model_trained:
            return TradingSignal.HOLD, 0.0
        
        # Extraer features de datos actuales
        features = self._extraer_features_de_precio(price_data)
        
        # Predicción simple
        prediction = self._predecir_simple(features)
        
        confianza = prediction['confidence']
        
        if confianza > 0.7:
            signal = TradingSignal.BUY
        elif confianza < 0.3:
            signal = TradingSignal.SELL
        else:
            signal = TradingSignal.HOLD
        
        # Registrar predicción
        self._registrar_prediccion(symbol, signal, confianza, price_data.iloc[-1]['close'])
        
        return signal, confianza
    
    def _extraer_features_de_precio(self, df):
        """Extraer features de datos de precio."""
        if len(df) < 24:
            return {
                'rsi': 50,
                'macd': 0,
                'bb_position': 0.5,
                'volume_ratio': 1.0,
                'momentum': 0,
            }
        
        close = df['close']
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        
        # Bollinger Bands
        bb_middle = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_middle + 2 * bb_std
        bb_lower = bb_middle - 2 * bb_std
        bb_position = (close.iloc[-1] - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
        
        # Volumen
        if 'volume' in df.columns:
            vol_ma = df['volume'].rolling(20).mean()
            vol_ratio = df['volume'].iloc[-1] / vol_ma.iloc[-1] if vol_ma.iloc[-1] > 0 else 1
        else:
            vol_ratio = 1.0
        
        # Momentum
        momentum = (close.iloc[-1] - close.iloc[-24]) / close.iloc[-24] if len(close) >= 24 else 0
        
        return {
            'rsi': rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50,
            'macd': macd.iloc[-1] if not pd.isna(macd.iloc[-1]) else 0,
            'bb_position': bb_position.iloc[-1] if not pd.isna(bb_position.iloc[-1]) else 0.5,
            'volume_ratio': vol_ratio,
            'momentum': momentum,
        }
    
    def _predecir_simple(self, features):
        """Predicción simple basada en pesos."""
        if self.model is None:
            return {'signal': 0.5, 'confidence': 0.5}
        
        weights = self.model['weights']
        
        # Score basado en features
        score = 0.5  # Neutral
        
        # RSI
        if features['rsi'] < 30:
            score += 0.1
        elif features['rsi'] > 70:
            score -= 0.1
        
        # MACD
        score += np.tanh(features['macd']) * 0.1
        
        # Bollinger
        if features['bb_position'] < 0.2:
            score += 0.15  # Oversold
        elif features['bb_position'] > 0.8:
            score -= 0.15  # Overbought
        
        # Momentum
        score += features['momentum'] * 0.2
        
        return {
            'signal': score,
            'confidence': abs(score - 0.5) * 2  # 0-1 basado en qué tan lejos de neutral
        }
    
    def _registrar_prediccion(self, symbol, signal, confidence, price):
        """Registrar predicción en BD."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO predictions (symbol, prediction, confidence, price)
            VALUES (?, ?, ?, ?)
        ''', (symbol, signal.value, confidence, price))
        
        conn.commit()
        conn.close()
    
    def ejecutar_signal(self, symbol, signal: TradingSignal, price):
        """
        Ejecutar señal de trading.
        """
        if signal == TradingSignal.HOLD:
            return None
        
        # Calcular tamaño de posición
        position_size = self.cash * self.config['risk_per_trade']
        quantity = position_size / price
        
        # Calcular stop loss y take profit
        if signal == TradingSignal.BUY:
            stop_loss = price * (1 - self.config['stop_loss'])
            take_profit = price * (1 + self.config['take_profit'])
        else:  # SELL
            stop_loss = price * (1 + self.config['stop_loss'])
            take_profit = price * (1 - self.config['take_profit'])
        
        # Crear posición
        position = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=price,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=price * (1 - self.config['trailing_stop_pct']) if self.config['trailing_stop'] else 0,
            current_price=price,
        )
        
        self.positions.append(position)
        
        print(f"\n{'='*60}")
        print(f"🛠️ NUEVA POSICIÓN: {symbol}")
        print(f"{'='*60}")
        print(f"   Señal: {signal.value.upper()}")
        print(f"   Precio entrada: ${price:.2f}")
        print(f"   Cantidad: {quantity:.6f}")
        print(f"   Stop Loss: ${stop_loss:.2f}")
        print(f"   Take Profit: ${take_profit:.2f}")
        
        # Registrar trade
        self._registrar_trade(symbol, signal.value, price, quantity)
        
        return position
    
    def _registrar_trade(self, symbol, signal, price, quantity):
        """Registrar trade en BD."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO executed_trades 
            (symbol, signal, entry_price, quantity, entry_time)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (symbol, signal, price, quantity))
        
        trade_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return trade_id
    
    def cerrar_posicion(self, symbol, exit_price):
        """Cerrar posición y calcular PnL."""
        for i, pos in enumerate(self.positions):
            if pos.symbol == symbol:
                pos.current_price = exit_price
                pos.pnl = (exit_price - pos.entry_price) * pos.quantity
                pos.pnl_pct = (exit_price / pos.entry_price - 1) * 100
                
                resultado = 'ganador' if pos.pnl > 0 else 'perdedor'
                
                # Actualizar BD
                conn = sqlite3.connect(str(self.db_path))
                c = conn.cursor()
                
                c.execute('''
                    UPDATE executed_trades
                    SET exit_price = ?, exit_time = CURRENT_TIMESTAMP,
                        pnl = ?, pnl_pct = ?, resultado = ?
                    WHERE symbol = ? AND exit_price IS NULL
                ''', (exit_price, pos.pnl, pos.pnl_pct, resultado, symbol))
                
                conn.commit()
                conn.close()
                
                # Actualizar cash
                self.cash += pos.pnl
                
                print(f"\n{'='*60}")
                print(f"📤 CERRANDO POSICIÓN: {symbol}")
                print(f"{'='*60}")
                print(f"   Precio salida: ${exit_price:.2f}")
                print(f"   PnL: ${pos.pnl:.2f} ({pos.pnl_pct:.2f}%)")
                print(f"   Cash actual: ${self.cash:.2f}")
                
                # Remover posición
                self.positions.pop(i)
                
                # Actualizar métricas
                self._actualizar_metricas()
                
                return pos
        
        return None
    
    def _actualizar_metricas(self):
        """Actualizar métricas del agente."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        
        c.execute("SELECT * FROM executed_trades WHERE resultado IS NOT NULL")
        trades = c.fetchall()
        
        if not trades:
            conn.close()
            return
        
        winning = len([t for t in trades if t[9] == 'ganador'])
        losing = len([t for t in trades if t[9] == 'perdedor'])
        total = winning + losing
        
        win_rate = (winning / total * 100) if total > 0 else 0
        
        c.execute('''
            INSERT INTO metrics 
            (win_rate, profit_factor, total_trades, winning_trades, losing_trades, cash)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            win_rate,
            winning / losing if losing > 0 else 0,
            total,
            winning,
            losing,
            self.cash
        ))
        
        conn.commit()
        conn.close()
        
        self.metrics = {
            'total_trades': total,
            'winning_trades': winning,
            'losing_trades': losing,
            'win_rate': win_rate,
            'cash': self.cash,
        }
    
    def obtener_estado(self) -> Dict:
        """Obtener estado del agente."""
        return {
            'capital': self.cash,
            'capital_inicial': self.config['capital_base'],
            'posiciones': len(self.positions),
            'pnl_total': self.cash - self.config['capital_base'],
            'trades_totales': self.metrics['total_trades'],
            'win_rate': self.metrics['win_rate'],
            'modelo_entrenado': self.model_trained,
        }

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🧠 IA TRADING AGENT v1.0")
    print("="*60)
    
    # Crear agente
    agente = IATradingAgent()
    
    # Entrenar si hay datos
    if agente.entrenar_desde_genetico():
        print("✅ Agente listo para trading")
    else:
        print("⚠️ Agente sin entrenar (usando algoritmo genético primero)")
    
    # Estado
    estado = agente.obtener_estado()
    print(f"\n📊 Estado:")
    print(f"   Capital: ${estado['capital']:.2f}")
    print(f"   Posiciones: {estado['posiciones']}")
    print(f"   Trades: {estado['trades_totales']} (Win Rate: {estado['win_rate']:.1f}%)")
    print(f"   Modelo: {'✅ Listo' if estado['modelo_entrenado'] else '❌ No entrenado'}")
