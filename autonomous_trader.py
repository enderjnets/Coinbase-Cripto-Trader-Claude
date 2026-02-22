#!/usr/bin/env python3
"""
🤖 AUTONOMOUS TRADING SYSTEM
=============================

Sistema completamente autónomo que:
1. Crea work units automáticamente
2. Analiza resultados
3. Optimiza estrategias
4. Busca 2-5% diario

Uso:
    python autonomous_trader.py --start
    python autonomous_trader.py --status
"""

import os
import sys
import time
import json
import sqlite3
import requests
import threading
import subprocess
from datetime import datetime
from typing import Dict, List
import argparse

PROJECT_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
COORDINATOR_URL = "http://localhost:5001"

# Objetivos
TARGET_DAILY_PCT = 3.0  # 3% objetivo
MIN_DAILY_PCT = 1.0     # Mínimo aceptable

# Configuración de WUs
WU_CONFIGS = [
    {
        "name": "BTC_MOMENTUM",
        "params": {
            "category": "Futures",
            "population_size": 30,
            "generations": 100,
            "risk_level": "HIGH",
            "stop_loss": 1.0,
            "take_profit": 5.0,
            "leverage": 3,
            "data_file": "BTC-USD_ONE_MINUTE.csv",
            "max_candles": 100000,
            "contracts": ["BIT-27FEB26-CDE", "BIP-20DEC30-CDE"]
        }
    },
    {
        "name": "ETH_MACD",
        "params": {
            "category": "Futures",
            "population_size": 30,
            "generations": 100,
            "risk_level": "MEDIUM",
            "stop_loss": 1.5,
            "take_profit": 4.0,
            "leverage": 2,
            "data_file": "ETH-USD_ONE_MINUTE.csv",
            "max_candles": 100000,
            "contracts": ["ET-27FEB26-CDE", "ETP-20DEC30-CDE"]
        }
    },
    {
        "name": "SOL_BREAKOUT",
        "params": {
            "category": "Futures",
            "population_size": 30,
            "generations": 100,
            "risk_level": "HIGH",
            "stop_loss": 1.0,
            "take_profit": 5.0,
            "leverage": 5,
            "data_file": "SOL-USD_ONE_MINUTE.csv",
            "max_candles": 100000,
            "contracts": ["SOL-27FEB26-CDE", "SLP-20DEC30-CDE"]
        }
    },
    {
        "name": "BTC_RSI_REVERSAL",
        "params": {
            "category": "Futures",
            "population_size": 40,
            "generations": 150,
            "risk_level": "MEDIUM",
            "stop_loss": 2.0,
            "take_profit": 6.0,
            "leverage": 2,
            "data_file": "BTC-USD_ONE_MINUTE.csv",
            "max_candles": 150000,
            "contracts": ["BIT-27FEB26-CDE"]
        }
    },
    {
        "name": "MULTI_COIN_AI",
        "params": {
            "category": "Futures",
            "population_size": 50,
            "generations": 200,
            "risk_level": "HIGH",
            "stop_loss": 1.0,
            "take_profit": 5.0,
            "leverage": 3,
            "data_file": "BTC-USD_ONE_MINUTE.csv",
            "max_candles": 200000,
            "contracts": ["BIT-27FEB26-CDE", "ET-27FEB26-CDE", "SOL-27FEB26-CDE"]
        }
    }
]


