# 🌐 BÚSQUEDAS DISTRIBUIDAS MULTI-MÁQUINA

**Configuración:** MacBook Pro (local) + PC Gamer (local) + Mac Amiga (remota)

---

## 🎯 CONCEPTO

Ejecutar búsquedas **independientes y automáticas** en múltiples máquinas:

```
📍 Tu Casa:
  ├─ MacBook Pro (esta máquina) - Coordinador
  ├─ MacBook Air (tu otra Mac)
  └─ PC Gamer (Windows)

📍 Otra Ciudad (amiga):
  └─ MacBook amiga

TOTAL: 4 máquinas trabajando simultáneamente
```

**NO necesitas cluster Ray** - cada máquina trabaja independiente.

---

## ✅ QUÉ SE NECESITA

### En TODAS las máquinas:

1. **Python 3.9+** instalado
2. **Dependencias:** pandas, numpy
3. **Archivos del proyecto:**
   - `strategy_miner.py`
   - `backtester.py`
   - `dynamic_strategy.py`
   - `data/BTC-USD_FIVE_MINUTE.csv`
4. **Script de búsqueda** (personalizado por máquina)
5. **Conexión a internet** (para sincronizar resultados)

### En tu MacBook Pro (Coordinador):

6. **Acceso SSH** a todas las máquinas (opcional pero recomendado)
7. **Google Drive** o **Dropbox** compartido (para recolectar resultados)
8. **Script de orquestación** (te lo voy a crear)

---

## 📋 CONFIGURACIÓN POR MÁQUINA

### Máquina 1: MacBook Pro (esta)
```
Role: Coordinador + Ejecutor
Risk Level: MEDIUM
Población: 40
Generaciones: 30
Tiempo: ~45 min
```

### Máquina 2: MacBook Air (tuya)
```
Role: Ejecutor
Risk Level: LOW
Población: 50
Generaciones: 25
Tiempo: ~55 min
```

### Máquina 3: PC Gamer (tu casa)
```
Role: Ejecutor
Risk Level: HIGH
Población: 60
Generaciones: 40
Tiempo: ~60 min (más rápido si tiene buenos specs)
```

### Máquina 4: Mac Amiga (remota)
```
Role: Ejecutor
Risk Level: CONSERVATIVE
Población: 30
Generaciones: 20
Tiempo: ~30 min
```

**TOTAL: 4,900 estrategias evaluadas en ~1 hora**

---

## 🔧 INSTALACIÓN EN CADA MÁQUINA

### PC Gamer (Windows):

```powershell
# 1. Instalar Python
# Descargar de python.org

# 2. Instalar dependencias
pip install pandas numpy

# 3. Crear carpeta proyecto
mkdir C:\BittraderMiner
cd C:\BittraderMiner

# 4. Recibir archivos (te los envío después)
```

### Mac Amiga (remota):

```bash
# 1. Verificar Python
python3 --version

# 2. Instalar dependencias
pip3 install pandas numpy

# 3. Crear carpeta
mkdir -p ~/BittraderMiner
cd ~/BittraderMiner

# 4. Recibir archivos (te los envío después)
```

---

## 📦 PREPARACIÓN DE ARCHIVOS

### Paso 1: Crear paquete para distribución

```bash
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

# Crear carpeta para paquete
mkdir -p ~/Desktop/BittraderMiner_Package

# Copiar archivos esenciales
cp strategy_miner.py ~/Desktop/BittraderMiner_Package/
cp backtester.py ~/Desktop/BittraderMiner_Package/
cp dynamic_strategy.py ~/Desktop/BittraderMiner_Package/
cp -r data ~/Desktop/BittraderMiner_Package/

# Crear scripts personalizados (los creo después)
```

### Paso 2: Comprimir y compartir

```bash
cd ~/Desktop
zip -r BittraderMiner_Package.zip BittraderMiner_Package/

# Enviar por:
# - Google Drive compartido
# - WeTransfer
# - Email (si es <25MB)
# - Dropbox
```

---

## 🚀 EJECUCIÓN AUTOMÁTICA

### Opción A: Manual coordinada (SIMPLE)

**Acuerdo:** Todos ejecutan a la misma hora

```bash
# Mensaje a todos: "Ejecutamos a las 8:00 PM"

# 8:00 PM - Todos ejecutan:
python3 run_miner_[MAQUINA].py
```

