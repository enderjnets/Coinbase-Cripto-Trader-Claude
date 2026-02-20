# 📚 ÍNDICE - Sistema Distribuido y Archivos del Proyecto

**Fecha:** 30 Enero 2026
**Proyecto:** Strategy Miner - Sistema Distribuido BOINC

---

## 🎯 EMPEZAR AQUÍ

**Nuevo en el proyecto?** Lee estos archivos en orden:

1. **`RESUMEN_FINAL_USUARIO.md`** ⭐⭐⭐⭐⭐
   - Resumen ejecutivo de todo
   - Resultados de búsquedas
   - Qué sistema usar
   - **EMPIEZA AQUÍ**

2. **`INFORME_TRABAJO_AUTONOMO_SISTEMA_DISTRIBUIDO.md`** ⭐⭐⭐⭐
   - Detalle completo del trabajo autónomo
   - Qué se implementó
   - Comparación de sistemas

3. **`SISTEMA_DISTRIBUIDO_GUIA_COMPLETA.md`** ⭐⭐⭐⭐⭐
   - Guía maestra (800+ líneas)
   - Arquitectura completa
   - Instalación paso a paso
   - Troubleshooting

---

## 📂 ESTRUCTURA DEL PROYECTO

```
Coinbase Cripto Trader Claude/
│
├── 🧬 SISTEMA DISTRIBUIDO BOINC (Nuevo)
│   ├── coordinator.py                    # Servidor central (570 líneas)
│   ├── crypto_worker.py                  # Cliente worker (320 líneas)
│   ├── start_coordinator.sh              # Inicio rápido servidor
│   ├── start_worker.sh                   # Inicio rápido worker
│   ├── test_sistema_distribuido.sh       # Suite de tests
│   └── coordinator.db                    # Base de datos (se crea al ejecutar)
│
├── 🔄 SISTEMA DE BÚSQUEDAS PARALELAS (Actual)
│   ├── run_miner_PRO.py                  # Miner MacBook Pro
│   ├── run_miner_AIR.py                  # Miner MacBook Air
│   ├── run_miner_NO_RAY.py               # Miner secuencial original
│   ├── compare_results.py                # Comparador de resultados
│   ├── monitor_progress.sh               # Monitor en tiempo real
│   ├── STATUS_PRO.txt                    # Estado MacBook Pro
│   └── STATUS_AIR.txt                    # Estado MacBook Air (en AIR)
│
├── 🧠 MOTOR DE MINERÍA
│   ├── strategy_miner.py                 # Motor genético principal
│   ├── backtester.py                     # Motor de backtesting
│   └── dynamic_strategy.py               # Estrategia dinámica
│
├── 💾 DATOS
│   └── data/
│       └── BTC-USD_FIVE_MINUTE.csv       # 59,207 velas, 3.9 MB
│
├── 📊 RESULTADOS
│   ├── BEST_STRATEGY_PRO_*.json          # Mejores estrategias Pro
│   ├── BEST_STRATEGY_AIR_*.json          # Mejores estrategias Air
│   ├── BEST_STRATEGY_NO_RAY_*.json       # Estrategias búsqueda original
│   ├── all_strategies_PRO_*.json         # Históricos completos Pro
│   ├── all_strategies_AIR_*.json         # Históricos completos Air
│   └── all_strategies_NO_RAY_*.json      # Históricos originales
│
├── 💾 BACKUP
│   ├── BACKUP_BUSQUEDAS_PARALELAS_20260130_230900/  # Carpeta backup
│   │   ├── README_RESTAURACION.md       # Guía de restauración
│   │   ├── RESTORE.sh                    # Script automático
│   │   ├── *.py (8 scripts)
│   │   ├── *.md (34 documentos)
│   │   ├── *.json (28 resultados)
│   │   └── data/                         # Datos BTC
│   ├── BACKUP_BUSQUEDAS_PARALELAS_20260130_230900.tar.gz  # Comprimido (1.5 MB)
│   └── RESUMEN_BACKUP_SISTEMA_PARALELO.md
│
└── 📖 DOCUMENTACIÓN
    ├── INDICE_SISTEMA_DISTRIBUIDO.md           # Este archivo
    ├── RESUMEN_FINAL_USUARIO.md                # ⭐ EMPIEZA AQUÍ
    ├── INFORME_TRABAJO_AUTONOMO_SISTEMA_DISTRIBUIDO.md
    ├── SISTEMA_DISTRIBUIDO_GUIA_COMPLETA.md    # Guía maestra
    ├── INVESTIGACION_SETI_AT_HOME_BOINC.md     # Research BOINC
    ├── INSTRUCCIONES_BUSQUEDAS_PARALELAS.md    # Guía paralelas
    ├── RESPUESTA_SOBRE_CLUSTER.md              # Por qué Ray no funcionó
    ├── PROBLEMA_CLUSTER_MACOS.md               # Limitaciones macOS
    ├── BUSQUEDAS_DISTRIBUIDAS_MULTI_MAQUINA.md # Plan 4 máquinas
    ├── REPORTE_AUTONOMO_MINER.md               # Búsqueda original
    └── ... (30+ documentos adicionales)
```

