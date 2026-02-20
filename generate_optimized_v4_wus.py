#!/usr/bin/env python3
"""
OPTIMIZED WU GENERATOR v4.0
Genera WUs basados en los mejores resultados ULTIMATE

Mejores resultados:
- CCI Oversold: $428.35 (14 trades, 64.3% win)
- The Record Breaker v3: $424.35 (17 trades, 70.6% win)
- Stochastic Oversold: $396.95 (10 trades, 70% win)
"""

import sqlite3
import json
from datetime import datetime

class OptimizedWUGenerator:
    """Genera WUs optimizados basados en mejores resultados"""
    
    def generate_optimized_strategies(self):
        """Genera estrategias basadas en los mejores resultados"""
        
        strategies = [
            # === CCI OPTIMIZADO ===
            {
                "name": "OPTIMIZED_CCI_Pro_v2",
                "category": "Momentum",
                "description": "Based on ULTIMATE_CCI_Oversold success ($428.35)",
                "population_size": 270,
                "generations": 315,
                "mutation_rate": 0.20,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.8,
                "take_profit": 4.65,
                "trailing_stop_pct": 0.02,
                "breakeven_after": 0.015,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "CCI", "period": 20}, "op": "<", "right": {"value": -100}},
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 35}},
                    {"left": {"field": "close"}, "op": ">", "right": {"indicator": "EMA", "period": 20}}
                ]
            },
            
            # === THE RECORD BREAKER OPTIMIZED ===
            {
                "name": "OPTIMIZED_Record_Breaker_v4",
                "category": "Record Breaker",
                "description": "Enhanced version of $424.35 winner",
                "population_size": 255,
                "generations": 305,
                "mutation_rate": 0.18,
                "crossover_rate": 0.88,
                "elite_rate": 0.13,
                "risk_level": "HIGH",
                "stop_loss": 1.75,
                "take_profit": 4.7,
                "trailing_stop_pct": 0.025,
                "breakeven_after": 0.02,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30}},
                    {"left": {"field": "close"}, "op": ">", "right": {"indicator": "SMA", "period": 50}},
                    {"left": {"indicator": "MACD_Hist", "period": 12}, "op": ">", "right": {"value": 0}},
                    {"left": {"indicator": "CCI", "period": 20}, "op": "<", "right": {"value": -50}}
                ]
            },
            
            # === SUPER COMBO MULTI-INDI ===
            {
                "name": "OPTIMIZED_Super_Combo",
                "category": "Multi-Factor",
                "description": "Maximum indicator confluence for record breaking",
                "population_size": 285,
                "generations": 330,
                "mutation_rate": 0.18,
                "crossover_rate": 0.88,
                "elite_rate": 0.14,
                "risk_level": "HIGH",
                "stop_loss": 1.7,
                "take_profit": 4.8,
                "trailing_stop_pct": 0.025,
                "breakeven_after": 0.02,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "CCI", "period": 20}, "op": "<", "right": {"value": -100}},
                    {"left": {"indicator": "STOCH_K", "period": 14}, "op": "<", "right": {"value": 20}},
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 35}},
                    {"left": {"indicator": "WILLIAMS_R", "period": 14}, "op": "<", "right": {"value": -80}}
                ]
            },
            
            # === STOCHASTIC POWER ===
            {
                "name": "OPTIMIZED_Stochastic_Power",
                "category": "Momentum",
                "description": "Enhanced stochastic with CCI confirmation",
                "population_size": 265,
                "generations": 310,
                "mutation_rate": 0.20,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.8,
                "take_profit": 4.6,
                "trailing_stop_pct": 0.02,
                "breakeven_after": 0.015,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "STOCH_K", "period": 14}, "op": "<", "right": {"value": 15}},
                    {"left": {"indicator": "CCI", "period": 20}, "op": "<", "right": {"value": -80}},
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30}}
                ]
            },
            
            # === WILLIAMS OPTIMIZED ===
            {
                "name": "OPTIMIZED_Williams_Pro",
                "category": "Momentum",
                "description": "Williams %R with stochastic confirmation",
                "population_size": 260,
                "generations": 305,
                "mutation_rate": 0.22,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.75,
                "take_profit": 4.5,
                "trailing_stop_pct": 0.02,
                "breakeven_after": 0.015,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "WILLIAMS_R", "period": 14}, "op": "<", "right": {"value": -85}},
                    {"left": {"indicator": "STOCH_K", "period": 14}, "op": "<", "right": {"value": 20}},
                    {"left": {"field": "close"}, "op": ">", "right": {"indicator": "EMA", "period": 50}}
                ]
            },
            
            # === ROC MOMENTUM OPTIMIZED ===
            {
                "name": "OPTIMIZED_ROC_Momentum_Pro",
                "category": "Momentum",
                "description": "ROC with CCI confirmation",
                "population_size": 268,
                "generations": 312,
                "mutation_rate": 0.20,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.8,
                "take_profit": 4.7,
                "trailing_stop_pct": 0.025,
                "breakeven_after": 0.02,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "ROC", "period": 10}, "op": ">", "right": {"value": 1}},
                    {"left": {"indicator": "CCI", "period": 20}, "op": "<", "right": {"value": -50}},
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 45}}
                ]
            },
            
            # === VOLATILITY ADAPTIVE PRO ===
            {
                "name": "OPTIMIZED_Volatility_Adaptive_Pro",
                "category": "Volatility",
                "description": "Enhanced volatility adaptive strategy",
                "population_size": 275,
                "generations": 320,
                "mutation_rate": 0.18,
                "crossover_rate": 0.87,
                "elite_rate": 0.13,
                "risk_level": "HIGH",
                "stop_loss": 1.9,
                "take_profit": 5.0,
                "trailing_stop_pct": 0.03,
                "breakeven_after": 0.02,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "BB_Width", "period": 20}, "op": ">", "right": {"value": 4}},
                    {"left": {"indicator": "ATR_Pct", "period": 14}, "op": ">", "right": {"value": 2.5}},
                    {"left": {"indicator": "CCI", "period": 20}, "op": "<", "right": {"value": -60}}
                ]
            },
            
            # === THE ULTIMATE BREAKER ===
            {
                "name": "OPTIMIZED_The_Ultimate_Breaker",
                "category": "Record Breaker",
                "description": "Maximum confluence for record breaking attempt",
                "population_size": 250,
                "generations": 300,
                "mutation_rate": 0.20,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.8,
                "take_profit": 4.5,
                "trailing_stop_pct": 0.025,
                "breakeven_after": 0.02,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "CCI", "period": 20}, "op": "<", "right": {"value": -100}},
                    {"left": {"indicator": "STOCH_K", "period": 14}, "op": "<", "right": {"value": 15}},
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 28}},
                    {"left": {"field": "close"}, "op": ">", "right": {"indicator": "EMA", "period": 20}}
                ]
            },
            
            # === ICHIMOKU ULTIMATE ===
            {
                "name": "OPTIMIZED_Ichimoku_Ultimate",
                "category": "Trend Following",
                "description": "Ichimoku with momentum confirmation",
                "population_size": 280,
                "generations": 325,
                "mutation_rate": 0.18,
                "crossover_rate": 0.88,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.9,
                "take_profit": 4.9,
                "trailing_stop_pct": 0.025,
                "breakeven_after": 0.02,
                "timeframe": "15m",
                "data_file": "BTC-USD_FIFTEEN_MINUTE.csv",
                "max_candles": 150000,
                "entry_rules": [
                    {"left": {"field": "close"}, "op": ">", "right": {"indicator": "ICHIMOKU_Base", "period": 26}},
                    {"left": {"indicator": "ICHIMOKU_Conv", "period": 9}, "op": ">", "right": {"indicator": "ICHIMOKU_Base", "period": 26}},
                    {"left": {"indicator": "CCI", "period": 20}, "op": "<", "right": {"value": -50}}
                ]
            },
            
            # === OBV VOLUME PRO ===
            {
                "name": "OPTIMIZED_OBV_Volume_Pro",
                "category": "Volume",
                "description": "OBV with momentum confirmation",
                "population_size": 262,
                "generations": 308,
                "mutation_rate": 0.20,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.75,
                "take_profit": 4.55,
                "trailing_stop_pct": 0.02,
                "breakeven_after": 0.015,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 32}},
                    {"left": {"indicator": "CCI", "period": 20}, "op": "<", "right": {"value": -70}},
                    {"left": {"field": "close"}, "op": ">", "right": {"indicator": "SMA", "period": 50}}
                ]
            }
        ]
        
        return strategies
    
    def create_wus(self):
        strategies = self.generate_optimized_strategies()
        
        print("="*80)
        print("GENERANDO WUs OPTIMIZADOS v4.0 (Basados en mejores resultados ULTIMATE)")
        print("="*80)
        print()
        
        conn = sqlite3.connect("coordinator.db")
        c = conn.cursor()
        
        created = []
        
        for i, strategy in enumerate(strategies, 1):
            name_escaped = strategy["name"].replace("'", "''")
            c.execute("SELECT id FROM work_units WHERE strategy_params LIKE '%" + name_escaped + "%'")
            existe = c.fetchone()
            
            if existe:
                print(f"   . [{i}/10] {strategy['name']}: Ya existe (WU #{existe[0]})")
                continue
            
            c.execute('''
                INSERT INTO work_units 
                (strategy_params, replicas_needed, status)
                VALUES (?, 2, 'pending')
            ''', (json.dumps(strategy),))
            
            wu_id = c.lastrowid
            created.append((wu_id, strategy['name']))
            
            print(f"   OK [{i}/10] {strategy['name']}: WU #{wu_id}")
            print(f"      Pop: {strategy['population_size']} | Gen: {strategy['generations']}")
        
        conn.commit()
        conn.close()
        
        print()
        print("="*80)
        print(f"SE HAN CREADO {len(created)} WUs OPTIMIZADOS")
        print("="*80)
        
        for wu_id, name in created:
            print(f"   WU #{wu_id}: {name}")
        
        return created

if __name__ == '__main__':
    print()
    generator = OptimizedWUGenerator()
    generator.create_wus()
