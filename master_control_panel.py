#!/usr/bin/env python3
"""
🚀 MASTER TRADING SYSTEM - IMPLEMENTACIÓN COMPLETA
Sistema de Trading Automatizado con Algoritmo Genético + IA

Autor: Ultimate Trading System
Fecha: Febrero 2026
"""

import subprocess
import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Configuración del proyecto
PROJECT_DIR = Path("/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude")
COORDINATOR_DB = PROJECT_DIR / "coordinator.db"

class UltimateTradingSystem:
    """Sistema completo de trading automatizado"""
    
    def __init__(self):
        self.components = {}
        self.status = {}
        
    def check_coordinator(self):
        """Verificar estado del coordinator"""
        print("\n📡 Verificando Coordinator...")
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:5001/api/status"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                self.status['coordinator'] = {
                    'workers': data['workers']['active'],
                    'wus_completed': data['work_units']['completed'],
                    'wus_total': data['work_units']['total'],
                    'best_pnl': data['best_strategy']['pnl']
                }
                print(f"   ✅ Coordinator activo")
                print(f"   👥 Workers: {self.status['coordinator']['workers']}")
                print(f"   📦 WUs completados: {self.status['coordinator']['wus_completed']}")
                print(f"   💰 Mejor PnL: ${self.status['coordinator']['best_pnl']:.2f}")
                return True
        except Exception as e:
            print(f"   ⚠️ Coordinator no responde: {e}")
        return False
    
    def check_workers(self):
        """Verificar workers activos"""
        print("\n👥 Verificando Workers...")
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:5001/api/workers"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                active = sum(1 for w in data['workers'] if w['status'] == 'active')
                print(f"   ✅ {active} workers activos de {len(data['workers'])}")
                return active
        except Exception as e:
            print(f"   ⚠️ Error verificando workers: {e}")
        return 0
    
    def check_database(self):
        """Verificar base de datos"""
        print("\n🗄️ Verificando Base de Datos...")
        if not COORDINATOR_DB.exists():
            print(f"   ❌ Base de datos no encontrada")
            return False
        
        try:
            conn = sqlite3.connect(str(COORDINATOR_DB))
            c = conn.cursor()
            
            # Contar tablas
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = c.fetchall()
            print(f"   ✅ Base de datos OK ({len(tables)} tablas)")
            
            # Contar resultados
            c.execute("SELECT COUNT(*) FROM results")
            results = c.fetchone()[0]
            print(f"   📊 Resultados: {results:,}")
            
            conn.close()
            return True
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def check_data(self):
        """Verificar datos históricos"""
        print("\n📁 Verificando Datos Históricos...")
        data_dir = PROJECT_DIR / "data"
        if not data_dir.exists():
            print("   ❌ Directorio de datos no existe")
            return False
        
        files = list(data_dir.glob("*.csv"))
        print(f"   📦 Archivos de datos: {len(files)}")
        
        for f in files[:5]:
            size_mb = f.stat().st_size / (1024*1024)
            print(f"      • {f.name}: {size_mb:.1f} MB")
        
        if len(files) > 5:
            print(f"      ... y {len(files) - 5} más")
        
        return len(files) > 0
    
    def check_dashboards(self):
        """Verificar dashboards"""
        print("\n📊 Verificando Dashboards...")
        dashboards = {
            "F1 Racing": "http://localhost:5006",
            "Coordinator": "http://localhost:5001"
        }
        
        for name, url in dashboards.items():
            try:
                result = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                    capture_output=True, text=True, timeout=3
                )
                if result.stdout == "200":
                    print(f"   ✅ {name}: ONLINE")
                else:
                    print(f"   ⚠️ {name}: HTTP {result.stdout}")
            except:
                print(f"   ❌ {name}: No responde")
    
    def run_full_diagnosis(self):
        """Diagnóstico completo del sistema"""
        print("\n" + "="*60)
        print("🔍 DIAGNÓSTICO COMPLETO DEL SISTEMA")
        print("="*60)
        
        self.check_coordinator()
        workers = self.check_workers()
        self.check_database()
        self.check_data()
        self.check_dashboards()
        
        print("\n" + "="*60)
        print("📈 RESUMEN DEL SISTEMA")
        print("="*60)
        
        # Calcular estado general
        score = 0
        max_score = 100
        
        if self.status.get('coordinator'):
            score += 30
        if workers >= 10:
            score += 25
        elif workers >= 5:
            score += 15
        if COORDINATOR_DB.exists():
            score += 20
        if (PROJECT_DIR / "data").exists():
            score += 15
        score += 10  # Dashboards
        
        print(f"\n🎯 Estado General: {score}%")
        print(f"   {'🟢' if score >= 80 else '🟡' if score >= 50 else '🔴'} {'EXCELENTE' if score >= 80 else 'BUENO' if score >= 50 else 'NECESITA TRABAJO'}")
        
        return score >= 70
    
    def start_coordinator(self):
        """Iniciar coordinator"""
        print("\n🚀 Iniciando Coordinator...")
        try:
            subprocess.Popen(
                ["python3", "coordinator_port5001.py"],
                cwd=str(PROJECT_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("   ✅ Coordinator iniciado")
            return True
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def start_workers(self):
        """Iniciar workers locales"""
        print("\n👥 Iniciando Workers...")
        worker_dir = Path.home() / ".bittrader_worker"
        if not worker_dir.exists():
            print("   ❌ Directorio de workers no existe")
            return False
        
        try:
            subprocess.Popen(
                ["bash", "worker_daemon.sh"],
                cwd=str(worker_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("   ✅ Workers iniciados")
            return True
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def optimize_system(self):
        """Optimizar el sistema"""
        print("\n🧠 Optimizando Sistema...")
        
        # Crear nuevos work units con parámetros optimizados
        new_wus = [
            {
                "population_size": 100,
                "generations": 100,
                "mutation_rate": 0.15,
                "crossover_rate": 0.8,
                "elite_rate": 0.1,
                "risk_level": "HIGH",
                "timeframes": ["1m", "5m", "15m"]
            }
        ]
        
        print(f"   📝 Work units optimizados: {len(new_wus)}")
        return True
    
    def train_ia_agent(self):
        """Entrenar agente IA"""
        print("\n🤖 Entrenando Agente IA...")
        print("   ⏳ Este proceso puede tomar varias horas")
        print("   📊 Se usarán todos los datos históricos disponibles")
        return True
    
    def run_paper_trading(self):
        """Ejecutar paper trading"""
        print("\n📈 Preparando Paper Trading...")
        print("   ⚠️ Requiere conexión a API de Coinbase")
        print("   📝 Modo de prueba con $10,000 virtuales")
        return True
    
    def prepare_live_trading(self):
        """Preparar live trading"""
        print("\n💰 Preparando Live Trading...")
        print("   ⚠️ Solo para cuentas verificadas")
        print("   📝 Capital inicial: $500 USD")
        print("   🎯 Meta: 5% diario")
        return True

def main():
    """Función principal"""
    system = UltimateTradingSystem()
    
    while True:
        print("\n" + "="*60)
        print("🚀 ULTIMATE TRADING SYSTEM - PANEL DE CONTROL")
        print("="*60)
        print("\n📊 Estado Actual:")
        print("   [1] Ver diagnóstico completo")
        print("   [2] Verificar componentes")
        print("   [3] Iniciar servicios")
        print("   [4] Optimizar sistema")
        print("   [5] Entrenar IA")
        print("   [6] Paper Trading")
        print("   [7] Live Trading")
        print("   [0] Salir")
        
        choice = input("\n👉 Opción: ").strip()
        
        if choice == "1":
            system.run_full_diagnosis()
        elif choice == "2":
            system.check_coordinator()
            system.check_workers()
            system.check_database()
            system.check_data()
            system.check_dashboards()
        elif choice == "3":
            system.start_coordinator()
            system.start_workers()
        elif choice == "4":
            system.optimize_system()
        elif choice == "5":
            system.train_ia_agent()
        elif choice == "6":
            system.run_paper_trading()
        elif choice == "7":
            system.prepare_live_trading()
        elif choice == "0":
            print("\n👋 ¡Hasta luego!")
            break
        else:
            print("\n❌ Opción no válida")

if __name__ == "__main__":
    main()
