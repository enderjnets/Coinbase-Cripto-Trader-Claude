#!/usr/bin/env python3
"""
Test del Strategy Miner con parámetros optimizados para generar estrategias RENTABLES
- Mayor población
- Más generaciones
- Riesgo MEDIUM para permitir más trades
- Dataset más pequeño para acelerar iteraciones
"""

import pandas as pd
from strategy_miner import StrategyMiner
import time
import ray
import os
import json

print("\n" + "="*80)
print("🧬 STRATEGY MINER - BÚSQUEDA DE ESTRATEGIAS RENTABLES")
print("="*80 + "\n")

# Inicializar Ray LOCAL
if ray.is_initialized():
    ray.shutdown()
    time.sleep(1)

cores = os.cpu_count() or 10
print(f"💻 Inicializando Ray LOCAL con {cores} CPUs...\n")

ray.init(
    address='local',
    num_cpus=cores,
    ignore_reinit_error=True,
    logging_level="ERROR",
    include_dashboard=False
)

resources = ray.cluster_resources()
total_cpus = int(resources.get('CPU', 0))
print(f"✅ Ray inicializado - {total_cpus} CPUs disponibles\n")

# 1. Cargar datos - USAR SUBSET MÁS RECIENTE (últimos 3 meses)
print("📊 Cargando datos...")
df_full = pd.read_csv("data/BTC-USD_FIVE_MINUTE.csv")

# Tomar solo los últimos 3 meses (aproximadamente 25,920 velas de 5 min)
df = df_full.tail(25000).copy()
df.reset_index(drop=True, inplace=True)

print(f"   Dataset: {len(df):,} velas (últimos 3 meses aprox)")
print(f"   Rango: {df.iloc[0]['timestamp']} -> {df.iloc[-1]['timestamp']}\n")

# 2. Configurar miner - PARÁMETROS AGRESIVOS
print("⚙️  Configuración PRODUCTIVA:")
print(f"   • Población: 50 (más diversidad)")
print(f"   • Generaciones: 20 (más evolución)")
print(f"   • Risk Level: MEDIUM (permite más trades)")
print(f"   • CPUs: {total_cpus}")
print(f"   • Tiempo estimado: ~40-60 minutos\n")

miner = StrategyMiner(
    df=df,
    population_size=50,
    generations=20,
    risk_level="MEDIUM",  # MEDIUM permite SL y TP más amplios
    force_local=True
)

# 3. Callback mejorado
all_results = []
best_ever = {'pnl': -float('inf'), 'genome': None, 'gen': 0}

def show_progress(msg_type, data):
    global best_ever

    if msg_type == "START_GEN":
        gen = data
        print(f"\n{'='*60}")
        print(f"🧬 Generación {gen}/20")
        print(f"{'='*60}")

    elif msg_type == "BEST_GEN":
        pnl = data.get('pnl', 0)
        trades = data.get('num_trades', 0)
        win_rate = data.get('win_rate', 0) * 100
        gen = data.get('gen', 0)

        # Determinar emoji según resultado
        if pnl > 2000:
            emoji = "🔥🔥🔥"
        elif pnl > 1000:
            emoji = "🔥🔥"
        elif pnl > 500:
            emoji = "🔥"
        elif pnl > 0:
            emoji = "✅"
        elif pnl == 0:
            emoji = "⏳"
        else:
            emoji = "❌"

        print(f"{emoji} PnL: ${pnl:>10,.2f} | Trades: {trades:>4d} | Win Rate: {win_rate:>5.1f}%")

        # Guardar resultado
        all_results.append({
            'gen': gen,
            'pnl': pnl,
            'trades': trades,
            'win_rate': win_rate,
            'genome': data.get('genome')
        })

        # Actualizar mejor histórico
        if pnl > best_ever['pnl']:
            best_ever = {
                'pnl': pnl,
                'genome': data.get('genome'),
                'gen': gen,
                'trades': trades,
                'win_rate': win_rate
            }
            if pnl > 0:
                print(f"   🏆 NUEVO RÉCORD! (Generación {gen})")

# 4. Ejecutar
print("="*80)
print("⚡ INICIANDO MINERÍA DE ESTRATEGIAS RENTABLES...")
print("="*80)
print("ℹ️  Este proceso puede tardar 40-60 minutos. Ten paciencia...")
print("ℹ️  Los mejores resultados suelen aparecer después de la Gen 10\n")

start_time = time.time()
best_genome, best_pnl = miner.run(progress_callback=show_progress)
total_time = time.time() - start_time

# 5. Análisis de Resultados
print("\n" + "="*80)
print("🏆 ANÁLISIS DE RESULTADOS")
print("="*80 + "\n")

