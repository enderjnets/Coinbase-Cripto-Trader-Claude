#!/usr/bin/env python3
"""
Test del Strategy Miner OPTIMIZADO PARA 9 CPUs
- Limitado a 9 CPUs para evitar sobrecarga del sistema
- Configuración segura para MacBook Air
- Modo LOCAL (no requiere cluster)
"""

import pandas as pd
from strategy_miner import StrategyMiner
import time
import ray
import json

print("\n" + "="*80)
print("🧬 STRATEGY MINER - MODO SEGURO (9 CPUs)")
print("="*80 + "\n")

# Inicializar Ray LOCAL con SOLO 9 CPUs
if ray.is_initialized():
    ray.shutdown()
    time.sleep(1)

print(f"💻 Inicializando Ray con 9 CPUs (1 CPU reservado para el sistema)...\n")

ray.init(
    address='local',
    num_cpus=9,  # FORZAR 9 CPUs
    ignore_reinit_error=True,
    logging_level="ERROR",
    include_dashboard=False,
    _temp_dir='/tmp/ray_safe'
)

resources = ray.cluster_resources()
total_cpus = int(resources.get('CPU', 0))
print(f"✅ Ray inicializado - {total_cpus} CPUs disponibles\n")

if total_cpus != 9:
    print(f"⚠️  ADVERTENCIA: Se esperaban 9 CPUs pero se detectaron {total_cpus}")
    print("   Continuando de todas formas...\n")

# 1. Cargar datos - Dataset reciente optimizado
print("📊 Cargando datos...")
df_full = pd.read_csv("data/BTC-USD_FIVE_MINUTE.csv")

# Últimos 3 meses de datos
df = df_full.tail(25000).copy()
df.reset_index(drop=True, inplace=True)

print(f"   Dataset: {len(df):,} velas")
print(f"   Rango: {df.iloc[0]['timestamp']} -> {df.iloc[-1]['timestamp']}\n")

# 2. Configuración CONSERVADORA para evitar sobrecarga
print("⚙️  Configuración SEGURA (9 CPUs):")
print(f"   • Población: 45 (5 x 9 CPUs)")
print(f"   • Generaciones: 20")
print(f"   • Risk Level: MEDIUM")
print(f"   • CPUs: {total_cpus}/9")
print(f"   • Modo: LOCAL (sin cluster)")
print(f"   • Tiempo estimado: ~50-70 minutos\n")

miner = StrategyMiner(
    df=df,
    population_size=45,  # Múltiplo de 9 para balanceo perfecto
    generations=20,
    risk_level="MEDIUM",
    force_local=True
)

# 3. Callback con progreso
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

        all_results.append({
            'gen': gen,
            'pnl': pnl,
            'trades': trades,
            'win_rate': win_rate,
            'genome': data.get('genome')
        })

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
print("⚡ INICIANDO MINERÍA (MODO SEGURO - 9 CPUs)...")
print("="*80)
print("ℹ️  Configuración optimizada para evitar sobrecarga del sistema")
print("ℹ️  Tiempo estimado: 50-70 minutos\n")

start_time = time.time()
best_genome, best_pnl = miner.run(progress_callback=show_progress)
total_time = time.time() - start_time

# 5. Resultados
print("\n" + "="*80)
print("🏆 RESULTADOS")
print("="*80 + "\n")

print(f"⏱️  Tiempo Total: {int(total_time/60)}m {int(total_time%60)}s")
print(f"💰 Mejor PnL: ${best_pnl:,.2f}\n")

if best_ever['pnl'] > 0:
    print(f"🎉 ¡ÉXITO! Estrategia rentable encontrada:")
    print(f"   PnL: ${best_ever['pnl']:,.2f}")
    print(f"   Generación: {best_ever['gen']}")
    print(f"   Trades: {best_ever['trades']}")
    print(f"   Win Rate: {best_ever['win_rate']:.1f}%\n")

    # Guardar
    timestamp = int(time.time())
    result_file = f"BEST_STRATEGY_9CPU_{timestamp}.json"
    with open(result_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'pnl': best_ever['pnl'],
            'trades': best_ever['trades'],
            'win_rate': best_ever['win_rate'],
            'genome': best_ever['genome'],
            'generation': best_ever['gen'],
            'execution_time_seconds': total_time,
            'cpus_used': 9,
            'mode': 'LOCAL_SAFE',
            'dataset_size': len(df)
        }, f, indent=2)
    print(f"💾 Guardado en: {result_file}\n")

else:
    print(f"⚠️  No se encontraron estrategias rentables")
    print(f"   Mejor PnL: ${best_pnl:,.2f}\n")

# Evolución
print("📊 Evolución:")
print("   Gen |    PnL     | Trades | Win Rate")
print("   " + "-"*50)
for r in all_results:
    emoji = "🏆" if r['pnl'] == best_ever['pnl'] else ("✅" if r['pnl'] > 0 else "  ")
    print(f"   {r['gen']:>2d}  | ${r['pnl']:>9,.2f} | {r['trades']:>6d} | {r['win_rate']:>7.1f}% {emoji}")

profitable_count = len([r for r in all_results if r['pnl'] > 0])
print(f"\n📈 Rentables: {profitable_count}/20 ({(profitable_count/20)*100:.0f}%)\n")

print("="*80 + "\n")

ray.shutdown()

exit(0 if best_ever['pnl'] > 0 else 1)
