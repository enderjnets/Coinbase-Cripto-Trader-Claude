#!/usr/bin/env python3
"""
Status Check - Verificación rápida del estado del sistema
Ejecuta una serie de checks para confirmar que todo está listo
"""

import os
import sys
from datetime import datetime

print("\n" + "="*80)
print("🔍 STRATEGY MINER - STATUS CHECK")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

checks_passed = 0
checks_total = 0

def check(name, condition, message_ok, message_fail, critical=True):
    global checks_passed, checks_total
    checks_total += 1

    if condition:
        checks_passed += 1
        print(f"✅ {name}")
        if message_ok:
            print(f"   {message_ok}")
        return True
    else:
        emoji = "❌" if critical else "⚠️ "
        print(f"{emoji} {name}")
        print(f"   {message_fail}")
        return False

print("📋 VERIFICANDO SISTEMA...\n")

# Check 1: Python Version
try:
    import sys
    version = sys.version_info
    version_ok = version.major == 3 and version.minor >= 9
    check(
        "Python Version",
        version_ok,
        f"Python {version.major}.{version.minor}.{version.micro}",
        f"Se requiere Python 3.9+, tienes {version.major}.{version.minor}",
        critical=True
    )
except Exception as e:
    check("Python Version", False, None, str(e), critical=True)

print()

# Check 2: Ray Instalado
try:
    import ray
    check(
        "Ray Instalado",
        True,
        f"Ray versión {ray.__version__}",
        "Ray no está instalado",
        critical=True
    )
except ImportError:
    check("Ray Instalado", False, None, "Instalar con: pip install ray", critical=True)

print()

# Check 3: Pandas Instalado
try:
    import pandas as pd
    check(
        "Pandas Instalado",
        True,
        f"Pandas versión {pd.__version__}",
        "Pandas no está instalado",
        critical=True
    )
except ImportError:
    check("Pandas Instalado", False, None, "Instalar con: pip install pandas", critical=True)

print()

# Check 4: Archivos de Código Principal
base_path = os.path.dirname(os.path.abspath(__file__))

files_to_check = [
    "strategy_miner.py",
    "optimizer.py",
    "backtester.py",
    "dynamic_strategy.py",
    "interface.py"
]

print("📂 VERIFICANDO ARCHIVOS DE CÓDIGO...\n")

for fname in files_to_check:
    fpath = os.path.join(base_path, fname)
    exists = os.path.exists(fpath)

    size = ""
    if exists:
        size = f"{os.path.getsize(fpath) / 1024:.1f} KB"

    check(
        fname,
        exists,
        f"Tamaño: {size}",
        f"No encontrado en {base_path}",
        critical=True
    )

print()

# Check 5: Datos
print("📊 VERIFICANDO DATOS...\n")

data_file = os.path.join(base_path, "data", "BTC-USD_FIVE_MINUTE.csv")
data_exists = os.path.exists(data_file)

if data_exists:
    size_mb = os.path.getsize(data_file) / (1024 * 1024)
    check(
        "Dataset BTC-USD (5 min)",
        size_mb > 3.0 and size_mb < 5.0,
        f"Tamaño: {size_mb:.1f} MB",
        f"Tamaño inesperado: {size_mb:.1f} MB (debería ser ~3.9 MB)",
        critical=False
    )
else:
    check(
        "Dataset BTC-USD (5 min)",
        False,
        None,
        f"No encontrado en {data_file}",
        critical=True
    )

print()

# Check 6: .env
print("⚙️  VERIFICANDO CONFIGURACIÓN...\n")

env_file = os.path.join(base_path, ".env")
env_exists = os.path.exists(env_file)

check(
    "Archivo .env",
    env_exists,
    "Configurado",
    f"No encontrado en {base_path}",
    critical=False
)

if env_exists:
    with open(env_file, 'r') as f:
        env_content = f.read()

    has_ray_address = "RAY_ADDRESS" in env_content
    check(
        "RAY_ADDRESS configurado",
        has_ray_address,
        "100.77.179.14:6379",
        "Variable RAY_ADDRESS no encontrada en .env",
        critical=False
    )

print()

# Check 7: Scripts de Test
print("🧪 VERIFICANDO SCRIPTS DE TEST...\n")

test_scripts = [
    "test_miner_local.py",
    "test_miner_productive.py",
    "validate_cluster.py"
]

for script in test_scripts:
    spath = os.path.join(base_path, script)
    exists = os.path.exists(spath)
    check(
        script,
        exists,
        "Listo para ejecutar",
        f"No encontrado",
        critical=False
    )

print()

# Check 8: Documentación
print("📚 VERIFICANDO DOCUMENTACIÓN...\n")

docs = [
    "RESUMEN_EJECUTIVO.md",
    "INSTRUCCIONES_USUARIO.md",
    "MINER_STATUS_REPORT.md",
    "DIAGNOSTIC_REPORT.md",
    "CONFIGURACIONES_RECOMENDADAS.json"
]