**Ventaja:** Simple
**Desventaja:** Requiere coordinación manual

---

### Opción B: SSH automático (SEMI-AUTOMÁTICO) ⭐

**Solo para máquinas locales (PC Gamer, MacBook Air)**

```bash
# Desde MacBook Pro, un solo comando inicia todo:

# Script master (te lo creo después)
./run_all_local.sh

# Internamente hace:
# 1. Ejecuta en MacBook Pro (local)
# 2. SSH a MacBook Air → ejecuta búsqueda
# 3. SSH a PC Gamer → ejecuta búsqueda
# 4. Notifica a Mac amiga (email/Slack)
```

**Ventaja:** Un comando inicia todo local
**Desventaja:** Mac amiga debe ejecutar manualmente

---

### Opción C: Carpeta compartida + Cron (TOTALMENTE AUTOMÁTICO) ⭐⭐⭐

**Setup:**

1. **Google Drive compartido** con todas las máquinas
2. **Cron job** en cada máquina
3. **Archivo de control** para coordinar

```bash
# En cada máquina:
# Cron job que revisa cada 5 minutos si debe ejecutar

# Archivo de control en Google Drive:
# run_config.json

{
  "execute_at": "2026-01-30T20:00:00",
  "machines": {
    "macbook_pro": { "status": "pending", "script": "run_miner_PRO.py" },
    "macbook_air": { "status": "pending", "script": "run_miner_AIR.py" },
    "pc_gamer": { "status": "pending", "script": "run_miner_GAMER.py" },
    "mac_amiga": { "status": "pending", "script": "run_miner_AMIGA.py" }
  }
}

# Cada máquina:
# 1. Lee run_config.json cada 5 min
# 2. Si llegó la hora → ejecuta su script
# 3. Guarda resultados en Google Drive
# 4. Actualiza status a "completed"
```

**Ventaja:** 100% automático, programable
**Desventaja:** Setup inicial más complejo

---

## 📊 RECOLECCIÓN DE RESULTADOS

### Estrategia: Google Drive compartido

```
Google Drive/BittraderResults/
├── MacBookPro/
│   ├── BEST_STRATEGY_PRO_[timestamp].json
│   └── all_strategies_PRO_[timestamp].json
├── MacBookAir/
│   ├── BEST_STRATEGY_AIR_[timestamp].json
│   └── all_strategies_AIR_[timestamp].json
├── PCGamer/
│   ├── BEST_STRATEGY_GAMER_[timestamp].json
│   └── all_strategies_GAMER_[timestamp].json
└── MacAmiga/
    ├── BEST_STRATEGY_AMIGA_[timestamp].json
    └── all_strategies_AMIGA_[timestamp].json
```

### Script de análisis automático:

```python
# compare_all_results.py
# Lee todos los archivos de Google Drive
# Compara las 4 estrategias
# Genera reporte consolidado
# Envía por email
```

---

## 🎯 PLAN DE IMPLEMENTACIÓN

### FASE 1: Setup Básico (30 min)

**Para ti (ahora):**
1. Crear scripts personalizados para cada máquina
2. Empaquetar archivos
3. Compartir en Google Drive

**Para cada máquina:**
1. Descargar paquete
2. Instalar Python + dependencias
3. Probar script con 1 generación (test rápido)

---

### FASE 2: Primera ejecución coordinada (1 hora)

**Todos ejecutan manualmente:**
- Acordar hora (ej: 8:00 PM)
- Todos ejecutan su script
- Esperan ~1 hora
- Suben resultados a Google Drive

**Tú analizas:**
- Descargas todos los JSON
- Ejecutas compare_all_results.py
- Ves ganador

---

### FASE 3: Automatización (opcional, 2 horas)

**Implementar Opción C:**
1. Configurar Google Drive sync en todas las máquinas
2. Crear cron jobs
3. Crear archivo de control
4. Probar ejecución automática
5. Configurar notificaciones (email/Slack)

---

## 🔐 SEGURIDAD Y COORDINACIÓN

### Para Mac Amiga (remota):

**Opción 1: Email automático**
```python
# Tu MacBook Pro envía email:
# "Búsqueda programada para 8:00 PM - ejecuta run_miner_AMIGA.py"
```

**Opción 2: Slack/Discord**
```bash
# Bot notifica en canal compartido
# "🚀 Iniciando búsqueda distribuida en 10 minutos"
```

