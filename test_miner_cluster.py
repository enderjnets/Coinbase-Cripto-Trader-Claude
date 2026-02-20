#!/usr/bin/env python3
"""
Test del Strategy Miner usando CLUSTER DISTRIBUIDO
- Usa HEAD (MacBook Pro: 12 CPUs) + Worker (MacBook Air: 9 CPUs) = 21+ CPUs
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
print("🧬 STRATEGY MINER - MODO CLUSTER DISTRIBUIDO")
print("="*80 + "\n")

if ray.is_initialized():
    ray.shutdown()
    time.sleep(1)

ray_address = os.getenv('RAY_ADDRESS', '100.77.179.14:6379')
print(f"🌐 Conectando al cluster: {ray_address}...\n")

ray.init(
    address=ray_address,
    ignore_reinit_error=True,
    logging_level="ERROR",
    _node_ip_address='100.118.215.73'
)

resources = ray.cluster_resources()
total_cpus = int(resources.get('CPU', 0))
nodes = ray.nodes()
active_nodes = [n for n in nodes if n['Alive']]

print(f"✅ Conectado al cluster Ray")
print(f"   📊 CPUs totales: {total_cpus}")
print(f"   🖥️  Nodos activos: {len(active_nodes)}\n")

print("📊 Cargando datos BTC...")
df_full = pd.read_csv("data/BTC-USD_FIVE_MINUTE.csv")
df = df_full.tail(25000).copy()
df.reset_index(drop=True, inplace=True)
print(f"   {len(df):,} velas cargadas\n")

optimal_pop = min((total_cpus // 10) * 10 or 50, 80)

print("⚙️  Configuración:")
print(f"   • Población: {optimal_pop}")
print(f"   • Generaciones: 25")
print(f"   • CPUs: {total_cpus}")
print(f"   • Tiempo estimado: 25-35 min\n")

miner = StrategyMiner(
    df=df,
    population_size=optimal_pop,
    generations=25,
    risk_level="MEDIUM",
    force_local=False
)

all_results = []
best_ever = {'pnl': -float('inf'), 'genome': None, 'gen': 0}

def show_progress(msg_type, data):
    global best_ever
    if msg_type == "START_GEN":
        print(f"\n{'='*60}\n🧬 Generación {data}/25\n{'='*60}")
    elif msg_type == "BEST_GEN":
        pnl = data.get('pnl', 0)
        trades = data.get('num_trades', 0)
        win_rate = data.get('win_rate', 0) * 100
        gen = data.get('gen', 0)
        
        emoji = "🔥🔥🔥" if pnl > 2000 else ("🔥🔥" if pnl > 1000 else ("🔥" if pnl > 500 else ("✅" if pnl > 0 else "⏳")))
        print(f"{emoji} PnL: ${pnl:>10,.2f} | Trades: {trades:>4d} | Win: {win_rate:>5.1f}%")
        
        all_results.append({'gen': gen, 'pnl': pnl, 'trades': trades, 'win_rate': win_rate, 'genome': data.get('genome')})
        
        if pnl > best_ever['pnl']:
            best_ever = {'pnl': pnl, 'genome': data.get('genome'), 'gen': gen, 'trades': trades, 'win_rate': win_rate}
            if pnl > 0:
                print(f"   🏆 NUEVO RÉCORD! (Gen {gen})")

print("="*80)
print("⚡ INICIANDO MINERÍA...")
print("="*80 + "\n")

start_time = time.time()
best_genome, best_pnl = miner.run(progress_callback=show_progress)
total_time = time.time() - start_time

print("\n" + "="*80)
print("🏆 RESULTADOS")
print("="*80 + "\n")

print(f"⏱️  Tiempo: {int(total_time/60)}m {int(total_time%60)}s")
print(f"💰 Mejor PnL: ${best_pnl:,.2f}\n")

if best_ever['pnl'] > 0:
    print(f"🎉 ¡ÉXITO! Estrategia rentable:")
    print(f"   PnL: ${best_ever['pnl']:,.2f}")
    print(f"   Gen: {best_ever['gen']}")
    print(f"   Trades: {best_ever['trades']}")
    print(f"   Win Rate: {best_ever['win_rate']:.1f}%\n")
    
    timestamp = int(time.time())
    result_file = f"BEST_STRATEGY_CLUSTER_{timestamp}.json"
    with open(result_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'pnl': best_ever['pnl'],
            'trades': best_ever['trades'],
            'win_rate': best_ever['win_rate'],
            'genome': best_ever['genome'],
            'generation': best_ever['gen'],
            'execution_time_seconds': total_time,
            'cluster_cpus': total_cpus
        }, f, indent=2)
    print(f"💾 Guardado: {result_file}\n")

print("📊 Evolución:")
for r in all_results:
    emoji = "🏆" if r['pnl'] == best_ever['pnl'] else ("✅" if r['pnl'] > 0 else "  ")
    print(f"   {r['gen']:>2d}  | ${r['pnl']:>9,.2f} | {r['trades']:>4d} | {r['win_rate']:>5.1f}% {emoji}")

profitable = len([r for r in all_results if r['pnl'] > 0])
print(f"\n📈 Rentables: {profitable}/25 ({(profitable/25)*100:.0f}%)\n")

print("="*80 + "\n")
ray.shutdown()
exit(0 if best_ever['pnl'] > 0 else 1)
