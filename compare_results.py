#!/usr/bin/env python3
"""
Comparador de Resultados - Búsquedas Paralelas
Compara estrategias de MacBook Pro vs MacBook Air
"""

import json
import glob
from datetime import datetime

print("\n" + "="*80)
print("📊 COMPARADOR DE RESULTADOS - BÚSQUEDAS PARALELAS")
print("="*80 + "\n")

# Buscar archivos de resultados
pro_files = sorted(glob.glob("BEST_STRATEGY_PRO_*.json"))
air_files = sorted(glob.glob("BEST_STRATEGY_AIR_*.json"))

if not pro_files and not air_files:
    print("❌ No se encontraron archivos de resultados.")
    print("   Esperando archivos:")
    print("   - BEST_STRATEGY_PRO_*.json")
    print("   - BEST_STRATEGY_AIR_*.json\n")
    exit(1)

print(f"📁 Archivos encontrados:")
print(f"   MacBook PRO: {len(pro_files)} búsqueda(s)")
print(f"   MacBook AIR: {len(air_files)} búsqueda(s)\n")

# Cargar resultados más recientes
strategies = []

if pro_files:
    with open(pro_files[-1], 'r') as f:
        pro_data = json.load(f)
        strategies.append({
            'source': 'MacBook PRO',
            'risk': 'MEDIUM',
            'file': pro_files[-1],
            **pro_data
        })
    print(f"✅ Cargado: {pro_files[-1]}")

if air_files:
    with open(air_files[-1], 'r') as f:
        air_data = json.load(f)
        strategies.append({
            'source': 'MacBook AIR',
            'risk': 'LOW',
            'file': air_files[-1],
            **air_data
        })
    print(f"✅ Cargado: {air_files[-1]}")

print("\n" + "="*80)
print("📊 COMPARACIÓN DE RESULTADOS")
print("="*80 + "\n")

# Tabla comparativa
print("┌─────────────────┬──────────────┬──────────────┐")
print("│     Métrica     │ MacBook PRO  │ MacBook AIR  │")
print("├─────────────────┼──────────────┼──────────────┤")

# Comparar métricas
if len(strategies) == 2:
    pro_s = strategies[0]
    air_s = strategies[1]

    print(f"│ PnL Total       │ ${pro_s['pnl']:>10,.2f} │ ${air_s['pnl']:>10,.2f} │")
    print(f"│ Trades          │ {pro_s['trades']:>12d} │ {air_s['trades']:>12d} │")
    print(f"│ Win Rate        │ {pro_s['win_rate']*100:>11.1f}% │ {air_s['win_rate']*100:>11.1f}% │")

    # Sharpe ratio aproximado
    pro_sharpe = pro_s['pnl'] / max(pro_s['trades'], 1)
    air_sharpe = air_s['pnl'] / max(air_s['trades'], 1)
    print(f"│ PnL/Trade       │ ${pro_sharpe:>10,.2f} │ ${air_sharpe:>10,.2f} │")

    # Tiempo de ejecución
    pro_time = pro_s['config']['population'] * pro_s['config']['generations']
    air_time = air_s['config']['population'] * air_s['config']['generations']
    print(f"│ Estrategias     │ {pro_time:>12,} │ {air_time:>12,} │")

    print(f"│ Generación      │ {pro_s['generation']:>12d} │ {air_s['generation']:>12d} │")
    print(f"│ Risk Level      │ {pro_s['config']['risk_level']:>12} │ {air_s['config']['risk_level']:>12} │")

print("└─────────────────┴──────────────┴──────────────┘\n")

# Determinar ganador
print("="*80)
print("🏆 ANÁLISIS Y RECOMENDACIONES")
print("="*80 + "\n")