class AutonomousTrader:
    """Sistema de trading completamente autónomo."""
    
    def __init__(self):
        self.running = False
        self.last_check = 0
        self.check_interval = 30  # segundos
        self.results_history = []
        
        print("\n" + "="*60)
        print("🤖 AUTONOMOUS TRADING SYSTEM")
        print("="*60)
        print(f"   🎯 Objetivo: {TARGET_DAILY_PCT}% diario")
        print(f"   📊 Mínimo: {MIN_DAILY_PCT}% diario")
        print(f"   🔄 Check cada: {self.check_interval}s")
        print("="*60 + "\n")
    
    def get_status(self) -> Dict:
        """Obtiene estado del sistema."""
        try:
            r = requests.get(f"{COORDINATOR_URL}/api/status", timeout=10)
            return r.json()
        except:
            return {}
    
    def get_results(self, limit=10) -> List:
        """Obtiene últimos resultados."""
        try:
            r = requests.get(f"{COORDINATOR_URL}/api/results?limit={limit}", timeout=10)
            data = r.json()
            return data.get("results", [])[:limit]
        except:
            return []
    
    def create_wu(self, config: Dict) -> bool:
        """Crea una work unit."""
        try:
            conn = sqlite3.connect(f"{PROJECT_DIR}/coordinator.db")
            c = conn.cursor()
            
            c.execute('''
                INSERT INTO work_units (strategy_params, status, replicas_needed, replicas_completed, replicas_assigned, created_at)
                VALUES (?, ?, ?, 0, 0, datetime('now'))
            ''', (json.dumps(config), "pending", 2))
            
            conn.commit()
            conn.close()
            
            print(f"   ✅ WU creada: {config.get('name', 'Unknown')}")
            return True
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def analyze_results(self) -> Dict:
        """Analiza resultados para optimizar."""
        
        # Obtener últimos resultados
        results = self.get_results(50)
        
        if not results:
            return {"action": "create", "reason": "Sin resultados"}
        
        # Analizar performance
        total_pnl = sum(r.get("pnl", 0) for r in results)
        avg_pnl = total_pnl / len(results) if results else 0
        
        winning = [r for r in results if r.get("pnl", 0) > 0]
        win_rate = len(winning) / len(results) * 100 if results else 0
        
        # Mejores estrategias
        best_results = sorted(results, key=lambda x: x.get("pnl", 0), reverse=True)[:5]
        
        # Analizar parámetros de mejores resultados
        best_params = {}
        for r in best_results[:3]:
            strategy = r.get("strategy_genome", {})
            
            # Extraer parámetros clave
            for key in ["stop_loss", "take_profit", "leverage", "risk_level"]:
                if key in strategy:
                    best_params[key] = strategy[key]
        
        return {
            "action": "create" if len(results) < 10 else "optimize",
            "total_results": len(results),
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "win_rate": win_rate,
            "best_pnl": best_results[0].get("pnl", 0) if best_results else 0,
            "best_params": best_params
        }
    
    def should_create_new_wu(self) -> bool:
        """Determina si debe crear nuevas WUs."""
        
        status = self.get_status()
        
        pending = status.get("work_units", {}).get("pending", 0)
        in_progress = status.get("work_units", {}).get("in_progress", 0)
        
        # Siempre mantener al menos 3 WUs pendientes
        if pending < 3:
            return True
        
        return False
    
    def run_cycle(self):
        """Ejecuta un ciclo de análisis y creación."""
        
        print(f"\n🔄 [{datetime.now().strftime('%H:%M:%S')}] Ciclo de análisis...")
        
        # 1. Ver estado
        status = self.get_status()
        
        pending = status.get("work_units", {}).get("pending", 0)
        in_progress = status.get("work_units", {}).get("in_progress", 0)
        completed = status.get("work_units", {}).get("completed", 0)
        active_workers = status.get("workers", {}).get("active", 0)
        
        print(f"   📊 WUs: {pending} pend | {in_progress} proc | {completed} done")
        print(f"   👷 Workers: {active_workers}")
        
        # 2. Analizar resultados
        analysis = self.analyze_results()
        
        print(f"   📈 Análisis:")
        print(f"      Resultados: {analysis.get('total_results', 0)}")
        print(f"      Win Rate: {analysis.get('win_rate', 0):.1f}%")
        print(f"      Mejor PnL: ${analysis.get('best_pnl', 0):.2f}")
        
        # 3. Crear nuevas WUs si necesario
        created = 0
        
        while self.should_create_new_wu() and created < 3:
            # Elegir configuración
            config = WU_CONFIGS[created % len(WU_CONFIGS)]
            
            # Modificar ligeramente para diversidad
            wu_config = {
                "name": config["name"],
                "params": {**config["params"]}
            }
            
            # Añadir variación basada en mejores resultados
            if analysis.get("best_params"):
                wu_config["params"]["stop_loss"] = analysis["best_params"].get("stop_loss", wu_config["params"]["stop_loss"])
                wu_config["params"]["take_profit"] = analysis["best_params"].get("take_profit", wu_config["params"]["take_profit"])
            
            if self.create_wu(wu_config):
                created += 1
        
        if created > 0:
            print(f"   ✅ Creadas {created} nuevas WUs")
        
        return pending, in_progress
    
    def start(self):
        """Inicia el sistema autónomo."""
        
        self.running = True
        
        print("🤖 Sistema autónomo iniciado\n")
        
        while self.running:
            try:
                self.run_cycle()
                
                # Verificar si está corriendo el coordinator
                status = self.get_status()
                
                if not status:
                    print("⚠️ Coordinator no responde, intentando reconectar...")
                
                # Dormir
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Sistema detenido")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(10)
    
    def stop(self):
        """Detiene el sistema."""
        self.running = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", action="store_true", help="Iniciar sistema")
    parser.add_argument("--status", action="store_true", help="Ver estado")
    parser.add_argument("--create", type=int, default=0, help="Crear N work units")
    
    args = parser.parse_args()
    
    if args.status:
        # Solo mostrar estado
        r = requests.get(f"{COORDINATOR_URL}/api/status", timeout=10)
        status = r.json()
        
        print("\n" + "="*50)
        print("📊 ESTADO DEL SISTEMA")
        print("="*50)
        
        wu = status.get("work_units", {})
        print(f"\n📝 Work Units:")
        print(f"   Total: {wu.get('total', 0)}")
        print(f"   Pendientes: {wu.get('pending', 0)}")
        print(f"   En proceso: {wu.get('in_progress', 0)}")
        print(f"   Completadas: {wu.get('completed', 0)}")
        
        workers = status.get("workers", {})
        print(f"\n👷 Workers:")
        print(f"   Activos: {workers.get('active', 0)}")
        
        best = status.get("best_strategy", {})
        print(f"\n🏆 Mejor Estrategia:")
        print(f"   PnL: ${best.get('pnl', 0):.2f}")
        print(f"   Trades: {best.get('trades', 0)}")
        
        print("="*50)
        
        return
    
    if args.create > 0:
        # Crear work units
        trader = AutonomousTrader()
        
        for i in range(args.create):
            config = WU_CONFIGS[i % len(WU_CONFIGS)]
            trader.create_wu(config)
            time.sleep(0.5)
        
        print(f"\n✅ Creadas {args.create} work units")
        return
    
    # Modo autónomo
    trader = AutonomousTrader()
    trader.start()


if __name__ == "__main__":
    main()
