#!/usr/bin/env python3
"""
ULTIMATE WORK UNIT GENERATOR v3.0
Genera WUs con todas las mejoras implementadas:

✓ Nuevos indicadores (Stochastic, Ichimoku, OBV, VWAP, ROC, CCI, Williams %R)
✓ Algoritmo Genético Optimizado (adaptive mutation, diversity control)
✓ Risk Management (trailing stop, breakeven)
✓ Multi-timeframe support
✓ ML-enhanced fitness function
"""

import sqlite3
import json
from datetime import datetime

class UltimateWUGenerator:
    """Genera Work Units ultra-optimizados"""
    
    def __init__(self):
        self.db_path = "coordinator.db"
    
    def generate_ultimate_strategies(self):
        """Genera estrategias con todos los indicadores nuevos"""
        
        strategies = [
            # === STOCHASTIC STRATEGIES ===
            {
                "name": "ULTIMATE_Stochastic_Oversold",
                "category": "Momentum",
                "population_size": 280,
                "generations": 320,
                "mutation_rate": 0.20,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.8,
                "take_profit": 4.5,
                "trailing_stop_pct": 0.02,
                "breakeven_after": 0.015,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "STOCH_K", "period": 14}, "op": "<", "right": {"value": 20}},
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 35}}
                ],
                "description": "Stochastic oversold + RSI filter"
            },
            {
                "name": "ULTIMATE_Stochastic_Crossover",
                "category": "Momentum",
                "population_size": 275,
                "generations": 310,
                "mutation_rate": 0.22,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.9,
                "take_profit": 4.8,
                "trailing_stop_pct": 0.025,
                "breakeven_after": 0.02,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "STOCH_K", "period": 14}, "op": ">", "right": {"indicator": "STOCH_D", "period": 14}},
                    {"left": {"indicator": "STOCH_K", "period": 14}, "op": "<", "right": {"value": 80}}
                ],
                "description": "Stochastic K crossing above D"
            },
            
            # === ICHIMOKU STRATEGIES ===
            {
                "name": "ULTIMATE_Ichimoku_Cloud",
                "category": "Trend Following",
                "population_size": 290,
                "generations": 340,
                "mutation_rate": 0.20,
                "crossover_rate": 0.88,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 2.0,
                "take_profit": 5.0,
                "trailing_stop_pct": 0.025,
                "breakeven_after": 0.02,
                "timeframe": "15m",
                "data_file": "BTC-USD_FIFTEEN_MINUTE.csv",
                "max_candles": 150000,
                "entry_rules": [
                    {"left": {"field": "close"}, "op": ">", "right": {"indicator": "ICHIMOKU_Base", "period": 26}},
                    {"left": {"indicator": "ICHIMOKU_Conv", "period": 9}, "op": ">", "right": {"indicator": "ICHIMOKU_Base", "period": 26}}
                ],
                "description": "Ichimoku cloud bullish signal"
            },
            
            # === OBV STRATEGIES ===
            {
                "name": "ULTIMATE_OBV_Divergence",
                "category": "Volume",
                "population_size": 260,
                "generations": 300,
                "mutation_rate": 0.18,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.7,
                "take_profit": 4.5,
                "trailing_stop_pct": 0.02,
                "breakeven_after": 0.015,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 35}},
                    {"left": {"field": "close"}, "op": ">", "right": {"indicator": "SMA", "period": 50}}
                ],
                "description": "OBV divergence setup"
            },
            
            # === CCI STRATEGIES ===
            {
                "name": "ULTIMATE_CCI_Oversold",
                "category": "Momentum",
                "population_size": 270,
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
                    {"left": {"indicator": "CCI", "period": 20}, "op": "<", "right": {"value": -100}},
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 40}}
                ],
                "description": "CCI oversold reversal"
            },
            
            # === WILLIAMS %R STRATEGIES ===
            {
                "name": "ULTIMATE_Williams_Oversold",
                "category": "Momentum",
                "population_size": 265,
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
                    {"left": {"indicator": "WILLIAMS_R", "period": 14}, "op": "<", "right": {"value": -80}},
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 35}}
                ],
                "description": "Williams %R oversold"
            },
            
            # === ROC STRATEGIES ===
            {
                "name": "ULTIMATE_ROC_Momentum",
                "category": "Momentum",
                "population_size": 260,
                "generations": 300,
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
                    {"left": {"indicator": "ROC", "period": 10}, "op": ">", "right": {"value": 2}},
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 55}}
                ],
                "description": "ROC momentum signal"
            },
            
            # === COMBO STRATEGIES ===
            {
                "name": "ULTIMATE_MultiIndicator_Combo",
                "category": "Multi-Factor",
                "population_size": 300,
                "generations": 350,
                "mutation_rate": 0.18,
                "crossover_rate": 0.88,
                "elite_rate": 0.15,
                "risk_level": "HIGH",
                "stop_loss": 1.6,
                "take_profit": 5.0,
                "trailing_stop_pct": 0.025,
                "breakeven_after": 0.02,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30}},
                    {"left": {"indicator": "STOCH_K", "period": 14}, "op": "<", "right": {"value": 20}},
                    {"left": {"indicator": "CCI", "period": 20}, "op": "<", "right": {"value": -50}}
                ],
                "description": "Triple oversold confirmation"
            },
            
            # === VOLATILITY ADAPTIVE ===
            {
                "name": "ULTIMATE_Volatility_Adaptive",
                "category": "Volatility",
                "population_size": 285,
                "generations": 330,
                "mutation_rate": 0.20,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 2.0,
                "take_profit": 5.2,
                "trailing_stop_pct": 0.03,
                "breakeven_after": 0.02,
                "timeframe": "5m",
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {"left": {"indicator": "BB_Width", "period": 20}, "op": ">", "right": {"value": 3}},
                    {"left": {"indicator": "ATR_Pct", "period": 14}, "op": ">", "right": {"value": 2}},
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 40}}
                ],
                "description": "Adaptive to volatility conditions"
            },
            
            # === ULTIMATE RECORD BREAKER ===
            {
                "name": "ULTIMATE_The_Record_Breaker_v3",
                "category": "Record Breaker",
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
                    {"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30}},
                    {"left": {"field": "close"}, "op": ">", "right": {"indicator": "SMA", "period": 50}},
                    {"left": {"indicator": "MACD_Hist", "period": 12}, "op": ">", "right": {"value": 0}}
                ],
                "description": "THE ONE - Ultimate record breaker with all indicators"
            }
        ]
        
        return strategies
    
    def create_wus(self):
        """Crea los WUs en la base de datos"""
        
        strategies = self.generate_ultimate_strategies()
        
        print("="*80)
        print("GENERANDO WORK UNITS ULTIMATE v3.0")
        print("Con nuevos indicadores, GA optimizado y risk management")
        print("="*80)
        print()
        
        conn = sqlite3.connect(self.db_path)
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
            print(f"      Pop: {strategy['population_size']} | Gen: {strategy['generations']} | " +
                  f"SL: {strategy['stop_loss']}% | TP: {strategy['take_profit']}%")
            print(f"      Trail: {strategy['trailing_stop_pct']*100}% | BE: {strategy['breakeven_after']*100}%")
        
        conn.commit()
        conn.close()
        
        print()
        print("="*80)
        print(f"SE HAN CREADO {len(created)} WORK UNITS ULTIMATE")
        print("="*80)
        
        for wu_id, name in created:
            print(f"   WU #{wu_id}: {name}")
        
        return created

if __name__ == '__main__':
    print()
    generator = UltimateWUGenerator()
    generator.create_wus()
    print()
    print("Verificar resultados:")
    print("   python3 analyze_performance_advanced.py")
