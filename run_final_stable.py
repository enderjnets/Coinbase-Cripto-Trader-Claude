#!/usr/bin/env python3
"""
Strategy Miner - VERSIÓN FINAL ESTABLE
Basado en test_miner_local.py que ya funciona
Optimizado para 6 CPUs y búsqueda de estrategias rentables
"""

import pandas as pd
from strategy_miner import StrategyMiner
import time
import ray
import json

print("\n" + "="*80)
print("🧬 STRATEGY MINER - VERSIÓN FINAL ESTABLE")
print("="*80 + "\n")

# Limpiar Ray anterior
if ray.is_initialized():
    print("Limpiando Ray anterior...")
    ray.shutdown()
    time.sleep(2)

print("💻 Inicializando Ray LOCAL (8 CPUs)...\n")

ray.init(
    address='local',
    num_cpus=8,  # 8 CPUs - balance velocidad/estabilidad
    ignore_reinit_error=True,
    logging_level="ERROR",
    include_dashboard=False
)

resources = ray.cluster_resources()
total_cpus = int(resources.get('CPU', 0))
print(f"✅ Ray inicializado - {total_cpus} CPUs disponibles\n")

# Cargar datos
print("📊 Cargando datos BTC...")
df = pd.read_csv("data/BTC-USD_FIVE_MINUTE.csv").tail(30000).copy()
df.reset_index(drop=True, inplace=True)
print(f"   {len(df):,} velas cargadas")
print(f"   Rango: {df.iloc[0]['timestamp']} -> {df.iloc[-1]['timestamp']}\n")

# Configuración optimizada para 8 CPUs
pop_size = 40  # 8 CPUs x 5 = buen balance
generations = 30

print("⚙️  Configuración:")
print(f"   Población: {pop_size} (optimizado para 8 CPUs)")
print(f"   Generaciones: {generations}")
print(f"   Risk Level: MEDIUM")
print(f"   Tiempo estimado: 35-45 minutos\n")

miner = StrategyMiner(
    df=df,
    population_size=pop_size,
    generations=generations,
    risk_level="MEDIUM",
    force_local=True
)

# Tracking
generation_best = []
best_ever = {'pnl': -999999}
start_time = time.time()

def show_progress(msg_type, data):
    global best_ever
    
    if msg_type == "START_GEN":
        gen = data
        elapsed = time.time() - start_time
        avg_time = elapsed / (gen + 1) if gen > 0 else 0
        remaining_mins = int(((generations - gen) * avg_time) / 60)
        
        print(f"\n{'='*70}")
        print(f"🧬 Generación {gen}/{generations} | Tiempo: {int(elapsed/60)}m | ETA: ~{remaining_mins}m")
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
        
        print(f"{emoji} PnL: ${pnl:>9,.2f} | Trades: {trades:>3d} | Win Rate: {win_rate:>5.1f}%", end="")
        
        generation_best.append({
            'gen': gen,
            'pnl': pnl,
            'trades': trades,
            'win_rate': win_rate,
            'genome': data.get('genome')
        })
        
        if pnl > best_ever['pnl']:
            best_ever = data
            best_ever['gen'] = gen
            if pnl > 0:
                print(" 🏆 RÉCORD!")
            else:
                print()
        else:
            print()

print("="*80)
print("⚡ INICIANDO MINERÍA...")
print("="*80)
print("ℹ️  Este proceso tomará ~45-60 minutos")
print("ℹ️  Los mejores resultados suelen aparecer después de la Gen 15\n")

best_genome, best_pnl = miner.run(progress_callback=show_progress)
total_time = time.time() - start_time

print("\n" + "="*80)
print("🏆 RESULTADOS FINALES")
print("="*80 + "\n")

print(f"⏱️  Tiempo Total: {int(total_time/60)}m {int(total_time%60)}s")
print(f"⚡ Velocidad: {int(total_time/generations)}s por generación")
print(f"💻 CPUs utilizados: {total_cpus}")
print(f"💰 Mejor PnL: ${best_pnl:,.2f}\n")