print(f"⏱️  Tiempo Total: {int(total_time/60)} minutos {int(total_time%60)} segundos")
print(f"⚡ Velocidad: {int(total_time/20)} seg/generación")
print(f"💻 Throughput: {int(50*20/(total_time/60))} estrategias/min\n")

print(f"💰 Mejor PnL Final: ${best_pnl:,.2f}")

if best_ever['pnl'] > 0:
    print(f"\n🎉 ¡ÉXITO! Encontramos estrategias rentables:")
    print(f"   Mejor PnL: ${best_ever['pnl']:,.2f}")
    print(f"   Generación: {best_ever['gen']}")
    print(f"   Trades: {best_ever['trades']}")
    print(f"   Win Rate: {best_ever['win_rate']:.1f}%\n")

    print("📋 Detalles de la Mejor Estrategia:")
    genome = best_ever['genome']
    print(f"\n   Entry Rules ({len(genome.get('entry_rules', []))} reglas):")
    for i, rule in enumerate(genome.get('entry_rules', [])):
        print(f"      {i+1}. {rule}")

    params = genome.get('params', {})
    print(f"\n   Risk Management:")
    print(f"      Stop Loss: {params.get('sl_pct', 0):.2%}")
    print(f"      Take Profit: {params.get('tp_pct', 0):.2%}")

    # Guardar resultado
    timestamp = int(time.time())
    result_file = f"BEST_STRATEGY_{timestamp}.json"
    with open(result_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'pnl': best_ever['pnl'],
            'trades': best_ever['trades'],
            'win_rate': best_ever['win_rate'],
            'genome': best_ever['genome'],
            'generation': best_ever['gen'],
            'execution_time_seconds': total_time,
            'dataset_size': len(df),
            'dataset_range': f"{df.iloc[0]['timestamp']} -> {df.iloc[-1]['timestamp']}"
        }, f, indent=2)
    print(f"\n💾 Mejor estrategia guardada en: {result_file}")

elif best_pnl == 0:
    print(f"\n⚠️  Ninguna estrategia generó trades")
    print("   Causas posibles:")
    print("   - Reglas muy restrictivas (convergencia prematura)")
    print("   - Dataset muy pequeño")
    print("   - Necesita más generaciones para diversificar\n")
    print("   Sugerencias:")
    print("   - Aumentar población a 100")
    print("   - Aumentar generaciones a 50")
    print("   - Cambiar risk_level a HIGH")

else:
    print(f"\n⚠️  Mejor PnL negativo: ${best_pnl:,.2f}")
    print("   Esto es relativamente común en tests pequeños")
    print("   Estrategias con PnL negativo aún pueden ser valiosas para el análisis\n")

# Mostrar evolución
print("\n📊 Evolución de la Minería:")
print("   Gen |    PnL     | Trades | Win Rate | Nota")
print("   " + "-"*70)
for r in all_results:
    note = ""
    if r['pnl'] > 0:
        note = "✅"
    if r['pnl'] > best_ever['pnl'] * 0.9 and best_ever['pnl'] > 0:
        note = "🏆 Top"

    print(f"   {r['gen']:>2d}  | ${r['pnl']:>9,.2f} | {r['trades']:>6d} | {r['win_rate']:>7.1f}% | {note}")

# Estadísticas finales
profitable_count = len([r for r in all_results if r['pnl'] > 0])
zero_trades_count = len([r for r in all_results if r['trades'] == 0])

print(f"\n📈 Estadísticas Generales:")
print(f"   Generaciones con PnL > 0: {profitable_count}/20")
print(f"   Generaciones sin trades: {zero_trades_count}/20")
print(f"   Tasa de éxito: {(profitable_count/20)*100:.1f}%")

# Guardar todas las estrategias
all_strategies_file = f"all_strategies_{int(time.time())}.json"
with open(all_strategies_file, 'w') as f:
    json.dump({
        'execution_time': total_time,
        'best_pnl': best_pnl,
        'best_ever': best_ever,
        'all_results': all_results,
        'stats': {
            'profitable_count': profitable_count,
            'zero_trades_count': zero_trades_count,
            'success_rate': (profitable_count/20)*100
        }
    }, f, indent=2)

print(f"\n💾 Todas las estrategias guardadas en: {all_strategies_file}")

print("\n" + "="*80 + "\n")

ray.shutdown()

# Exit code según resultado
if best_ever['pnl'] > 500:
    print("🎉 MISIÓN CUMPLIDA: Estrategia altamente rentable encontrada!\n")
    exit(0)
elif best_ever['pnl'] > 0:
    print("✅ ÉXITO PARCIAL: Estrategia rentable encontrada, pero podría mejorarse\n")
    exit(0)
else:
    print("⚠️  No se encontraron estrategias rentables en esta ejecución\n")
    print("   Considera ejecutar nuevamente con más población/generaciones\n")
    exit(1)
