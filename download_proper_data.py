#!/usr/bin/env python3
"""
Descarga datos históricos suficientes para Strategy Miner
"""
import sys
from datetime import datetime, timedelta
from backtester import Backtester
from coinbase_client import CoinbaseClient

print("=" * 80)
print("📥 DESCARGANDO DATOS HISTÓRICOS COMPLETOS")
print("=" * 80)

# Inicializar broker y backtester
broker = CoinbaseClient()
bt = Backtester(broker_client=broker)

# Configuración de descarga
PRODUCT = "BTC-USD"
GRANULARITY = "ONE_HOUR"
DAYS_BACK = 180  # 6 meses = ~4320 velas

end_date = datetime.now()
start_date = end_date - timedelta(days=DAYS_BACK)

print(f"\n📊 Configuración:")
print(f"   - Par: {PRODUCT}")
print(f"   - Timeframe: {GRANULARITY}")
print(f"   - Desde: {start_date.strftime('%Y-%m-%d')}")
print(f"   - Hasta: {end_date.strftime('%Y-%m-%d')}")
print(f"   - Días: {DAYS_BACK}")
print(f"   - Velas esperadas: ~{DAYS_BACK * 24} velas")

print("\n📡 Descargando... (esto puede tomar 1-2 minutos)")

def progress(pct):
    bar_length = 50
    filled = int(bar_length * pct)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f"\r   [{bar}] {int(pct*100)}%", end='', flush=True)

try:
    df = bt.download_data(
        PRODUCT,
        start_date,
        end_date,
        GRANULARITY,
        progress_callback=progress
    )

    if df is not None and not df.empty:
        print(f"\n\n✅ DESCARGA COMPLETADA")
        print(f"   - Velas descargadas: {len(df):,}")
        print(f"   - Columnas: {list(df.columns)}")
        print(f"   - Fecha inicio: {df.iloc[0]['timestamp']}")
        print(f"   - Fecha fin: {df.iloc[-1]['timestamp']}")

        # Guardar a CSV
        filename = f"data/{PRODUCT}_{GRANULARITY}_FULL.csv"
        df.to_csv(filename, index=False)
        print(f"\n💾 Guardado en: {filename}")

        if len(df) >= 5000:
            print("\n✅ DATASET ÓPTIMO para Strategy Miner (5000+ velas)")
        elif len(df) >= 1000:
            print("\n⚠️  Dataset SUFICIENTE (1000+ velas), pero se recomienda más")
        else:
            print("\n❌ Dataset AÚN INSUFICIENTE - Descarga más días")

    else:
        print("\n❌ Error: No se recibieron datos")
        print("   Verifica tus API keys en cdp_api_key.json")

except Exception as e:
    print(f"\n❌ Error durante descarga: {e}")
    import traceback
    print(traceback.format_exc())

print("\n" + "=" * 80)
print("✅ Proceso completado")
print("=" * 80)
