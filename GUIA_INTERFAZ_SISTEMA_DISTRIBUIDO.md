# 🌐 Guía de Uso - Interfaz Sistema Distribuido

**Fecha:** 31 Enero 2026
**Versión:** 1.0
**Estado:** ✅ Integración Completa

---

## 📋 ÍNDICE

1. [Introducción](#introducción)
2. [Inicio Rápido](#inicio-rápido)
3. [Pestaña Dashboard](#pestaña-dashboard)
4. [Pestaña Workers](#pestaña-workers)
5. [Pestaña Control](#pestaña-control)
6. [Pestaña Logs](#pestaña-logs)
7. [Pestaña Crear Work Units](#pestaña-crear-work-units)
8. [Casos de Uso Comunes](#casos-de-uso-comunes)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 INTRODUCCIÓN

La interfaz Streamlit ahora incluye una nueva pestaña **"🌐 Sistema Distribuido"** que te permite:

- ✅ Monitorear el estado del sistema en tiempo real
- ✅ Ver workers activos y su rendimiento
- ✅ Controlar el coordinator y workers (iniciar/detener)
- ✅ Ver logs en tiempo real
- ✅ Crear nuevos work units fácilmente
- ✅ Visualizar resultados de búsquedas

**Todo desde una interfaz web intuitiva, sin necesidad de usar la terminal.**

---

## 🚀 INICIO RÁPIDO

### Paso 1: Iniciar la Interfaz

```bash
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

streamlit run interface.py
```

### Paso 2: Navegar al Sistema Distribuido

1. La interfaz se abrirá en tu navegador (http://localhost:8501)
2. En el menú lateral izquierdo, selecciona **"🌐 Sistema Distribuido"**
3. Verás el dashboard principal con 4 métricas:
   - 📡 Coordinator (estado)
   - 👥 Workers (cantidad activos)
   - 📊 Work Units (progreso)
   - 🏆 Mejor PnL (mejor resultado encontrado)

### Paso 3: Verificar Estado

Si el coordinator está **ejecutando**, verás:
- ✅ Coordinator: **ACTIVO**
- 👥 Workers: **2** (o más)
- 📊 Work Units: **X/Y completados**

Si el coordinator **NO** está ejecutando:
- ❌ Coordinator: **INACTIVO**
- Ve a la pestaña **"Control"** para iniciarlo

---

## 📊 PESTAÑA DASHBOARD

**Función:** Vista general del sistema en tiempo real

### Métricas Principales

**📈 Progreso General**
- Barra de progreso visual
- Work units completados vs total
- Work units en progreso
- Work units pendientes

**🏆 Mejor Estrategia**
- PnL (Profit & Loss) del mejor resultado
- Número de trades ejecutados
- Win rate (tasa de victorias)
- Worker que encontró la estrategia

### Tabla de Resultados

Muestra todos los resultados recibidos de los workers:

| Columna | Descripción |
|---------|-------------|
| work_unit_id | ID del trabajo ejecutado |
| pnl | Profit & Loss en USD |
| trades | Número de trades |
| win_rate | Tasa de victorias (0-1) |
| worker_id | Worker que generó el resultado |
| is_canonical | Si es el resultado validado (1) o réplica (0) |
| created_at | Timestamp de creación |

### Botón de Actualización

🔄 **Actualizar Dashboard**: Refresca todos los datos en tiempo real

**Tip:** Deja esta pestaña abierta para monitorear progreso mientras trabajas en otras pestañas

---

## 👥 PESTAÑA WORKERS

**Función:** Ver todos los workers conectados y su estado

### Información por Worker

Cada worker muestra:

**Estado y Conexión:**
- ✅ Estado: Activo / ❌ Inactivo
- IP: Dirección IP del worker
- Plataforma: python-requests/versión

**Rendimiento:**
- Work Units Completados: Total ejecutados
- Última Actividad: Timestamp del último contacto
- Registrado: Cuándo se conectó por primera vez

### Ejemplo de Workers

```
🖥️ Enders-MacBook-Pro.local_Darwin
   Estado: ✅ Activo
   IP: 127.0.0.1
   Plataforma: python-requests/2.32.4
   Work Units Completados: 29
   Última Actividad: 2026-01-31 10:15:23

🖥️ Enders-MacBook-Air.local_Darwin
   Estado: ✅ Activo
   IP: 100.77.179.14
   Plataforma: python-requests/2.32.5
   Work Units Completados: 31
   Última Actividad: 2026-01-31 10:15:25
```

### Botón de Actualización

🔄 **Actualizar Workers**: Refresca la lista de workers

**Nota:** Los workers se actualizan automáticamente cada 30 segundos en el coordinator

---

## ⚙️ PESTAÑA CONTROL

**Función:** Iniciar y detener componentes del sistema

### Sección Coordinator

**Si está ejecutando:**
- ✅ Muestra "Coordinator está ejecutando en puerto 5001"
- 🛑 Botón **"Detener Coordinator"** disponible
- Enlaces al Dashboard y API

**Si NO está ejecutando:**
- ❌ Muestra "Coordinator no está ejecutando"
- ▶️ Botón **"Iniciar Coordinator"** disponible

**Cómo Iniciar:**
1. Click en **"▶️ Iniciar Coordinator"**
2. Espera 3 segundos
3. La página se actualizará automáticamente
4. Verás ✅ en las métricas superiores

**Cómo Detener:**
1. Click en **"🛑 Detener Coordinator"**
2. Se enviará señal SIGTERM al proceso
3. La página se actualizará
4. Verás ❌ en las métricas

### Sección Workers

**MacBook Pro (Local):**

Botones disponibles:
- ▶️ **Iniciar Worker MacBook Pro**: Inicia worker local
- 🛑 **Detener Worker MacBook Pro**: Detiene worker local

**MacBook Air (Remoto):**

Para controlar el worker remoto, necesitas usar SSH:

```bash
# Iniciar
ssh enderj@100.77.179.14 "cd '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude' && ./start_worker.sh http://100.118.215.73:5001"

# Detener
ssh enderj@100.77.179.14 "kill \$(cat '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/worker_air.pid')"
```

**Tip:** Puedes copiar estos comandos desde la interfaz y pegarlos en tu terminal

---

## 📜 PESTAÑA LOGS

**Función:** Ver logs en tiempo real de todos los componentes

### Sub-pestañas

**📡 Coordinator Log**
- Muestra últimas líneas del log del coordinator
- Incluye requests HTTP, asignaciones de trabajo, resultados recibidos
- Slider para ajustar número de líneas (10-200)
- 🔄 Botón para actualizar

**🖥️ Worker MacBook Pro Log**
- Muestra log del worker local
- Incluye progreso de backtests, generaciones, PnLs
- Slider para ajustar líneas
- 🔄 Botón para actualizar

**🌐 Worker MacBook Air Log**
- Instrucciones SSH para acceder al log remoto
- Comando para ver log en tiempo real con `tail -f`

### Ejemplo de Uso

1. Ve a pestaña **"Logs"**
2. Selecciona **"📡 Coordinator"**
3. Ajusta slider a **100 líneas**
4. Click **"🔄 Actualizar Log Coordinator"**
5. Verás las últimas 100 líneas del log

**Logs útiles para:**
- Verificar que workers están conectando
- Ver qué work units se están asignando
- Confirmar recepción de resultados
- Debug de problemas

---

## ➕ PESTAÑA CREAR WORK UNITS

**Función:** Crear nuevos trabajos de búsqueda de estrategias

### Formulario de Creación

**Campos:**

1. **Tamaño de Población** (5-100)
   - Cantidad de estrategias por generación
   - Más población = más diversidad, más tiempo
   - Recomendado: 40-50

2. **Generaciones** (3-100)
   - Número de iteraciones evolutivas
   - Más generaciones = mejor convergencia
   - Recomendado: 25-30

3. **Nivel de Riesgo** (LOW/MEDIUM/HIGH)
   - LOW: Estrategias conservadoras
   - MEDIUM: Balance entre riesgo y retorno
   - HIGH: Estrategias agresivas

4. **Réplicas** (1-5)
   - Cantidad de workers que ejecutarán el mismo trabajo
   - Para validación por redundancia
   - Recomendado: 2

### Cómo Crear Work Unit

1. Ve a pestaña **"➕ Crear Work Units"**
2. Llena el formulario con tus parámetros
3. Click **"➕ Crear Work Unit"**
4. Verás confirmación: "✅ Work Unit #X creado exitosamente!"
5. Los workers automáticamente tomarán el trabajo

### Presets Rápidos

**⚡ Búsqueda Rápida**
- Población: 20
- Generaciones: 15
- Risk: LOW
- Tiempo estimado: ~5-10 minutos

**🎯 Búsqueda Estándar**
- Población: 40
- Generaciones: 30
- Risk: MEDIUM
- Tiempo estimado: ~20-30 minutos

**🔥 Búsqueda Exhaustiva**
- Población: 60
- Generaciones: 50
- Risk: HIGH
- Tiempo estimado: ~60-90 minutos

**Tip:** Usa presets rápidos para pruebas, estándar para producción

---

## 💡 CASOS DE USO COMUNES

### Caso 1: Inicio del Sistema desde Cero

**Objetivo:** Iniciar todo el sistema distribuido

**Pasos:**
1. Abrir interfaz: `streamlit run interface.py`
2. Ir a **"🌐 Sistema Distribuido"**
3. Ir a pestaña **"⚙️ Control"**
4. Click **"▶️ Iniciar Coordinator"** (espera 3s)
5. Click **"▶️ Iniciar Worker MacBook Pro"** (espera 2s)
6. Para worker remoto, usar SSH (comando en interfaz)
7. Verificar en pestaña **"👥 Workers"** que ambos estén activos
8. Ir a **"➕ Crear Work Units"** y crear trabajo
9. Monitorear progreso en **"📊 Dashboard"**

### Caso 2: Crear Búsqueda de Estrategia

**Objetivo:** Crear y monitorear nueva búsqueda

**Pasos:**
1. Verificar que coordinator y workers estén activos (métricas superiores)
2. Ir a **"➕ Crear Work Units"**
3. Configurar:
   - Población: 40
   - Generaciones: 30
   - Risk: MEDIUM
   - Réplicas: 2
4. Click **"➕ Crear Work Unit"**
5. Ir a **"📊 Dashboard"**
6. Click **"🔄 Actualizar Dashboard"** cada minuto
7. Ver tabla de resultados al completarse

### Caso 3: Verificar Progreso de Búsqueda

**Objetivo:** Monitorear búsqueda en ejecución

**Pasos:**
1. Ir a **"📊 Dashboard"**
2. Ver barra de progreso (ej: 50% completado)
3. Ver **"En progreso: 1"** = trabajo ejecutándose
4. Ir a **"📜 Logs"** > **"🖥️ Worker Pro"**
5. Ver líneas como:
   ```
   Gen 15/30
   🚀 Vectorizing Indicators...
   Best PnL: $234.56
   ```
6. Esperar a que "Completados" aumente
7. Verificar resultados en tabla

### Caso 4: Comparar Resultados de Réplicas

**Objetivo:** Ver resultados de validación por redundancia

**Pasos:**
1. Ir a **"📊 Dashboard"**
2. Scroll a tabla de resultados
3. Filtrar por `work_unit_id` (ej: todos los resultados con ID=1)
4. Comparar columna `pnl` entre diferentes `worker_id`
5. Ver `is_canonical=1` para el resultado validado
6. Si PnLs son similares (±10%), hay consenso ✅

### Caso 5: Detener Sistema Completamente

**Objetivo:** Apagar todo el sistema distribuido

**Pasos:**
1. Ir a **"⚙️ Control"**
2. Click **"🛑 Detener Worker MacBook Pro"**
3. Para worker remoto, usar SSH con comando de detener
4. Click **"🛑 Detener Coordinator"**
5. Verificar métricas superiores muestren ❌
6. Cerrar interfaz Streamlit (Ctrl+C en terminal)

### Caso 6: Agregar Más Máquinas

**Objetivo:** Escalar sistema con nuevo worker

**Pasos:**
1. En la nueva máquina:
   ```bash
   cd "ruta/al/proyecto"
   python3 crypto_worker.py http://IP_COORDINATOR:5001
   ```
2. En interfaz, ir a **"👥 Workers"**
3. Click **"🔄 Actualizar Workers"**
4. Verificar nuevo worker aparece en lista ✅
5. Worker automáticamente tomará trabajo disponible

---

## 🔧 TROUBLESHOOTING

### Problema 1: Coordinator Inactivo

**Síntoma:**
- ❌ Coordinator: INACTIVO
- Métricas muestran 0/N/A

**Solución:**
1. Ir a **"⚙️ Control"**
2. Click **"▶️ Iniciar Coordinator"**
3. Si falla, revisar terminal:
   ```bash
   python3 coordinator_port5001.py
   ```
4. Verificar puerto 5001 no esté ocupado:
   ```bash
   lsof -i :5001
   ```

### Problema 2: Workers No Aparecen

**Síntoma:**
- 👥 Workers: 0
- Pestaña Workers está vacía

**Solución:**
1. Verificar workers estén ejecutando:
   ```bash
   ps aux | grep crypto_worker
   ```
2. Revisar logs de workers:
   - **"📜 Logs"** > **"🖥️ Worker Pro"**
3. Verificar workers puedan conectar a coordinator:
   ```bash
   curl http://localhost:5001/api/status
   ```
4. Reiniciar workers desde **"⚙️ Control"**

### Problema 3: Work Units No Completan

**Síntoma:**
- Work units quedan en "En progreso" indefinidamente
- Tabla de resultados vacía

**Solución:**
1. Revisar logs de workers (**"📜 Logs"**)
2. Buscar errores como:
   - `FileNotFoundError` (falta archivo data)
   - `MemoryError` (población muy grande)
   - `Exception in backtest` (error en estrategia)
3. Si hay error, detener workers y coordinator
4. Crear work unit más pequeño (población 10, generaciones 5)
5. Probar nuevamente

### Problema 4: Interfaz No Carga

**Síntoma:**
- Error al abrir http://localhost:8501
- Streamlit no inicia

**Solución:**
1. Verificar dependencias:
   ```bash
   pip install streamlit requests pandas
   ```
2. Reiniciar Streamlit:
   ```bash
   pkill -f streamlit
   streamlit run interface.py
   ```
3. Verificar puerto 8501 no esté ocupado:
   ```bash
   lsof -i :8501
   ```

### Problema 5: Botones de Control No Funcionan

**Síntoma:**
- Click en "Iniciar" o "Detener" no hace nada
- Error en interfaz

**Solución:**
1. Verificar scripts existan:
   ```bash
   ls -la start_coordinator.sh start_worker.sh
   ```
2. Verificar archivos PID:
   ```bash
   ls -la coordinator.pid worker_pro.pid
   ```
3. Si PID file corrupto, eliminar:
   ```bash
   rm coordinator.pid worker_pro.pid
   ```
4. Iniciar manualmente desde terminal:
   ```bash
   ./start_coordinator.sh
   ./start_worker.sh http://localhost:5001
   ```

### Problema 6: Logs No Se Ven

**Síntoma:**
- Pestaña Logs muestra "Log file not found"
- Área de texto vacía

**Solución:**
1. Verificar archivos log existan:
   ```bash
   ls -la coordinator.log worker_pro.log
   ```
2. Si no existen, significa procesos no han iniciado
3. Iniciar coordinator/workers primero
4. Logs se crearán automáticamente

---

## 📚 RECURSOS ADICIONALES

### Documentación Relacionada

- **SISTEMA_DISTRIBUIDO_GUIA_COMPLETA.md**: Guía técnica completa del sistema
- **REPORTE_PRUEBAS_SISTEMA_DISTRIBUIDO.md**: Resultados de pruebas end-to-end
- **SISTEMA_ACTIVO.md**: Comandos y URLs del sistema activo
- **START_HERE.md**: Guía de inicio rápido

### URLs Importantes

- **Interfaz Streamlit:** http://localhost:8501
- **Dashboard Coordinator:** http://localhost:5001
- **API Status:** http://localhost:5001/api/status
- **API Workers:** http://localhost:5001/api/workers
- **API Results:** http://localhost:5001/api/results

### Comandos de Terminal Útiles

```bash
# Ver estado completo
curl -s http://localhost:5001/api/status | python3 -m json.tool

# Ver workers
curl -s http://localhost:5001/api/workers | python3 -m json.tool

# Monitorear logs en tiempo real
tail -f coordinator.log
tail -f worker_pro.log

# Ver procesos
ps aux | grep coordinator
ps aux | grep crypto_worker

# Ver base de datos
sqlite3 coordinator.db "SELECT * FROM work_units"
sqlite3 coordinator.db "SELECT * FROM results ORDER BY pnl DESC LIMIT 10"
```

---

## ✅ CHECKLIST DE INICIO

Usa este checklist cada vez que inicies el sistema:

- [ ] Interfaz Streamlit abierta (`streamlit run interface.py`)
- [ ] Navegado a **"🌐 Sistema Distribuido"**
- [ ] ✅ Coordinator: ACTIVO (si no, iniciar desde Control)
- [ ] ✅ Workers: 2+ activos (si no, iniciar desde Control)
- [ ] Work units creados (desde "➕ Crear Work Units")
- [ ] Dashboard mostrando progreso (pestaña "📊 Dashboard")
- [ ] Logs accesibles (pestaña "📜 Logs")

**¡Sistema listo para usar!** 🎉

---

## 🎯 MEJORES PRÁCTICAS

### Para Búsquedas Eficientes

1. **Empezar pequeño**: Prueba con población 20, generaciones 15
2. **Escalar gradualmente**: Si funciona, aumenta a 40/30
3. **Usar réplicas**: Siempre usa 2 réplicas mínimo para validación
4. **Monitorear logs**: Revisa logs cada 5-10 minutos
5. **No sobrecargar**: Máximo 2-3 work units en paralelo

### Para Estabilidad del Sistema

1. **Verificar recursos**: No saturar CPU/RAM
2. **Mantener workers conectados**: Revisar pestaña Workers
3. **Backup de resultados**: Exportar tabla de resultados periódicamente
4. **Limpiar logs viejos**: Si crecen mucho (>100 MB)
5. **Reiniciar periódicamente**: Una vez al día para refresh

### Para Escalabilidad

1. **Agregar workers gradualmente**: Uno a la vez
2. **Distribuir geográficamente**: Si tienes múltiples ubicaciones
3. **Usar VPN**: Tailscale para conexión segura
4. **Monitorear red**: Verificar latencia entre workers y coordinator
5. **Balancear trabajo**: Crear work units con tamaños similares

---

**¡Disfruta usando el Sistema Distribuido desde la interfaz! 🚀**

**Última actualización:** 31 Enero 2026
**Versión:** 1.0
**Estado:** ✅ Producción
