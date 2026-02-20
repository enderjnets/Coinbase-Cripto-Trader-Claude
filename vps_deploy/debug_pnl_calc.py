"""
Debug: Verificar cálculo de PnL manualmente
"""

# Trade #5 del backtest alcista (TAKE_PROFIT que resultó en pérdida)
entry_price = 117317.20
exit_price = 117998.48
size_usd = 1000
fee_rate = 0.004  # 0.4% Maker

print("=" * 70)
print("🔍 DEBUG: Cálculo Manual de PnL - Trade #5")
print("=" * 70)

print(f"\n📊 DATOS DEL TRADE:")
print(f"   Entry price: ${entry_price:,.2f}")
print(f"   Exit price:  ${exit_price:,.2f}")
print(f"   Movimiento:  +${exit_price - entry_price:,.2f} ({((exit_price/entry_price - 1) * 100):.2f}%)")
print(f"   Razón:       TAKE_PROFIT")

# COMPRA
print(f"\n💵 COMPRA (Entry):")
entry_fee = size_usd * fee_rate
cost_total = size_usd + entry_fee
quantity = size_usd / entry_price

print(f"   Inversión:    ${size_usd:,.2f}")
print(f"   Fee (0.4%):   ${entry_fee:,.2f}")
print(f"   COSTO TOTAL:  ${cost_total:,.2f}")
print(f"   Cantidad BTC: {quantity:.8f}")

# VENTA
print(f"\n💰 VENTA (Exit):")
exit_val_gross = quantity * exit_price
exit_fee = exit_val_gross * fee_rate
exit_val_net = exit_val_gross - exit_fee

print(f"   Valor bruto:  ${exit_val_gross:,.2f}")
print(f"   Fee (0.4%):   ${exit_fee:,.2f}")
print(f"   VALOR NETO:   ${exit_val_net:,.2f}")

# PnL
print(f"\n🎯 RESULTADO:")
pnl = exit_val_net - cost_total
pnl_pct = (pnl / cost_total) * 100

print(f"   PnL = Valor Neto - Costo Total")
print(f"   PnL = ${exit_val_net:.2f} - ${cost_total:.2f}")
print(f"   PnL = ${pnl:.2f}")
print(f"   PnL % = {pnl_pct:.2f}%")

print("\n" + "=" * 70)

if pnl > 0:
    print("✅ CORRECTO: PnL debería ser POSITIVO")
else:
    print("❌ ERROR: PnL debería ser POSITIVO, pero es NEGATIVO")

print("=" * 70)

# Ahora verificar qué hace el backtester
print("\n🔍 VERIFICANDO CÓDIGO DEL BACKTESTER:")
print("\nLeyendo backtester.py...")

# Leer el código relevante
with open('backtester.py', 'r') as f:
    lines = f.readlines()

print("\n📋 Código de cálculo de PnL (líneas 160-170):")
for i, line in enumerate(lines[159:171], start=160):
    print(f"{i}: {line.rstrip()}")
