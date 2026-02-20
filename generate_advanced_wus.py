#!/usr/bin/env python3
"""
🚀 ADVANCED WORK UNIT GENERATOR v2.0
Genera Work Units optimizados usando indicadores avanzados (MACD, ATR, BB, ADX)

Objetivo: Superar el récord de PnL de $443.99

Estrategias:
1. MACD Crossover + RSI Filter
2. Bollinger Band Bounce + ATR SL/TP
3. ADX Trend Filter + RSI Entry
4. MACD + BB Confluence
5. ATR Volatility-adaptive entries

Uso: python3 generate_advanced_wus.py
"""

import sqlite3
import json
import os
from datetime import datetime

class AdvancedWUGenerator:
    """
    Genera Work Units avanzados para superar el récord de $443.99
    """
    
    def __init__(self):
        self.db_path = "coordinator.db"
        self.records_file = "advanced_wu_records.json"
        
    def get_advanced_strategies(self):
        """
        Define estrategias avanzadas basadas en análisis de las top performers.
        Los mejores resultados tenían: population=200-300, generations=200-350, risk=HIGH
        """
        
        strategies = [
            # === ESTRATEGIA 1: MACD Master ===
            {
                "name": "MACD_Master_v2",
                "category": "Trend Following",
                "population_size": 280,
                "generations": 320,
                "mutation_rate": 0.20,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.8,
                "take_profit": 4.5,
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {
                        "left": {"indicator": "MACD", "period": 14},
                        "op": ">",
                        "right": {"indicator": "MACD_Signal", "period": 14}
                    },
                    {
                        "left": {"indicator": "RSI", "period": 14},
                        "op": "<",
                        "right": {"value": 70}
                    }
                ],
                "description": "MACD crossover con filtro RSI"
            },
            
            # === ESTRATEGIA 2: Bollinger Band Pro ===
            {
                "name": "BB_Pro_v2",
                "category": "Mean Reversion",
                "population_size": 260,
                "generations": 300,
                "mutation_rate": 0.22,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.5,
                "take_profit": 4.8,
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {
                        "left": {"indicator": "BB_Position", "period": 20},
                        "op": "<",
                        "right": {"value": 20}
                    },
                    {
                        "left": {"indicator": "RSI", "period": 14},
                        "op": "<",
                        "right": {"value": 40}
                    }
                ],
                "description": "BB oversold + RSI filter"
            },
            
            # === ESTRATEGIA 3: ADX Trend Master ===
            {
                "name": "ADX_Trend_Master",
                "category": "Trend Following",
                "population_size": 275,
                "generations": 325,
                "mutation_rate": 0.20,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.9,
                "take_profit": 4.6,
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {
                        "left": {"indicator": "ADX", "period": 14},
                        "op": ">",
                        "right": {"value": 25}
                    },
                    {
                        "left": {"indicator": "DI_Plus", "period": 14},
                        "op": ">",
                        "right": {"indicator": "DI_Minus", "period": 14}
                    }
                ],
                "description": "Strong trend detection with ADX"
            },
            
            # === ESTRATEGIA 4: MACD + BB Confluence ===
            {
                "name": "MACD_BB_Confluence",
                "category": "Confluence",
                "population_size": 290,
                "generations": 350,
                "mutation_rate": 0.18,
                "crossover_rate": 0.88,
                "elite_rate": 0.15,
                "risk_level": "HIGH",
                "stop_loss": 1.7,
                "take_profit": 5.0,
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {
                        "left": {"indicator": "MACD", "period": 14},
                        "op": ">",
                        "right": {"value": 0}
                    },
                    {
                        "left": {"indicator": "BB_Position", "period": 20},
                        "op": "<",
                        "right": {"value": 30}
                    },
                    {
                        "left": {"indicator": "ATR_Pct", "period": 14},
                        "op": "<",
                        "right": {"value": 3}
                    }
                ],
                "description": "MACD + BB + ATR low volatility filter"
            },
            
            # === ESTRATEGIA 5: ATR Adaptive ===
            {
                "name": "ATR_Adaptive_Strategy",
                "category": "Volatility Adaptive",
                "population_size": 300,
                "generations": 350,
                "mutation_rate": 0.20,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 2.0,
                "take_profit": 5.0,
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {
                        "left": {"indicator": "ATR_Pct", "period": 14},
                        "op": ">",
                        "right": {"value": 1.5}
                    },
                    {
                        "left": {"indicator": "RSI", "period": 14},
                        "op": "<",
                        "right": {"value": 65}
                    },
                    {
                        "left": {"indicator": "MACD_Hist", "period": 14},
                        "op": ">",
                        "right": {"value": 0}
                    }
                ],
                "description": "Trade only in volatile conditions with ATR filter"
            },
            
            # === ESTRATEGIA 6: Triple Indicator Combo ===
            {
                "name": "Triple_Combo_v2",
                "category": "Multi-Factor",
                "population_size": 285,
                "generations": 340,
                "mutation_rate": 0.22,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 1.6,
                "take_profit": 4.8,
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {
                        "left": {"indicator": "RSI", "period": 14},
                        "op": "<",
                        "right": {"value": 35}
                    },
                    {
                        "left": {"indicator": "MACD_Signal", "period": 14},
                        "op": ">",
                        "right": {"indicator": "MACD", "period": 14}
                    },
                    {
                        "left": {"indicator": "ADX", "period": 14},
                        "op": ">",
                        "right": {"value": 20}
                    }
                ],
                "description": "RSI oversold + MACD bullish + ADX trending"
            },
            
            # === ESTRATEGIA 7: Scalping 1min BB ===
            {
                "name": "Scalping_BB_1min",
                "category": "Scalping",
                "population_size": 250,
                "generations": 280,
                "mutation_rate": 0.25,
                "crossover_rate": 0.80,
                "elite_rate": 0.10,
                "risk_level": "HIGH",
                "stop_loss": 1.2,
                "take_profit": 3.0,
                "data_file": "BTC-USD_ONE_MINUTE.csv",
                "max_candles": 500000,
                "entry_rules": [
                    {
                        "left": {"indicator": "BB_Width", "period": 20},
                        "op": ">",
                        "right": {"value": 3}
                    },
                    {
                        "left": {"indicator": "BB_Position", "period": 20},
                        "op": "<",
                        "right": {"value": 15}
                    }
                ],
                "description": "Quick scalps on BB squeeze + bounce"
            },
            
            # === ESTRATEGIA 8: Volume Profile Advanced ===
            {
                "name": "Volume_Profile_Advanced",
                "category": "Volume Profile",
                "population_size": 300,
                "generations": 400,
                "mutation_rate": 0.18,
                "crossover_rate": 0.90,
                "elite_rate": 0.15,
                "risk_level": "HIGH",
                "stop_loss": 1.8,
                "take_profit": 5.5,
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 250000,
                "entry_rules": [
                    {
                        "left": {"indicator": "RSI", "period": 7},
                        "op": "<",
                        "right": {"value": 30}
                    },
                    {
                        "left": {"indicator": "MACD_Hist", "period": 12},
                        "op": ">",
                        "right": {"value": -1}
                    },
                    {
                        "left": {"indicator": "ATR_Pct", "period": 14},
                        "op": "<",
                        "right": {"value": 4}
                    }
                ],
                "description": "Fast RSI reversal + MACD confirmation"
            },
            
            # === ESTRATEGIA 9: Precision Entry ===
            {
                "name": "Precision_Entry_v2",
                "category": "Precision",
                "population_size": 320,
                "generations": 380,
                "mutation_rate": 0.15,
                "crossover_rate": 0.90,
                "elite_rate": 0.18,
                "risk_level": "HIGH",
                "stop_loss": 1.5,
                "take_profit": 6.0,
                "data_file": "BTC-USD_FIVE_MINUTE.csv",
                "max_candles": 200000,
                "entry_rules": [
                    {
                        "left": {"indicator": "BB_Position", "period": 20},
                        "op": "<",
                        "right": {"value": 5}
                    },
                    {
                        "left": {"indicator": "RSI", "period": 14},
                        "op": "<",
                        "right": {"value": 25}
                    },
                    {
                        "left": {"indicator": "DI_Plus", "period": 14},
                        "op": ">",
                        "right": {"indicator": "DI_Minus", "period": 14}
                    }
                ],
                "description": "Extreme oversold with bullish DI crossover"
            },
            
            # === ESTRATEGIA 10: The Breaker (Reversal) ===
            {
                "name": "The_Breaker_Reversal",
                "category": "Reversal",
                "population_size": 275,
                "generations": 350,
                "mutation_rate": 0.22,
                "crossover_rate": 0.85,
                "elite_rate": 0.12,
                "risk_level": "HIGH",
                "stop_loss": 2.0,
                "take_profit": 5.0,
                "data_file": "BTC-USD_FIFTEEN_MINUTE.csv",
                "max_candles": 150000,
                "entry_rules": [
                    {
                        "left": {"indicator": "RSI", "period": 14},
                        "op": "<",
                        "right": {"value": 20}
                    },
                    {
                        "left": {"indicator": "MACD", "period": 14},
                        "op": "<",
                        "right": {"indicator": "MACD_Signal", "period": 14}
                    },
                    {
                        "left": {"indicator": "BB_Position", "period": 20},
                        "op": "<",
                        "right": {"value": 10}
                    }
                ],
                "description": "Triple confirmation reversal setup"
            }
        ]
        
        return strategies
    
    def create_work_units(self):
        """Crea work units avanzados en la base de datos"""
        
        strategies = self.get_advanced_strategies()
        
        print("\n" + "="*70)
        print("🚀 GENERANDO WORK UNITS AVANZADOS v2.0")
        print("="*70)
        print(f"\n📊 Estrategias a crear: {len(strategies)}")
        print(f"🎯 Objetivo: Superar $443.99 PnL\n")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        wus_creados = []
        
        for i, strategy in enumerate(strategies, 1):
            # Verificar si ya existe estrategia similar
            c.execute('SELECT id, strategy_params FROM work_units WHERE strategy_params LIKE ?', 
                     (f'%{strategy["name"]}%',))
            existe = c.fetchone()
            
            if existe:
                print(f"   ⏭️ [{i}/{len(strategies)}] {strategy['name']}: Ya existe (WU #{existe[0]})")
                continue
            
            # Crear WU
            c.execute('''
                INSERT INTO work_units 
                (strategy_params, replicas_needed, status)
                VALUES (?, 2, 'pending')
            ''', (json.dumps(strategy),))
            
            wu_id = c.lastrowid
            wus_creados.append((wu_id, strategy['name'], strategy['category']))
            
            print(f"   ✅ [{i}/{len(strategies)}] {strategy['name']}: WU #{wu_id}")
            print(f"      📈 Pop: {strategy['population_size']} | Gen: {strategy['generations']} | " +
                  f"SL: {strategy['stop_loss']}% | TP: {strategy['take_profit']}%")
        
        conn.commit()
        conn.close()
        
        # Resumen
        print("\n" + "="*70)
        print(f"✅ {len(wus_creados)} Work Units Avanzados creados")
        print("="*70)
        
        for wu_id, name, category in wus_creados:
            print(f"   WU #{wu_id}: {name} ({category})")
        
        return wus_creados
    
    def analyze_current_records(self):
        """Analiza los Work Units actuales para entender qué parámetros funcionan"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        print("\n" + "="*70)
        print("📊 ANÁLISIS DE WORK UNITS EXISTENTES")
        print("="*70)
        
        # Top performers
        c.execute('''
            SELECT r.pnl, r.trades, r.win_rate, w.strategy_params
            FROM results r
            JOIN work_units w ON r.work_unit_id = w.id
            WHERE r.pnl > 400
            ORDER BY r.pnl DESC
            LIMIT 10
        ''')
        
        print("\n🏆 TOP 10 ESTRATEGIAS GANADORAS:")
        print("-" * 70)
        
        for row in c.fetchall():
            params = json.loads(row[3])
            print(f"\n💰 PnL: ${row[0]:,.2f}")
            print(f"   Trades: {row[1]} | Win Rate: {row[2]:.1%}")
            print(f"   Name: {params.get('name', 'Unknown')}")
            print(f"   Pop: {params.get('population_size', 'N/A')} | Gen: {params.get('generations', 'N/A')}")
            print(f"   SL: {params.get('stop_loss', 'N/A')} | TP: {params.get('take_profit', 'N/A')}")
            print(f"   Risk: {params.get('risk_level', 'N/A')}")
        
        conn.close()

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 ADVANCED WORK UNIT GENERATOR v2.0")
    print("   Objetivo: Superar $443.99 PnL")
    print("="*70 + "\n")
    
    generator = AdvancedWUGenerator()
    
    # Analizar estado actual
    generator.analyze_current_records()
    
    # Crear nuevos WUs
    wus = generator.create_work_units()
    
    print(f"\n📝 Resumen:")
    print(f"   WUs creados: {len(wus)}")
    print(f"   Listos para procesar por los 18 workers activos")
    print(f"\n💡 Próximos pasos:")
    print(f"   1. Ejecutar: python3 admin_server.py")
    print(f"   2. Verificar en: http://localhost:5000")
    print(f"   3. Monitorear resultados de PnL")
