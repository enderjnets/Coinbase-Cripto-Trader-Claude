#!/usr/bin/env python3
"""
Strategy Miner - Configuración ESTABLE para Cluster
HEAD: 12 CPUs (MacBook Pro)
Worker: 6 CPUs (MacBook Air) 
Total: 18 CPUs - Configuración balanceada y estable
"""

import pandas as pd
from strategy_miner import StrategyMiner
import time
import ray
import json
import os
from dotenv import load_dotenv

load_dotenv()

print("\n" + "="*80)
print("🧬 STRATEGY MINER - CLUSTER ESTABLE (18 CPUs)")
print("="*80 + "\n")

if ray.is_initialized():
    ray.shutdown()
    time.sleep(2)

ray_address = os.getenv('RAY_ADDRESS', '100.77.179.14:6379')
print(f"🌐 Conectando al cluster: {ray_address}...")

ray.init(
    address=ray_address,
    ignore_reinit_error=True,
    logging_level="ERROR",
    _node_ip_address='100.118.215.73'
)

resources = ray.cluster_resources()
total_cpus = int(resources.get('CPU', 0))

print(f"✅ Cluster conectado")
print(f"   CPUs: {total_cpus}")
print(f"   HEAD: 12 CPUs (MacBook Pro)")
print(f"   Worker: 6 CPUs (MacBook Air)\n")

# Cargar datos
print("📊 Cargando datos BTC...")
df_full = pd.read_csv("data/BTC-USD_FIVE_MINUTE.csv")
df = df_full.tail(25000).copy()
df.reset_index(drop=True, inplace=True)
print(f"   {len(df):,} velas cargadas\n")

# Configuración conservadora
pop_size = 36  # 18 CPUs x 2 = múltiplo perfecto
generations = 30

print("⚙️  Configuración ESTABLE:")
print(f"   Población: {pop_size}")
print(f"   Generaciones: {generations}")
print(f"   Risk: MEDIUM")
print(f"   Tiempo estimado: 35-45 min\n")

miner = StrategyMiner(
    df=df,
    population_size=pop_size,
    generations=generations,
    risk_level="MEDIUM",
    force_local=False
)

all_results = []
best_ever = {'pnl': -float('inf'), 'genome': None, 'gen': 0}
start_time = time.time()

def show_progress(msg_type, data):
    global best_ever
    
    if msg_type == "START_GEN":
        gen = data
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"🧬 Gen {gen}/{generations} | Tiempo: {int(elapsed/60)}m {int(elapsed%60)}s")
        print(f"{'='*60}")
    
    elif msg_type == "BEST_GEN":
        pnl = data.get('pnl', 0)
        trades = data.get('num_trades', 0)
        win_rate = data.get('win_rate', 0) * 100
        gen = data.get('gen', 0)
        
        emoji = "🔥🔥" if pnl > 1000 else ("🔥" if pnl > 500 else ("✅" if pnl > 0 else "⏳"))
        print(f"{emoji} PnL: ${pnl:>9,.2f} | Trades: {trades:>3d} | Win: {win_rate:>5.1f}%")
        
        all_results.append({
            'gen': gen, 'pnl': pnl, 'trades': trades, 
            'win_rate': win_rate, 'genome': data.get('genome')
        })
        
        if pnl > best_ever['pnl']:
            best_ever = {
                'pnl': pnl, 'genome': data.get('genome'), 'gen': gen,
                'trades': trades, 'win_rate': win_rate
            }
            if pnl > 0:
                print(f"   🏆 NUEVO RÉCORD!")

print("="*80)
print("⚡ INICIANDO MINERÍA ESTABLE...")
print("="*80 + "\n")

best_genome, best_pnl = miner.run(progress_callback=show_progress)
total_time = time.time() - start_time

print("\n" + "="*80)
print("🏆 RESULTADOS FINALES")
print("="*80 + "\n")

print(f"⏱️  Tiempo Total: {int(total_time/60)}m {int(total_time%60)}s")
print(f"⚡ Velocidad: {int(total_time/generations)}s/gen")
print(f"💰 Mejor PnL: ${best_pnl:,.2f}")
print(f"🌐 CPUs: 18 (12 HEAD + 6 Worker)\n")

if best_ever['pnl'] > 0:
    print(f"🎉 ÉXITO - Estrategia rentable encontrada!")
    print(f"   PnL: ${best_ever['pnl']:,.2f}")
    print(f"   Gen: {best_ever['gen']}")
    print(f"   Trades: {best_ever['trades']}")
    print(f"   Win Rate: {best_ever['win_rate']:.1f}%\n")
    
    timestamp = int(time.time())
    result_file = f"BEST_STRATEGY_STABLE_{timestamp}.json"
    with open(result_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'cluster_config': {'cpus': 18, 'head': 12, 'worker': 6},
            'pnl': best_ever['pnl'],
            'trades': best_ever['trades'],
            'win_rate': best_ever['win_rate'],
            'genome': best_ever['genome'],
            'generation': best_ever['gen'],
            'execution_time_seconds': total_time
        }, f, indent=2)
    print(f"💾 Guardado: {result_file}\n")
else:
    print(f"⚠️  No se encontraron estrategias rentables\n")

print("📊 Top 10 Generaciones:")
sorted_results = sorted(all_results, key=lambda x: x['pnl'], reverse=True)[:10]
for i, r in enumerate(sorted_results, 1):
    emoji = "🏆" if i == 1 else "✅"
    print(f"{emoji} #{i} Gen {r['gen']:>2d} | ${r['pnl']:>9,.2f} | {r['trades']:>3d} trades | {r['win_rate']:>5.1f}%")

profitable = len([r for r in all_results if r['pnl'] > 0])
print(f"\n📈 Estadísticas:")
print(f"   Rentables: {profitable}/{generations} ({(profitable/generations)*100:.0f}%)")
print(f"   Mejor PnL: ${best_ever['pnl']:,.2f}")
print(f"   Peor PnL: ${min(r['pnl'] for r in all_results):,.2f}\n")

print("="*80 + "\n")
ray.shutdown()
exit(0 if best_ever['pnl'] > 0 else 1)
