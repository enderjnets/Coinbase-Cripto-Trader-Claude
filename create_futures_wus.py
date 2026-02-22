#!/usr/bin/env python3
"""
📝 Creador de Work Units para Futuros
=====================================

Crea work units específicas para optimizar estrategias de futuros.

Uso:
    python create_futures_wus.py
    python create_futures_wus.py --pop 30 --gen 50
"""

import requests
import json
import argparse

COORDINATOR_URL = "http://localhost:5001"

# Configuración de Work Units para Futuros
FUTURES_WU_CONFIGS = [
    {
        "name": "BTC_FUTURES_MOMENTUM",
        "params": {
            "population_size": 20,
            "generations": 50,
            "risk_level": "HIGH",
            "data_file": "BTC-USD_ONE_MINUTE.csv",
            "max_candles": 50000,
            "strategy_type": "momentum",
            "contracts": ["BIT-27FEB26-CDE", "BIP-20DEC30-CDE"],
            "leverage": 3
        }
    },
    {
        "name": "ETH_FUTURES_MEAN_REV",
        "params": {
            "population_size": 20,
            "generations": 50,
            "risk_level": "MEDIUM",
            "data_file": "ETH-USD_ONE_MINUTE.csv",
            "max_candles": 50000,
            "strategy_type": "mean_reversion",
            "contracts": ["ET-27FEB26-CDE", "ETP-20DEC30-CDE"],
            "leverage": 2
        }
    },
    {
        "name": "SOL_FUTURES_BREAKOUT",
        "params": {
            "population_size": 20,
            "generations": 50,
            "risk_level": "HIGH",
            "data_file": "SOL-USD_ONE_MINUTE.csv",
            "max_candles": 50000,
            "strategy_type": "breakout",
            "contracts": ["SOL-27FEB26-CDE", "SLP-20DEC30-CDE"],
            "leverage": 5
        }
    },
    {
        "name": "MULTI_COIN_MACD",
        "params": {
            "population_size": 30,
            "generations": 100,
            "risk_level": "MEDIUM",
            "data_file": "BTC-USD_ONE_MINUTE.csv",
            "max_candles": 100000,
            "strategy_type": "macd_cross",
            "contracts": ["BIT-27FEB26-CDE", "ET-27FEB26-CDE", "SOL-27FEB26-CDE"],
            "leverage": 3
        }
    },
    {
        "name": "AGGRESSIVE_5X",
        "params": {
            "population_size": 25,
            "generations": 75,
            "risk_level": "HIGH",
            "data_file": "BTC-USD_ONE_MINUTE.csv",
            "max_candles": 75000,
            "strategy_type": "combined",
            "contracts": ["BIT-27FEB26-CDE", "BIP-20DEC30-CDE", "ETP-20DEC30-CDE"],
            "leverage": 5
        }
    },
]


def create_work_unit(config, replicas=2):
    """Crea una work unit."""
    
    data = {
        "strategy_params": config["params"],
        "replicas": replicas,
        "name": config["name"]
    }
    
    try:
        response = requests.post(
            f"{COORDINATOR_URL}/api/create_work_unit",
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ {config['name']}: {result.get('id', 'OK')}")
            return result
        else:
            print(f"   ❌ {config['name']}: Error {response.status_code}")
            return None
    
    except Exception as e:
        print(f"   ❌ {config['name']}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pop", type=int, default=20, help="Population size")
    parser.add_argument("--gen", type=int, default=50, help="Generations")
    parser.add_argument("--replicas", type=int, default=2, help="Replicas")
    parser.add_argument("--count", type=int, default=5, help="Number of WUs")
    
    args = parser.parse_args()
    
    print("\n" + "="*50)
    print("📝 CREANDO WORK UNITS PARA FUTUROS")
    print("="*50)
    print(f"   Population: {args.pop}")
    print(f"   Generations: {args.gen}")
    print(f"   Replicas: {args.replicas}")
    print()
    
    # Verificar coordinator
    try:
        r = requests.get(f"{COORDINATOR_URL}/api/status", timeout=5)
        status = r.json()
        print(f"📊 Estado actual:")
        print(f"   Work Units: {status['work_units']['total']} total, {status['work_units']['pending']} pending")
        print(f"   Workers: {status['workers']['active']} activos")
        print()
    except:
        print("❌ Coordinator no está corriendo")
        return
    
    # Crear WUs
    created = 0
    
    for i, config in enumerate(FUTURES_WU_CONFIGS[:args.count]):
        # Actualizar parámetros
        config["params"]["population_size"] = args.pop
        config["params"]["generations"] = args.gen
        
        print(f"Creando WU {i+1}/{args.count}...")
        
        result = create_work_unit(config, args.replicas)
        
        if result:
            created += 1
        
        import time
        time.sleep(1)
    
    print(f"\n✅ Creadas {created} work units")
    
    # Verificar
    r = requests.get(f"{COORDINATOR_URL}/api/status")
    status = r.json()
    
    print(f"\n📊 Nuevo estado:")
    print(f"   Total: {status['work_units']['total']}")
    print(f"   Pending: {status['work_units']['pending']}")
    print(f"   In Progress: {status['work_units']['in_progress']}")
    print("="*50)


if __name__ == "__main__":
    main()