if best_ever['pnl'] > 0:
    print(f"🎉 ¡ÉXITO! Estrategia rentable encontrada!")
    print(f"   PnL Final: ${best_ever['pnl']:,.2f}")
    print(f"   Generación: {best_ever.get('gen', 0)}")
    print(f"   Trades: {best_ever.get('num_trades', 0)}")
    print(f"   Win Rate: {best_ever.get('win_rate', 0)*100:.1f}%\n")
    
    genome = best_ever.get('genome', {})
    print("📋 Estrategia Ganadora:")
    print(f"\n   Entry Rules ({len(genome.get('entry_rules', []))} reglas):")
    for i, rule in enumerate(genome.get('entry_rules', []), 1):
        left = rule.get('left', {})
        op = rule.get('op', '')
        right = rule.get('right', {})
        
        if 'field' in left:
            left_str = left['field']
        elif 'indicator' in left:
            left_str = f"{left['indicator']}({left.get('period', '?')})"
        else:
            left_str = str(left.get('value', '?'))
        
        if 'value' in right:
            right_str = str(right['value'])
        elif 'indicator' in right:
            right_str = f"{right['indicator']}({right.get('period', '?')})"
        elif 'field' in right:
            right_str = right['field']
        else:
            right_str = '?'
        
        print(f"      {i}. {left_str} {op} {right_str}")
    
    params = genome.get('params', {})
    print(f"\n   Risk Management:")
    print(f"      Stop Loss: {params.get('sl_pct', 0):.2%}")
    print(f"      Take Profit: {params.get('tp_pct', 0):.2%}\n")
    
    # Guardar resultado
    timestamp = int(time.time())
    result_file = f"BEST_STRATEGY_FINAL_{timestamp}.json"
    with open(result_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'mode': 'LOCAL_STABLE_FINAL',
            'cpus': total_cpus,
            'pnl': best_ever['pnl'],
            'trades': best_ever.get('num_trades'),
            'win_rate': best_ever.get('win_rate'),
            'genome': genome,
            'generation': best_ever.get('gen'),
            'execution_time_seconds': total_time,
            'config': {
                'population': pop_size,
                'generations': generations,
                'risk_level': 'MEDIUM'
            }
        }, f, indent=2)
    print(f"💾 Guardado: {result_file}\n")

else:
    print(f"⚠️  No se encontraron estrategias con PnL positivo")
    print(f"   Mejor PnL obtenido: ${best_ever['pnl']:,.2f}")
    print(f"   En generación: {best_ever.get('gen', 0)}\n")

# Estadísticas
print("📊 Top 10 Generaciones:")
sorted_gens = sorted(generation_best, key=lambda x: x['pnl'], reverse=True)[:10]
for i, g in enumerate(sorted_gens, 1):
    emoji = "🏆" if g['pnl'] == best_ever['pnl'] else ("✅" if g['pnl'] > 0 else "  ")
    print(f"{emoji} #{i:>2d} Gen {g['gen']:>2d} | ${g['pnl']:>9,.2f} | {g['trades']:>3d} trades | {g['win_rate']:>5.1f}%")

profitable = len([g for g in generation_best if g['pnl'] > 0])
avg_pnl = sum(g['pnl'] for g in generation_best) / len(generation_best)

print(f"\n📈 Estadísticas Generales:")
print(f"   Total generaciones: {generations}")
print(f"   Con PnL > 0: {profitable} ({profitable/generations*100:.0f}%)")
print(f"   PnL promedio: ${avg_pnl:,.2f}")
print(f"   Mejor: ${best_ever['pnl']:,.2f}")
print(f"   Peor: ${min(g['pnl'] for g in generation_best):,.2f}\n")

# Guardar histórico completo
all_file = f"all_strategies_final_{int(time.time())}.json"
with open(all_file, 'w') as f:
    json.dump({
        'execution_info': {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'mode': 'LOCAL_STABLE_FINAL',
            'cpus': total_cpus,
            'duration_seconds': total_time,
            'population': pop_size,
            'generations': generations
        },
        'best_strategy': best_ever,
        'all_generations': generation_best,
        'statistics': {
            'profitable_count': profitable,
            'success_rate': profitable/generations*100,
            'avg_pnl': avg_pnl,
            'best_pnl': best_ever['pnl'],
            'worst_pnl': min(g['pnl'] for g in generation_best)
        }
    }, f, indent=2)

print(f"💾 Histórico completo: {all_file}\n")
print("="*80 + "\n")

ray.shutdown()

exit_code = 0 if best_ever['pnl'] > 0 else 1
print(f"Terminado con código: {exit_code}\n")
exit(exit_code)
