#!/usr/bin/env python3
"""
Prueba del Strategy Miner con datos reales y suficientes
"""
import pandas as pd
from strategy_miner import StrategyMiner

print("=" * 80)
print("⛏️  PRUEBA DE STRATEGY MINER CON DATOS REALES")
print("=" * 80)

# Cargar datos completos
print("\n📊 Cargando datos...")
df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")

print(f"   ✅ Dataset cargado: {len(df):,} velas")
print(f"   - Desde: {df.iloc[0]['timestamp']}")
print(f"   - Hasta: {df.iloc[-1]['timestamp']}")

# Normalizar timestamp si es necesario
if 'time' in df.columns:
    df = df.rename(columns={'time': 'timestamp'})

print("\n🧬 Configurando Strategy Miner...")
print("   - Población: 20 estrategias")
print("   - Generaciones: 3")
print("   - Modo: LOCAL (para debug)")

miner = StrategyMiner(
    df=df,
    population_size=20,  # Población pequeña para prueba rápida
    generations=3,       # Solo 3 generaciones para ver si funciona
    risk_level="LOW",
    force_local=True     # Modo local para ver errores claramente
)

print("\n⚡ Iniciando evolución...")
print("=" * 80)

# Callback para mostrar progreso
def progress_callback(msg_type, data):
    if msg_type == "START_GEN":
        print(f"\n🧬 Generación {data}...")
    elif msg_type == "BEST_GEN":
        gen = data.get('gen', 0)
        pnl = data.get('pnl', 0)
        print(f"   🏆 Mejor PnL Gen {gen}: ${pnl:.2f}")

try:
    best_genome, best_pnl = miner.run(
        progress_callback=progress_callback,
        cancel_event=None
    )

    print("\n" + "=" * 80)
    print("📊 RESULTADOS FINALES")
    print("=" * 80)

    print(f"\n🏆 Mejor PnL encontrado: ${best_pnl:.2f}")

    if best_pnl > 0:
        print("   ✅ ESTRATEGIA RENTABLE ENCONTRADA!")
    elif best_pnl > -1000:
        print("   ⚠️  PnL negativo pero razonable (dataset pequeño o mala estrategia)")
    else:
        print("   ❌ PnL muy negativo - posible problema")

    print(f"\n🧬 Mejor Genoma:")
    print(f"   - Reglas de entrada: {len(best_genome['entry_rules'])}")
    print(f"   - Stop Loss: {best_genome['params']['sl_pct']:.3f} ({best_genome['params']['sl_pct']*100:.1f}%)")
    print(f"   - Take Profit: {best_genome['params']['tp_pct']:.3f} ({best_genome['params']['tp_pct']*100:.1f}%)")

    print(f"\n📋 Reglas de Entrada:")
    for i, rule in enumerate(best_genome['entry_rules'], 1):
        print(f"   {i}. {rule}")

except Exception as e:
    print(f"\n❌ Error durante minería: {e}")
    import traceback
    print(traceback.format_exc())

print("\n" + "=" * 80)
print("✅ Prueba completada")
print("=" * 80)
