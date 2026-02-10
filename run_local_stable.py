#!/usr/bin/env python3
"""
Strategy Miner - Modo LOCAL ESTABLE
Ejecuta solo en MacBook Air con 6 CPUs
Configuración optimizada para estabilidad
"""

import pandas as pd
from strategy_miner import StrategyMiner
import time
import ray
import json

print("\n" + "="*80)
print("🧬 STRATEGY MINER - MODO LOCAL ESTABLE (6 CPUs)")
print("="*80 + "\n")

if ray.is_initialized():
    ray.shutdown()
    time.sleep(2)

print("💻 Inicializando Ray LOCAL con 6 CPUs...\n")

ray.init(
    address='local',
    num_cpus=6,
    ignore_reinit_error=True,
    logging_level="ERROR",
    include_dashboard=False
)

resources = ray.cluster_resources()
total_cpus = int(resources.get('CPU', 0))
print(f"✅ Ray inicializado - {total_cpus} CPUs\n")

# Cargar datos
print("📊 Cargando datos BTC...")
df_full = pd.read_csv("data/BTC-USD_FIVE_MINUTE.csv")
df = df_full.tail(25000).copy()
df.reset_index(drop=True, inplace=True)
print(f"   {len(df):,} velas cargadas\n")

# Configuración balanceada para 6 CPUs
pop_size = 30  # 6 CPUs x 5 = buen balance
generations = 35

print("⚙️  Configuración:")
print(f"   Población: {pop_size}")
print(f"   Generaciones: {generations}")
print(f"   Risk: MEDIUM")
print(f"   Modo: LOCAL")
print(f"   Tiempo est: 40-60 min\n")

miner = StrategyMiner(
    df=df,
    population_size=pop_size,
    generations=generations,
    risk_level="MEDIUM",
    force_local=True
)

all_results = []
best_ever = {'pnl': -float('inf'), 'genome': None, 'gen': 0}
start_time = time.time()

def show_progress(msg_type, data):
    global best_ever
    
    if msg_type == "START_GEN":
        gen = data
        elapsed = time.time() - start_time
        avg_time = elapsed / (gen + 1) if gen > 0 else 0
        remaining = (generations - gen) * avg_time
        print(f"\n{'='*70}")
        print(f"🧬 Gen {gen}/{generations} | Tiempo: {int(elapsed/60)}m | ETA: {int(remaining/60)}m")
        print(f"{'='*70}")
    
    elif msg_type == "BEST_GEN":
        pnl = data.get('pnl', 0)
        trades = data.get('num_trades', 0)
        win_rate = data.get('win_rate', 0) * 100
        gen = data.get('gen', 0)
        
        if pnl > 2000:
            emoji = "🔥🔥🔥"
        elif pnl > 1000:
            emoji = "🔥🔥"
        elif pnl > 500:
            emoji = "🔥"
        elif pnl > 0:
            emoji = "✅"
        else:
            emoji = "⏳"
        
        print(f"{emoji} PnL: ${pnl:>9,.2f} | Trades: {trades:>3d} | Win: {win_rate:>5.1f}%", end="")
        
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
                print(" 🏆 RÉCORD!")
            else:
                print()
        else:
            print()

print("="*80)
print("⚡ INICIANDO MINERÍA...")
print("="*80 + "\n")

best_genome, best_pnl = miner.run(progress_callback=show_progress)
total_time = time.time() - start_time

print("\n" + "="*80)
print("🏆 RESULTADOS FINALES")
print("="*80 + "\n")

print(f"⏱️  Tiempo: {int(total_time/60)}m {int(total_time%60)}s")
print(f"⚡ Velocidad: {int(total_time/generations)}s/gen")
print(f"💻 CPUs: {total_cpus}")
print(f"💰 Mejor PnL: ${best_pnl:,.2f}\n")

if best_ever['pnl'] > 0:
    print(f"🎉 ¡ÉXITO! Estrategia rentable encontrada!")
    print(f"   PnL: ${best_ever['pnl']:,.2f}")
    print(f"   Generación: {best_ever['gen']}")
    print(f"   Trades: {best_ever['trades']}")
    print(f"   Win Rate: {best_ever['win_rate']:.1f}%\n")
    
    genome = best_ever['genome']
    print("📋 Reglas de Entrada:")
    for i, rule in enumerate(genome.get('entry_rules', []), 1):
        left = rule.get('left', {})
        op = rule.get('op', '')
        right = rule.get('right', {})
        
        left_str = left.get('field') or f"{left.get('indicator')}({left.get('period')})"
        right_str = str(right.get('value')) if 'value' in right else f"{right.get('indicator')}({right.get('period')})"
        
        print(f"   {i}. {left_str} {op} {right_str}")
    
    params = genome.get('params', {})
    print(f"\n   Risk Management:")
    print(f"   • Stop Loss: {params.get('sl_pct', 0):.2%}")
    print(f"   • Take Profit: {params.get('tp_pct', 0):.2%}\n")
    
    timestamp = int(time.time())
    result_file = f"BEST_STRATEGY_LOCAL_{timestamp}.json"
    with open(result_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'mode': 'LOCAL_STABLE',
            'cpus': total_cpus,
            'pnl': best_ever['pnl'],
            'trades': best_ever['trades'],
            'win_rate': best_ever['win_rate'],
            'genome': best_ever['genome'],
            'generation': best_ever['gen'],
            'execution_time_seconds': total_time,
            'population_size': pop_size,
            'total_generations': generations
        }, f, indent=2)
    print(f"💾 Guardado: {result_file}\n")
else:
    print(f"⚠️  No se encontraron estrategias rentables\n")

print("📊 Top 10 Generaciones:")
sorted_results = sorted(all_results, key=lambda x: x['pnl'], reverse=True)[:10]
for i, r in enumerate(sorted_results, 1):
    emoji = "🏆" if i == 1 else ("✅" if r['pnl'] > 0 else "  ")
    print(f"{emoji} #{i:>2d} Gen {r['gen']:>2d} | ${r['pnl']:>9,.2f} | {r['trades']:>3d} trades | {r['win_rate']:>5.1f}%")

profitable = len([r for r in all_results if r['pnl'] > 0])
avg_pnl = sum(r['pnl'] for r in all_results) / len(all_results)

print(f"\n📈 Estadísticas Completas:")
print(f"   Total generaciones: {generations}")
print(f"   Rentables: {profitable} ({(profitable/generations)*100:.0f}%)")
print(f"   Mejor PnL: ${best_ever['pnl']:,.2f}")
print(f"   PnL promedio: ${avg_pnl:,.2f}")
print(f"   Peor PnL: ${min(r['pnl'] for r in all_results):,.2f}\n")

# Guardar todo
all_file = f"all_strategies_local_{int(time.time())}.json"
with open(all_file, 'w') as f:
    json.dump({
        'config': {
            'mode': 'LOCAL_STABLE',
            'cpus': total_cpus,
            'population': pop_size,
            'generations': generations,
            'execution_time': total_time
        },
        'best': best_ever,
        'all_results': all_results,
        'stats': {
            'profitable': profitable,
            'success_rate': (profitable/generations)*100,
            'avg_pnl': avg_pnl
        }
    }, f, indent=2)

print(f"💾 Histórico completo: {all_file}\n")
print("="*80 + "\n")

ray.shutdown()
exit(0 if best_ever['pnl'] > 0 else 1)
