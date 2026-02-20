"""
Find significant bearish periods in the data
Para testing cash_mode necesitamos caídas >8%
"""

import pandas as pd
import numpy as np

# Cargar datos
df = pd.read_csv('data/BTC-USD_FIVE_MINUTE.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("🔍 Buscando períodos bajistas significativos...")
print(f"Datos: {len(df)} velas desde {df['timestamp'].iloc[0]} hasta {df['timestamp'].iloc[-1]}")

# Buscar ventanas de 500 velas (~41 horas) con caídas significativas
window_size = 500
min_drop = 5.0  # Buscar caídas de al menos 5%

bearish_periods = []

for i in range(0, len(df) - window_size, 100):  # Step de 100 para rapidez
    window = df.iloc[i:i+window_size]
    start_price = window['close'].iloc[0]
    end_price = window['close'].iloc[-1]

    # Calcular máxima caída desde cualquier punto
    high = window['high'].max()
    low = window['low'].min()
    max_drop_pct = ((low - high) / high) * 100

    # Caída total del período
    total_drop_pct = ((end_price - start_price) / start_price) * 100

    if max_drop_pct < -min_drop or total_drop_pct < -min_drop:
        bearish_periods.append({
            'start_idx': i,
            'end_idx': i + window_size,
            'start_time': window['timestamp'].iloc[0],
            'end_time': window['timestamp'].iloc[-1],
            'start_price': start_price,
            'end_price': end_price,
            'high': high,
            'low': low,
            'total_drop_pct': total_drop_pct,
            'max_drop_pct': max_drop_pct
        })

# Ordenar por mayor caída
bearish_periods_df = pd.DataFrame(bearish_periods)
if not bearish_periods_df.empty:
    bearish_periods_df = bearish_periods_df.sort_values('max_drop_pct', ascending=True)

    print(f"\n📉 Top 10 períodos bajistas encontrados:\n")
    print(f"{'Índice':<12} {'Fecha inicio':<20} {'Caída total':<12} {'Caída máxima':<12} {'Rango precio'}")
    print("-" * 90)

    for idx, period in bearish_periods_df.head(10).iterrows():
        print(f"{period['start_idx']:<12} {str(period['start_time']):<20} "
              f"{period['total_drop_pct']:>10.2f}% {period['max_drop_pct']:>10.2f}%  "
              f"${period['high']:>10,.0f} → ${period['low']:>10,.0f}")

    # Mejor candidato
    best = bearish_periods_df.iloc[0]
    print(f"\n🎯 MEJOR PERÍODO PARA TEST:")
    print(f"   Índice: {best['start_idx']} - {best['end_idx']}")
    print(f"   Período: {best['start_time']} → {best['end_time']}")
    print(f"   Precio: ${best['start_price']:,.2f} → ${best['end_price']:,.2f}")
    print(f"   Caída total: {best['total_drop_pct']:.2f}%")
    print(f"   Caída máxima: {best['max_drop_pct']:.2f}%")
    print(f"\n   Usar: df.iloc[{best['start_idx']}:{best['end_idx']}]")
else:
    print("\n⚠️  No se encontraron períodos bajistas significativos")

# También buscar caídas rápidas (en ventanas más pequeñas)
print("\n" + "=" * 90)
print("🔍 Buscando caídas rápidas (100 velas = ~8 horas)...\n")

window_size_short = 100
rapid_drops = []

for i in range(0, len(df) - window_size_short, 50):
    window = df.iloc[i:i+window_size_short]

    # Buscar la mayor caída intrawindow
    for j in range(len(window)):
        high_before = window['high'].iloc[:j+1].max() if j > 0 else window['high'].iloc[0]
        low_after = window['low'].iloc[j:].min()
        drop_pct = ((low_after - high_before) / high_before) * 100

        if drop_pct < -8.0:  # Caída >8% (umbral de cash_mode)
            rapid_drops.append({
                'start_idx': i,
                'end_idx': i + window_size_short,
                'drop_idx': i + j,
                'start_time': window['timestamp'].iloc[0],
                'drop_time': window['timestamp'].iloc[j] if j < len(window) else window['timestamp'].iloc[-1],
                'high_price': high_before,
                'low_price': low_after,
                'drop_pct': drop_pct
            })
            break  # Solo registrar la primera caída >8% en esta ventana

rapid_drops_df = pd.DataFrame(rapid_drops)
if not rapid_drops_df.empty:
    rapid_drops_df = rapid_drops_df.sort_values('drop_pct', ascending=True)

    print(f"⚡ Top 5 caídas rápidas >8%:\n")
    print(f"{'Índice':<12} {'Momento caída':<20} {'Caída':<10} {'Precio'}")
    print("-" * 70)

    for idx, drop in rapid_drops_df.head(5).iterrows():
        print(f"{drop['start_idx']:<12} {str(drop['drop_time']):<20} "
              f"{drop['drop_pct']:>8.2f}%  ${drop['high_price']:>10,.0f} → ${drop['low_price']:>10,.0f}")

    # Mejor candidato
    best_rapid = rapid_drops_df.iloc[0]
    print(f"\n🎯 MEJOR CAÍDA RÁPIDA:")
    print(f"   Índice: {best_rapid['start_idx']} - {best_rapid['end_idx']}")
    print(f"   Caída: {best_rapid['drop_pct']:.2f}%")
    print(f"   ${best_rapid['high_price']:,.2f} → ${best_rapid['low_price']:,.2f}")
    print(f"\n   Usar: df.iloc[{best_rapid['start_idx']}:{best_rapid['end_idx']+500}]")
else:
    print("\n⚠️  No se encontraron caídas rápidas >8%")
