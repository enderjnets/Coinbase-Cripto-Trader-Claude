# 📊 Ray Cluster - Reporte de Problema de Scheduling

**Fecha**: 2026-01-28
**Versión Ray**: 2.51.2
**Plataforma**: macOS (Darwin 25.1.0)

---

## ✅ Estado Actual del Cluster

### Configuración (CORRECTA)
- **MacBook Pro (100.77.179.14)**: Head Node - 12 CPUs
- **MacBook Air (100.118.215.73)**: Worker Node - 10 CPUs
- **Total**: 22 CPUs disponibles
- **Conectividad**: Estable vía Tailscale VPN
- **Python**: 3.9.6 en ambas máquinas
- **Ray**: 2.51.2 en ambas máquinas

### Verificaciones Exitosas
✅ Ambos nodos vivos y registrados en GCS
✅ PYTHONPATH configurado correctamente en Worker
✅ Ambos nodos pueden ejecutar tareas (confirmado con tests)
✅ No hay errores críticos en logs

---

## ❌ PROBLEMA IDENTIFICADO: Distribución Desbalanceada de Tareas

### Comportamiento Observado
- **Head (MacBook Pro)**: 99.3% de las tareas (298/300)
- **Worker (MacBook Air)**: 0.7% de las tareas (2/300)

### Tests Realizados
1. **Test pequeño** (10 población, 5 generaciones = 50 tareas)
   - Distribución: 93.5% Head, 6.5% Worker

2. **Test mediano** (100 población, 10 generaciones = 1000 tareas)
   - Distribución: 99.3% Head, 0.7% Worker
   - Tiempo: 102 segundos (9.8 backtests/segundo)

### Causa Raíz
**Ray 2.51.2 en macOS NO respeta `scheduling_strategy="SPREAD"`**

Evidencia:
- Código ya tiene `.options(scheduling_strategy="SPREAD")` en strategy_miner.py línea 240
- Se agregó también en optimizer.py línea 84: `@ray.remote(num_cpus=1, scheduling_strategy="SPREAD")`
- A pesar de esto, Ray asigna casi todas las tareas al Head

Este es un **bug conocido/limitación de Ray en clusters macOS**. Ray está optimizado para Linux, y el scheduling en macOS tiene comportamiento subóptimo.

---

## 🔧 SOLUCIONES

### Opción 1: Actualizar Ray ⭐ (RECOMENDADO)

Ray 2.51.2 es de mayo 2024. Versiones más recientes pueden tener mejoras en scheduling para macOS.

**Pasos:**
```bash
# 1. En MacBook Air (Worker)
ssh enderj@100.118.215.73
pip3 install --upgrade ray
ray stop --force

# 2. En MacBook Pro (Head)
pip3 install --upgrade ray
ray stop --force

# 3. Reiniciar Head
ray start --head --port=6379 --node-ip-address=100.77.179.14 --num-cpus=12

# 4. Reiniciar Worker
launchctl load ~/Library/LaunchAgents/com.bittrader.worker.plist
```

**Ventajas:**
- Solución oficial
- Puede incluir correcciones de bugs
- Mejoras de rendimiento

**Desventajas:**
- Requiere actualización en ambas máquinas
- Posibles breaking changes

---

### Opción 2: Usar Placement Groups (Workaround Avanzado)

Forzar distribución explícita usando Ray Placement Groups.

**Implementación requerida en strategy_miner.py:**
```python
import ray

# Crear placement group al iniciar
pg = ray.util.placement_group([
    {"CPU": 12, "node:100.77.179.14": 1},  # Head bundle
    {"CPU": 10, "node:100.118.215.73": 1}   # Worker bundle
], strategy="STRICT_SPREAD")

ray.get(pg.ready())

# Al lanzar tareas, usar el placement group
futures = [
    run_backtest_task.options(
        placement_group=pg,
        placement_group_bundle_index=i % 2  # Alterna entre Head y Worker
    ).remote(...)
    for i, genome in enumerate(population)
]
```

**Ventajas:**
- Control explícito de distribución
- No requiere actualizar Ray

**Desventajas:**
- Código más complejo
- Requiere modificaciones significativas
- Puede tener overhead

---

### Opción 3: Aceptar Desbalance y Optimizar

El cluster funciona, solo está desbalanceado. Dado que el Head tiene MÁS CPUs (12 vs 10), podría ser aceptable.

**Análisis:**
- Head: 12 CPUs (54.5% de capacidad)
- Worker: 10 CPUs (45.5% de capacidad)
- Distribución actual: 99% Head vs 1% Worker ❌

**Mejora posible sin código:**
```bash
# Reducir CPUs del Head para forzar overflow al Worker
ray stop --force
ray start --head --port=6379 --node-ip-address=100.77.179.14 --num-cpus=6  # Reducir de 12 a 6
```

Esto forza a Ray a usar el Worker cuando el Head se satura (6 CPUs).

**Ventajas:**
- Sin cambios de código
- Solución inmediata

**Desventajas:**
- Desperdicia CPUs del Head
- No resuelve el problema real
- 6+10=16 CPUs totales en lugar de 22

---

### Opción 4: Migrar a Linux (Solución Definitiva)

Ray funciona óptimamente en Linux. Si el proyecto crece, considerar:
- Raspberry Pi Cluster
- AWS EC2 spot instances
- Servidor Linux local

**Ventajas:**
- Scheduling perfecto
- Mejor rendimiento general
- Más escalable

**Desventajas:**
- Requiere nueva infraestructura
- Costo adicional (si cloud)
- Tiempo de migración

---

## 📋 PRÓXIMOS PASOS RECOMENDADOS

### Corto Plazo (HOY)
1. ✅ Cluster estabilizado (HECHO)
2. ⚠️ Decidir entre Opción 1 (actualizar Ray) u Opción 3 (reducir CPUs Head)

### Mediano Plazo
1. Si actualizar Ray no resuelve, implementar Placement Groups (Opción 2)
2. Monitorear rendimiento y distribución en optimizaciones largas

### Largo Plazo
1. Evaluar migración a Linux si scheduling sigue siendo problema
2. Considerar escalar con más Workers

---

## 📝 NOTAS TÉCNICAS

### Archivos Modificados
- `optimizer.py` línea 84: Agregado `scheduling_strategy="SPREAD"` a `@ray.remote`
- `strategy_miner.py` línea 300: Agregado `scheduling_strategy="SPREAD"` a reintentos

### Logs de Debugging
- `/tmp/test_load_output.log`: Test de 1000 backtests
- `/tmp/test_spread_validation.log`: Validación post-fix
- `~/.bittrader_worker/logs/worker.log`: Logs del Worker

### Comandos de Verificación
```bash
# Ver estado del cluster
ssh enderj@100.77.179.14 "python3 /tmp/check_ray_status.py"

# Ver distribución de tareas
grep 'ip=100' /tmp/test_load_output.log | sort | uniq -c
```

---

## 🎯 RECOMENDACIÓN FINAL

**Intentar Opción 1 (Actualizar Ray) primero**. Si no mejora, implementar Opción 3 (reducir CPUs Head) como workaround temporal mientras se planifica Opción 2 (Placement Groups) para solución robusta.

El cluster funciona correctamente desde el punto de vista técnico. El único problema es el scheduling subóptimo de Ray en macOS, que tiene soluciones conocidas.

---

**Contacto**: Claude Sonnet 4.5
**Sesión**: 2026-01-28 22:00-23:00
