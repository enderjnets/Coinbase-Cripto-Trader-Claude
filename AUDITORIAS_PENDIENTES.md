# 📋 AUDITORÍAS PENDIENTES - BUGS 5-12

## 🔍 Bugs Auditables

| # | Archivo | Problema | Estado |
|----|---------|-----------|--------|
| 5 | config.py | Token addresses | ⏳ PENDIENTE |
| 6 | dynamic_strategy.py | SMA/EMA logic | ⏳ PENDIENTE |
| 7 | strategy.py | Sell TP params | ⏳ PENDIENTE |
| 8 | backtester.py | Drawdown tracking | ⏳ PENDIENTE |
| 9 | *.py | .seconds vs .total_seconds() | ⏳ PENDIENTE |
| 11 | coinbase_client.py | Decimals | ⏳ PENDIENTE |
| 12 | *.py | Syntax review general | ⏳ PENDIENTE |
| 10 | Risk limits enforcement | Implementado | ✅ HECHO |

---

## 📋 BUG #5: TOKEN ADDRESSES
### Archivos a verificar:
- config.py
- coinbase_client.py
- dynamic_strategy.py

```bash
# Verificar direcciones de tokens
grep -rn "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" .
grep -rn "Es9vMFrzaCERmJfrF4H2 🔍 BUG #6: SMA/EMA LOGIC
### Problema: Comparar price vs indicator con % deviation
### Archivos: dynamic_strategy.py, strategy.py
```

Verificar que SMA/EMA comparen precio vs indicador correctamente.

```python
# CORREGIDO vs ORIGINAL
# ANTES (BUGGY)
if sma > 0:  # SMA siempre > 0!
    buy_condition = True

# DESPUÉS (CORRECTO)  
price < sma * (1 - deviation)
```

---

## 🔧 BUG #7: SELL TP
### Verificar que TP venga del genome params
### Archivos: strategy.py, dynamic_strategy.py
```

---

## 📊 BUG #8: DRAWDOWN TRACKING
### Tracking continuo (no solo entre trades)
### Archivos: backtester.py, numba_backtester.py
```

---

## ⏰ BUG #9: .seconds vs .total_seconds()
### Buscar y reemplazar en todo el código
```bash
grep -rn "\.seconds" --include="*.py"
```

---

## 🔢 BUG #11: DECIMALS
### Verificar decimales por token
### Archivos: coinbase_client.py
```

---

## 📝 BUG #12: SYNTAX REVIEW
### Verificar todos los scripts
```bash
python3 -m py_compile *.py
```

---

*Auditoría en progreso - Modo Autónomo*