---

## 🚀 ARCHIVOS PRINCIPALES POR CASO DE USO

### Quiero ejecutar búsqueda simple (2-3 máquinas)

**Archivos necesarios:**
- `run_miner_PRO.py`
- `run_miner_AIR.py`
- `compare_results.py`
- `monitor_progress.sh`

**Documentación:**
- `INSTRUCCIONES_BUSQUEDAS_PARALELAS.md`

**Comandos:**
```bash
python3 run_miner_PRO.py
python3 run_miner_AIR.py  # En otra máquina
python3 compare_results.py
```

---

### Quiero sistema distribuido escalable (10+ máquinas)

**Archivos necesarios:**
- `coordinator.py`
- `crypto_worker.py`
- `start_coordinator.sh`
- `start_worker.sh`

**Documentación:**
- `SISTEMA_DISTRIBUIDO_GUIA_COMPLETA.md`
- `INVESTIGACION_SETI_AT_HOME_BOINC.md`

**Comandos:**
```bash
./start_coordinator.sh
./start_worker.sh http://COORDINATOR_IP:5000
open http://localhost:5000
```

---

### Quiero entender qué pasó

**Lee en orden:**
1. `RESUMEN_FINAL_USUARIO.md` - Overview completo
2. `INFORME_TRABAJO_AUTONOMO_SISTEMA_DISTRIBUIDO.md` - Detalles
3. `SISTEMA_DISTRIBUIDO_GUIA_COMPLETA.md` - Guía técnica

---

### Quiero restaurar sistema anterior

**Archivos necesarios:**
- `BACKUP_BUSQUEDAS_PARALELAS_20260130_230900/`
- `BACKUP_BUSQUEDAS_PARALELAS_20260130_230900.tar.gz`

**Documentación:**
- `RESUMEN_BACKUP_SISTEMA_PARALELO.md`
- `BACKUP_BUSQUEDAS_PARALELAS_20260130_230900/README_RESTAURACION.md`

**Comandos:**
```bash
cd BACKUP_BUSQUEDAS_PARALELAS_20260130_230900
./RESTORE.sh
```

---

## 📖 DOCUMENTACIÓN POR TEMA

### Sistema Distribuido

- **`SISTEMA_DISTRIBUIDO_GUIA_COMPLETA.md`** - Guía maestra (800+ líneas)
- **`INVESTIGACION_SETI_AT_HOME_BOINC.md`** - Arquitectura BOINC (800+ líneas)
- **`coordinator.py`** - Código servidor (570 líneas, bien comentado)
- **`crypto_worker.py`** - Código worker (320 líneas, bien comentado)

### Búsquedas Paralelas

- **`INSTRUCCIONES_BUSQUEDAS_PARALELAS.md`** - Guía paso a paso
- **`BUSQUEDAS_DISTRIBUIDAS_MULTI_MAQUINA.md`** - Plan 4 máquinas
- **`run_miner_PRO.py`** - Código ejemplo (230 líneas)
- **`run_miner_AIR.py`** - Código ejemplo (230 líneas)

### Problemas y Soluciones

- **`RESPUESTA_SOBRE_CLUSTER.md`** - Por qué cluster sí sirve (pero no en macOS)
- **`PROBLEMA_CLUSTER_MACOS.md`** - Limitaciones de Ray en macOS
- **`SISTEMA_DISTRIBUIDO_GUIA_COMPLETA.md`** - Sección Troubleshooting

### Resultados y Análisis

- **`REPORTE_AUTONOMO_MINER.md`** - Análisis búsqueda original
- **`compare_results.py`** - Script de comparación
- **`BEST_STRATEGY_*.json`** - Archivos de resultados

---

## 🔧 SCRIPTS Y HERRAMIENTAS

### Scripts de Ejecución

| Script | Propósito | Uso |
|--------|-----------|-----|
| `start_coordinator.sh` | Inicia servidor distribuido | `./start_coordinator.sh` |
| `start_worker.sh` | Inicia worker | `./start_worker.sh http://IP:5000` |
| `monitor_progress.sh` | Monitor búsquedas paralelas | `./monitor_progress.sh` |
| `test_sistema_distribuido.sh` | Suite de tests | `./test_sistema_distribuido.sh` |

### Scripts de Minería

| Script | Risk Level | Población | Generaciones | Tiempo |
|--------|------------|-----------|--------------|--------|
| `run_miner_PRO.py` | MEDIUM | 40 | 30 | ~45 min |
| `run_miner_AIR.py` | LOW | 50 | 25 | ~55 min |
| `run_miner_NO_RAY.py` | MEDIUM | 30 | 20 | ~27 min |

### Scripts de Análisis

| Script | Propósito |
|--------|-----------|
| `compare_results.py` | Compara resultados de múltiples búsquedas |
| `coordinator.py` | Dashboard web + API + Validación |

---

## 📊 RESULTADOS DISPONIBLES

### Búsqueda MacBook PRO (COMPLETADA)