for doc in docs:
    dpath = os.path.join(base_path, doc)
    exists = os.path.exists(dpath)
    check(
        doc,
        exists,
        "Disponible",
        "No encontrado",
        critical=False
    )

print()

# Check 9: Worker Daemon
print("🔧 VERIFICANDO WORKER DAEMON...\n")

worker_status_file = os.path.expanduser("~/.bittrader_worker/status")
worker_exists = os.path.exists(worker_status_file)

if worker_exists:
    with open(worker_status_file, 'r') as f:
        worker_status = f.read().strip()

    is_connected = 'connected' in worker_status
    check(
        "Worker Daemon Status",
        is_connected,
        f"Status: {worker_status}",
        f"Status: {worker_status} (no conectado)",
        critical=False
    )
else:
    check(
        "Worker Daemon",
        False,
        None,
        "Status file no encontrado (daemon no instalado o no corriendo)",
        critical=False
    )

print()

# Check 10: Streamlit
print("🌐 VERIFICANDO STREAMLIT...\n")

import subprocess

try:
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )

    streamlit_running = "streamlit run interface.py" in result.stdout

    if streamlit_running:
        # Extraer PID
        lines = result.stdout.split('\n')
        for line in lines:
            if "streamlit run interface.py" in line:
                parts = line.split()
                if len(parts) > 1:
                    pid = parts[1]
                    break

        check(
            "Streamlit Interface",
            streamlit_running,
            f"Corriendo en PID {pid}, puerto 8501",
            None,
            critical=False
        )
    else:
        check(
            "Streamlit Interface",
            False,
            None,
            "No está corriendo. Iniciar con: streamlit run interface.py",
            critical=False
        )
except Exception as e:
    check("Streamlit Interface", False, None, f"Error verificando: {e}", critical=False)

print()

# Check 11: Ray Local
print("⚡ VERIFICANDO RAY...\n")

try:
    # Intentar inicializar Ray local
    import ray

    if ray.is_initialized():
        print("⚠️  Ray ya está inicializado")
        print("   (Probablemente de una sesión anterior)")
        resources = ray.cluster_resources()
        cpus = int(resources.get('CPU', 0))
        print(f"   CPUs disponibles: {cpus}\n")
        checks_passed += 1
        checks_total += 1
    else:
        # Test de inicialización
        ray.init(address='local', num_cpus=2, ignore_reinit_error=True, logging_level="ERROR")
        resources = ray.cluster_resources()
        cpus = int(resources.get('CPU', 0))
        ray.shutdown()

        check(
            "Ray Funcional",
            cpus >= 2,
            f"Puede inicializar con {cpus} CPUs",
            "No pudo inicializar correctamente",
            critical=True
        )
except Exception as e:
    check("Ray Funcional", False, None, f"Error: {e}", critical=True)

print()

# RESUMEN FINAL
print("="*80)
print("📊 RESUMEN")
print("="*80 + "\n")

success_rate = (checks_passed / checks_total) * 100
print(f"Checks Pasados: {checks_passed}/{checks_total} ({success_rate:.0f}%)\n")

if success_rate == 100:
    print("🎉 SISTEMA COMPLETAMENTE FUNCIONAL")
    print("\n✅ Todo listo para ejecutar:")
    print("   python3 test_miner_productive.py\n")
    exit_code = 0

elif success_rate >= 80:
    print("✅ SISTEMA MAYORMENTE FUNCIONAL")
    print("\n⚠️  Algunos checks no pasaron, pero el sistema debería funcionar")
    print("   Revisa los warnings arriba para detalles\n")
    print("✅ Puedes ejecutar:")
    print("   python3 test_miner_productive.py\n")
    exit_code = 0

elif success_rate >= 60:
    print("⚠️  SISTEMA PARCIALMENTE FUNCIONAL")
    print("\n⚠️  Varios checks fallaron. El sistema puede tener problemas")
    print("   Revisa los errores arriba antes de continuar\n")
    exit_code = 1

else:
    print("❌ SISTEMA NO FUNCIONAL")
    print("\n❌ Muchos checks críticos fallaron")
    print("   Revisa la instalación y configuración del sistema\n")
    exit_code = 1

print("="*80 + "\n")

# Instrucciones según el resultado
if success_rate >= 80:
    print("📋 PRÓXIMOS PASOS RECOMENDADOS:\n")
    print("1. Lee RESUMEN_EJECUTIVO.md (2 minutos)")
    print("2. Ejecuta: python3 test_miner_productive.py")
    print("3. Espera ~60 minutos")
    print("4. Revisa resultados en BEST_STRATEGY_*.json\n")
else:
    print("🔧 ACCIONES REQUERIDAS:\n")
    print("1. Revisa los errores marcados con ❌ arriba")
    print("2. Consulta INSTRUCCIONES_USUARIO.md")
    print("3. Ejecuta nuevamente este script para verificar\n")

sys.exit(exit_code)