if len(strategies) == 2:
    # Calcular score compuesto
    def calculate_score(s):
        # Peso: 50% PnL, 30% Trades, 20% Win Rate
        pnl_score = s['pnl'] * 0.5
        trades_score = s['trades'] * 10 * 0.3
        winrate_score = s['win_rate'] * 1000 * 0.2
        return pnl_score + trades_score + winrate_score

    pro_score = calculate_score(strategies[0])
    air_score = calculate_score(strategies[1])

    winner = strategies[0] if pro_score > air_score else strategies[1]
    loser = strategies[1] if pro_score > air_score else strategies[0]

    print(f"🥇 GANADOR: {winner['source']}")
    print(f"   PnL: ${winner['pnl']:,.2f}")
    print(f"   Trades: {winner['trades']}")
    print(f"   Win Rate: {winner['win_rate']*100:.1f}%")
    print(f"   Score compuesto: {calculate_score(winner):.2f}\n")

    print(f"🥈 Segundo lugar: {loser['source']}")
    print(f"   PnL: ${loser['pnl']:,.2f}")
    print(f"   Trades: {loser['trades']}")
    print(f"   Win Rate: {loser['win_rate']*100:.1f}%")
    print(f"   Score compuesto: {calculate_score(loser):.2f}\n")

    # Análisis de reglas
    print("="*80)
    print("📋 ESTRATEGIA GANADORA - REGLAS")
    print("="*80 + "\n")

    genome = winner['genome']
    print(f"Entry Rules ({len(genome.get('entry_rules', []))} reglas):\n")

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

        print(f"   {i}. {left_str} {op} {right_str}")

    params = genome.get('params', {})
    print(f"\nRisk Management:")
    print(f"   Stop Loss: {params.get('sl_pct', 0):.2%}")
    print(f"   Take Profit: {params.get('tp_pct', 0):.2%}")
    print(f"   Ratio TP/SL: {params.get('tp_pct', 0) / max(params.get('sl_pct', 0.01), 0.01):.2f}x\n")

# Comparación con estrategia anterior
print("="*80)
print("📈 COMPARACIÓN CON BÚSQUEDA ANTERIOR")
print("="*80 + "\n")

# Buscar estrategia anterior (NO_RAY)
prev_files = sorted(glob.glob("BEST_STRATEGY_NO_RAY_*.json"))
if prev_files:
    with open(prev_files[-1], 'r') as f:
        prev_data = json.load(f)

    print(f"Búsqueda Anterior (30 población × 20 gen):")
    print(f"   PnL: ${prev_data['pnl']:,.2f}")
    print(f"   Trades: {prev_data['trades']}")
    print(f"   Win Rate: {prev_data['win_rate']*100:.1f}%\n")

    if len(strategies) == 2:
        best_new = max(strategies, key=lambda x: x['pnl'])
        improvement = ((best_new['pnl'] - prev_data['pnl']) / max(abs(prev_data['pnl']), 1)) * 100

        if improvement > 0:
            print(f"✅ MEJORA: +{improvement:.1f}% vs búsqueda anterior")
        else:
            print(f"⚠️  Búsqueda anterior sigue siendo mejor ({abs(improvement):.1f}% más PnL)")
        print()

# Recomendaciones finales
print("="*80)
print("💡 PRÓXIMOS PASOS RECOMENDADOS")
print("="*80 + "\n")

if len(strategies) == 2:
    print("1. VALIDAR AMBAS ESTRATEGIAS")
    print("   → Ejecutar backtest en datos out-of-sample")
    print("   → Walk-forward testing\n")

    print("2. IMPLEMENTAR LA MEJOR")
    print(f"   → Usar estrategia de {winner['source']}")
    print("   → Empezar con paper trading\n")

    if winner['trades'] < 5:
        print("⚠️  ADVERTENCIA: Muy pocos trades")
        print(f"   Solo {winner['trades']} operaciones no es estadísticamente significativo")
        print("   Considerar ejecutar búsqueda más larga o validar extensivamente\n")

    print("3. CONSIDERAR HÍBRIDO")
    print("   → Combinar lo mejor de ambas estrategias")
    print("   → Probar reglas de PRO con risk management de AIR\n")

print("="*80)
print("📁 ARCHIVOS GENERADOS")
print("="*80 + "\n")

for s in strategies:
    print(f"✅ {s['file']}")

print("\n" + "="*80)
print("🤖 Análisis completado")
print("="*80 + "\n")