```
Archivo: BEST_STRATEGY_PRO_1769839513.json
PnL: $70.73
Trades: 16
Win Rate: 37.5%
Estrategia: close < SMA(100) AND RSI(20) > 75
Tiempo: 57 minutos
```

### Búsqueda MacBook AIR (EN PROGRESO)

```
Estado: 96% completado
Mejor PnL: $78.12
ETA: ~5 minutos
```

### Búsqueda Original (NO_RAY)

```
Archivo: BEST_STRATEGY_NO_RAY_1769815729.json
PnL: $154.99
Trades: 2
Win Rate: 100%
Estrategia: RSI(100) < 30 AND close > EMA(14)
Tiempo: 27 minutos
```

---

## 🆘 AYUDA RÁPIDA

### ¿Qué archivo debo leer primero?

**`RESUMEN_FINAL_USUARIO.md`** - Todo lo que necesitas saber en un archivo.

### ¿Cómo ejecuto el sistema distribuido?

```bash
./test_sistema_distribuido.sh  # Verificar todo está OK
./start_coordinator.sh          # Iniciar servidor
./start_worker.sh http://localhost:5000  # Iniciar worker
```

### ¿Cómo vuelvo al sistema anterior?

```bash
cd BACKUP_BUSQUEDAS_PARALELAS_20260130_230900
./RESTORE.sh
```

### ¿Dónde está la documentación técnica?

**`SISTEMA_DISTRIBUIDO_GUIA_COMPLETA.md`** - 800+ líneas, todo explicado.

### ¿Cómo analizo los resultados actuales?

```bash
python3 compare_results.py
```

---

## 🎯 COMANDOS MÁS ÚTILES

### Sistema Distribuido

```bash
# Test completo
./test_sistema_distribuido.sh

# Iniciar servidor
./start_coordinator.sh

# Iniciar worker
./start_worker.sh http://100.118.215.73:5000

# Ver dashboard
open http://localhost:5000

# Ver estado
curl http://localhost:5000/api/status | python3 -m json.tool
```

### Búsquedas Paralelas

```bash
# MacBook Pro
python3 run_miner_PRO.py

# MacBook Air (vía SSH)
ssh enderj@100.77.179.14 "python3 run_miner_AIR.py"

# Monitorear
./monitor_progress.sh

# Comparar resultados
python3 compare_results.py
```

### Backup y Restauración

```bash
# Restaurar backup
cd BACKUP_BUSQUEDAS_PARALELAS_20260130_230900
./RESTORE.sh

# Ver contenido del backup
tar -tzf BACKUP_BUSQUEDAS_PARALELAS_20260130_230900.tar.gz | head -20
```

---

## 📞 CONTACTO Y SOPORTE

### Documentos de Ayuda

- **Problemas con cluster Ray:** `PROBLEMA_CLUSTER_MACOS.md`
- **Troubleshooting distribuido:** `SISTEMA_DISTRIBUIDO_GUIA_COMPLETA.md` (sección Troubleshooting)
- **Preguntas sobre BOINC:** `INVESTIGACION_SETI_AT_HOME_BOINC.md`

### Logs y Debugging

```bash
# Logs de coordinator
# Se muestran en terminal al ejecutar

# Logs de worker
# Se muestran en terminal al ejecutar

# Logs de búsquedas paralelas
tail -f miner_PRO_*.log
ssh enderj@100.77.179.14 "tail -f miner_AIR_*.log"

# Base de datos
sqlite3 coordinator.db
```

---

## 📈 ESTADÍSTICAS DEL PROYECTO

**Total de archivos creados:** 10+
**Total líneas de código:** ~1,200
**Total líneas de documentación:** ~3,000+
**Sistemas implementados:** 2 (Paralelas + Distribuido)
**Tests automatizados:** 7
**Tiempo de implementación:** ~1 hora

---

## ✅ CHECKLIST RÁPIDO

**Sistema listo si:**
- [ ] `./test_sistema_distribuido.sh` pasa todos los tests
- [ ] Tienes archivo `coordinator.py`
- [ ] Tienes archivo `crypto_worker.py`
- [ ] Flask está instalado
- [ ] Datos BTC disponibles

**Sistema paralelas listo si:**
- [ ] Tienes `run_miner_PRO.py` y `run_miner_AIR.py`
- [ ] Tienes `compare_results.py`
- [ ] pandas y numpy instalados
- [ ] Datos BTC disponibles

---

## 🎉 RESUMEN

**Tienes acceso a:**
✅ 2 sistemas completos de minería distribuida
✅ Backup seguro del sistema anterior
✅ 3,000+ líneas de documentación
✅ Suite de tests automáticos
✅ Scripts de inicio rápido
✅ Resultados de búsquedas (1 completo, 1 en progreso)

**Puedes:**
✅ Ejecutar búsquedas en 2-3 máquinas (paralelas)
✅ Escalar a 10+ máquinas (distribuido)
✅ Monitorear todo vía dashboard web
✅ Restaurar sistema anterior cuando quieras

---

**🤖 Índice creado - 30 Enero 2026**

**EMPIEZA POR:** `RESUMEN_FINAL_USUARIO.md`
