# 🚀 INICIAR WORKER EN MACBOOK PRO

**Para activar los 18 cores en paralelo**

---

## Opción 1: Comando Rápido

Abre Terminal en MacBook Pro y ejecuta:

```bash
cd /Users/enderjnets
python3 crypto_worker.py http://100.118.215.73:5001 &
```

---

## Opción 2: Con Auto-Restart (Recomendado)

```bash
cd /Users/enderjnets
nohup python3 crypto_worker.py http://100.118.215.73:5001 > worker_pro.log 2>&1 &
```

---

## Verificar que está funcionando

```bash
# Ver proceso
ps aux | grep crypto_worker

# Ver log
tail -f worker_pro.log

# Ver Ray workers (deberías ver 9)
ps aux | grep "ray::run_backtest_task" | wc -l
```

---

## Estado Actual del Sistema

✅ **MacBook Air: 9 cores activos (880% CPU)**
⏳ **MacBook Pro: Esperando inicio**

Con Pro activo tendrás:
- Air: 9 cores procesando
- Pro: 9 cores procesando
- **Total: 18 cores en red trabajando al unísono**

---

## Work Units Disponibles

El coordinator tiene 3 work units pendientes esperando:
- WU #10: Population 30, Generations 100
- WU #11: Population 25, Generations 50
- WU #12: Population 25, Generations 50

Cuando inicies el Pro, tomará automáticamente uno de estos work units.

---

**Nota:** El worker se conectará automáticamente al coordinator y comenzará a procesar inmediatamente.
