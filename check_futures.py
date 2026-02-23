#!/usr/bin/env python3
import requests
import json
from datetime import datetime

# Obtener contratos de futuros activos (endpoint público)
url = "https://api.coinbase.com/api/v3/brokerage/market/products?product_type=FUTURE"
resp = requests.get(url, timeout=30)
data = resp.json()
products = data.get('products', [])

print(f"Total futuros disponibles: {len(products)}\n")
print(f"{'Product ID':25} | {'Base':8} | {'Expiry':20} | {'Days':>5} | Type")
print("-" * 80)

active_contracts = []
for p in sorted(products, key=lambda x: x.get('contract_expiry_date', '9999')):
    pid = p['product_id']
    base = p.get('base_currency_id', '?')
    exp = p.get('contract_expiry_date', '')
    ctype = p.get('contract_type', '?')

    days_left = 'PERP'
    if exp:
        try:
            exp_date = datetime.fromisoformat(exp.replace('Z', '+00:00'))
            days_left = str((exp_date - datetime.now(exp_date.tzinfo)).days)
            active_contracts.append({
                'product_id': pid,
                'base': base,
                'expiry': exp,
                'days': int(days_left),
                'type': ctype
            })
        except:
            pass

    exp_str = exp[:19] if exp else 'PERPETUAL'
    print(f"{pid:25} | {base:8} | {exp_str:20} | {days_left:>5} | {ctype}")

print(f"\n--- Contratos activos (no vencidos): {len(active_contracts)} ---")
for c in active_contracts:
    print(f"  {c['product_id']}: {c['base']} - {c['days']} días restantes")
