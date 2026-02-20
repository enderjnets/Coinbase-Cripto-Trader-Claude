#!/usr/bin/env python3
"""
Test del Strategy Miner en MODO LOCAL
Usa todos los cores del MacBook Air para validar funcionalidad
"""

import pandas as pd
from strategy_miner import StrategyMiner
import time
import ray
import os

print("\n" + "="*80)
print("🧬 STRATEGY MINER - TEST LOCAL (10 CPUs)")
print("="*80 + "\n")

# Inicializar Ray LOCAL (no cluster)
if ray.is_initialized():
    print("⚠️  Ray ya estaba inicializado, cerrando...")
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

# Verificar recursos
resources = ray.cluster_resources()
total_cpus = int(resources.get('CPU', 0))
print(f"✅ Ray inicializado")
print(f"   CPUs disponibles: {total_cpus}\n")

# 1. Cargar datos
print("📊 Cargando datos...")
df = pd.read_csv("data/BTC-USD_FIVE_MINUTE.csv")
print(f"   Dataset: {len(df):,} velas")
print(f"   Rango: {df.iloc[0]['timestamp']} -> {df.iloc[-1]['timestamp']}\n")

# 2. Configurar miner
print("⚙️  Configuración TEST:")
print(f"   • Población: 20")
print(f"   • Generaciones: 5")
print(f"   • Risk Level: LOW")
print(f"   • CPUs: {total_cpus}\n")

miner = StrategyMiner(
    df=df,
    population_size=20,
    generations=5,
    risk_level="LOW",
    force_local=True  # IMPORTANTE: Forzar modo local
)

# 3. Callback
generation_best = []

def show_progress(msg_type, data):
    if msg_type == "START_GEN":
        print(f"\n🧬 Generación {data}/5")

    elif msg_type == "BEST_GEN":
        pnl = data.get('pnl', 0)
        trades = data.get('num_trades', 0)
        win_rate = data.get('win_rate', 0) * 100

        emoji = "🔥" if pnl > 1000 else ("✅" if pnl > 0 else "⏳")
        print(f"   {emoji} PnL: ${pnl:>8,.2f} | Trades: {trades:>3d} | Win: {win_rate:>5.1f}%")

        generation_best.append({
            'gen': data.get('gen', 0),
            'pnl': pnl,
            'trades': trades,
            'win_rate': win_rate,
            'genome': data.get('genome')
        })

    elif msg_type == "BATCH_PROGRESS":
        # Mostrar progreso global
        pct = data * 100
        if int(pct) % 10 == 0 and int(pct) > 0:
            # Solo mostrar cada 10%
            pass

# 4. Ejecutar
print("="*80)
print("⚡ INICIANDO MINERÍA...")
print("="*80)

start_time = time.time()
best_genome, best_pnl = miner.run(progress_callback=show_progress)
total_time = time.time() - start_time

# 5. Resultados
print("\n" + "="*80)
print("🏆 RESULTADO FINAL")
print("="*80 + "\n")

print(f"💰 Mejor PnL: ${best_pnl:,.2f}")
print(f"⏱️  Tiempo Total: {int(total_time)} segundos")
print(f"⚡ Velocidad: {int(total_time / 5)} seg/generación\n")

if best_pnl > 0:
    print("✅ ¡ÉXITO! El algoritmo encontró estrategia rentable\n")
    print("📋 Mejor Estrategia:")
    print(f"   Entry Rules: {len(best_genome.get('entry_rules', []))} reglas")
    for i, rule in enumerate(best_genome.get('entry_rules', [])):
        print(f"      {i+1}. {rule}")
    print(f"\n   Stop Loss: {best_genome.get('params', {}).get('sl_pct', 0):.2%}")
    print(f"   Take Profit: {best_genome.get('params', {}).get('tp_pct', 0):.2%}")

elif best_pnl == -9999:
    print("❌ ERROR: PnL = -9999 indica problema en backtest")
    print("   Posibles causas:")
    print("   - Dataset demasiado pequeño")
    print("   - Error en carga de datos")
    print("   - Timeout en tasks")
    print("\n   Revisa: miner_debug.log")

else:
    print("⚠️  PnL negativo (puede ser normal en test pequeño)")
    print("   Aumenta población y generaciones para mejores resultados")

# Mostrar evolución
if generation_best:
    print("\n📊 Evolución por Generación:")
    print("   Gen | PnL        | Trades | Win Rate")
    print("   " + "-"*40)
    for g in generation_best:
        print(f"   {g['gen']:>2d}  | ${g['pnl']:>8,.2f} | {g['trades']:>6d} | {g['win_rate']:>6.1f}%")

print("\n" + "="*80 + "\n")

# Guardar resultado
if best_pnl > 0:
    import json
    result_file = f"miner_result_local_{int(time.time())}.json"
    with open(result_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'pnl': best_pnl,
            'genome': best_genome,
            'time_seconds': total_time,
            'generations': generation_best
        }, f, indent=2)
    print(f"💾 Resultado guardado en: {result_file}\n")

ray.shutdown()