**Opción 3: Google Drive watcher**
```python
# Script en Mac amiga:
# Revisa Google Drive cada 5 min
# Si ve archivo "START_SEARCH.txt" → ejecuta
```

---

## 💡 VENTAJAS DE ESTE SISTEMA

✅ **Sin cluster Ray** - No problemas de compatibilidad
✅ **Cada máquina independiente** - Si una falla, otras continúan
✅ **Escalable** - Agregar más máquinas es trivial
✅ **Flexible** - Cada máquina con su configuración
✅ **Económico** - No necesitas servidores cloud
✅ **Geográficamente distribuido** - Diferentes ciudades OK

---

## 📊 CAPACIDAD TOTAL

Con las 4 máquinas:

| Máquina | Población | Generaciones | Estrategias | Tiempo |
|---------|-----------|--------------|-------------|--------|
| MacBook Pro | 40 | 30 | 1,200 | 45 min |
| MacBook Air | 50 | 25 | 1,250 | 55 min |
| PC Gamer | 60 | 40 | 2,400 | 60 min |
| Mac Amiga | 30 | 20 | 600 | 30 min |
| **TOTAL** | - | - | **5,450** | **~1 hora** |

**Comparación:**
- Búsqueda simple: 600 estrategias en 27 min
- Este sistema: **5,450 estrategias en 60 min**
- **9x más exploración** del espacio de búsqueda

---

## 🚧 CONSIDERACIONES

### PC Gamer (Windows):

**Python en Windows es ligeramente diferente:**
```powershell
# Windows usa:
python run_miner_GAMER.py

# (no python3)
```

**Rutas de archivos:**
```python
# Windows usa backslashes
data_path = "data\\BTC-USD_FIVE_MINUTE.csv"

# O mejor (compatible):
import os
data_path = os.path.join("data", "BTC-USD_FIVE_MINUTE.csv")
```

### Mac Amiga (confianza):

**Consideraciones:**
- ¿Confías en compartir los datos BTC? (son públicos, OK)
- ¿Confías en el código? (es tuyo, OK)
- ¿Ella entiende qué está ejecutando? (explícale)
- ¿Tiempo de máquina está OK? (1 hora de CPU)

**Alternativa:** Solo usa las 3 máquinas tuyas (sigue siendo 4,850 estrategias)

---

## 🎁 LO QUE VOY A CREAR PARA TI

1. **`run_miner_GAMER.py`** - Script para PC Windows (HIGH risk)
2. **`run_miner_AMIGA.py`** - Script para Mac remota (CONSERVATIVE)
3. **`compare_all_results.py`** - Analizador de 4+ máquinas
4. **`distribute_package.sh`** - Script para empaquetar todo
5. **`run_all_local.sh`** - Ejecutar todo local con un comando
6. **`INSTRUCCIONES_SETUP_WINDOWS.md`** - Guía para PC Gamer
7. **`INSTRUCCIONES_SETUP_REMOTO.md`** - Guía para Mac amiga

---

## ❓ PREGUNTAS PARA TI

Antes de crear todo, necesito saber:

1. **PC Gamer specs:**
   - ¿Cuántos cores tiene?
   - ¿Windows 10/11?
   - ¿Ya tiene Python instalado?

2. **Mac Amiga:**
   - ¿Ella está de acuerdo?
   - ¿Tiene conocimientos técnicos?
   - ¿Prefieres instrucciones muy detalladas?

3. **Método preferido:**
   - A) Manual coordinado (simple)
   - B) SSH automático local (semi-auto)
   - C) Google Drive + Cron (totalmente auto)

4. **Prioridad:**
   - ¿Quieres esto AHORA o después de probar con 2 máquinas primero?

---

## 🚀 RESPUESTA DIRECTA

**Pregunta:** ¿Puedo agregar PC Gamer local + Mac amiga remota?

**Respuesta:** **SÍ, totalmente posible.**

**Qué se necesita:**
- Instalar Python + dependencias en cada máquina
- Copiar archivos del proyecto
- Ejecutar scripts personalizados
- Recolectar resultados (manual o automático)

**Complejidad:**
- Básico (manual): 30 min setup
- Automático completo: 2-3 horas setup inicial

**Resultado:**
- 5,450 estrategias en ~1 hora
- 9x más que búsqueda simple

---

¿Quieres que cree los scripts y documentación completa para este setup de 4 máquinas?