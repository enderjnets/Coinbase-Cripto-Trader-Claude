#!/usr/bin/env python3
"""
Test script para verificar integración de la interfaz con el sistema distribuido
"""

import requests
import sqlite3
import os
import json

COORDINATOR_URL = "http://localhost:5001"

def test_coordinator_api():
    """Test 1: Verificar conectividad con Coordinator API"""
    print("🧪 TEST 1: Coordinator API Status")
    try:
        response = requests.get(f"{COORDINATOR_URL}/api/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status API: OK")
            print(f"   - Workers activos: {data.get('workers', {}).get('active', 0)}")
            print(f"   - Work units: {data.get('work_units', {}).get('total', 0)}")
            return True
        else:
            print(f"   ❌ Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def test_workers_api():
    """Test 2: Verificar Workers API"""
    print("\n🧪 TEST 2: Workers API")
    try:
        response = requests.get(f"{COORDINATOR_URL}/api/workers", timeout=2)
        if response.status_code == 200:
            data = response.json()
            workers = data.get('workers', [])
            print(f"   ✅ Workers API: OK")
            print(f"   - Total workers: {len(workers)}")
            for worker in workers:
                print(f"   - {worker.get('id')}: {worker.get('status')}")
            return True
        else:
            print(f"   ❌ Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def test_results_api():
    """Test 3: Verificar Results API"""
    print("\n🧪 TEST 3: Results API")
    try:
        response = requests.get(f"{COORDINATOR_URL}/api/results", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Results API: OK")
            print(f"   - Total resultados: {len(data)}")
            return True
        else:
            print(f"   ❌ Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def test_log_files():
    """Test 4: Verificar acceso a archivos de log"""
    print("\n🧪 TEST 4: Archivos de Log")
    log_files = {
        "coordinator.log": "Coordinator",
        "worker_pro.log": "Worker MacBook Pro"
    }

    all_ok = True
    for log_file, name in log_files.items():
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    print(f"   ✅ {name}: {len(lines)} líneas")
            except Exception as e:
                print(f"   ❌ {name}: Error al leer - {str(e)}")
                all_ok = False
        else:
            print(f"   ⚠️  {name}: Archivo no encontrado")

    return all_ok

def test_database_access():
    """Test 5: Verificar acceso a base de datos"""
    print("\n🧪 TEST 5: Base de Datos SQLite")
    try:
        conn = sqlite3.connect('coordinator.db')
        cursor = conn.cursor()

        # Check work_units table
        cursor.execute("SELECT COUNT(*) FROM work_units")
        work_units_count = cursor.fetchone()[0]
        print(f"   ✅ Work units en DB: {work_units_count}")

        # Check results table
        cursor.execute("SELECT COUNT(*) FROM results")
        results_count = cursor.fetchone()[0]
        print(f"   ✅ Results en DB: {results_count}")

        # Check workers table
        cursor.execute("SELECT COUNT(*) FROM workers")
        workers_count = cursor.fetchone()[0]
        print(f"   ✅ Workers en DB: {workers_count}")

        conn.close()
        return True
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def test_pid_files():
    """Test 6: Verificar PID files"""
    print("\n🧪 TEST 6: Archivos PID")
    pid_files = {
        "coordinator.pid": "Coordinator",
        "worker_pro.pid": "Worker MacBook Pro"
    }

    for pid_file, name in pid_files.items():
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                    # Check if process is running
                    try:
                        os.kill(pid, 0)  # Signal 0 just checks if process exists
                        print(f"   ✅ {name}: PID {pid} (ejecutando)")
                    except OSError:
                        print(f"   ⚠️  {name}: PID {pid} (no ejecutando)")
            except Exception as e:
                print(f"   ❌ {name}: Error - {str(e)}")
        else:
            print(f"   ⚠️  {name}: Archivo no encontrado")

    return True

def test_work_unit_creation():
    """Test 7: Verificar creación de work units"""
    print("\n🧪 TEST 7: Creación de Work Units")
    try:
        conn = sqlite3.connect('coordinator.db')
        cursor = conn.cursor()

        # Count before
        cursor.execute("SELECT COUNT(*) FROM work_units")
        count_before = cursor.fetchone()[0]

        # Create test work unit
        strategy_params = {
            'population_size': 10,
            'generations': 5,
            'risk_level': 'LOW',
            'test': True
        }

        cursor.execute("""
            INSERT INTO work_units (strategy_params, replicas_needed, status)
            VALUES (?, ?, 'pending')
        """, (json.dumps(strategy_params), 1))
        conn.commit()
        work_unit_id = cursor.lastrowid

        # Count after
        cursor.execute("SELECT COUNT(*) FROM work_units")
        count_after = cursor.fetchone()[0]

        # Delete test work unit
        cursor.execute("DELETE FROM work_units WHERE id = ?", (work_unit_id,))
        conn.commit()

        conn.close()

        if count_after == count_before + 1:
            print(f"   ✅ Work unit creado exitosamente (ID: {work_unit_id})")
            print(f"   ✅ Work unit eliminado (test cleanup)")
            return True
        else:
            print(f"   ❌ Error en conteo: antes={count_before}, después={count_after}")
            return False

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def main():
    print("=" * 80)
    print("🧬 TEST DE INTEGRACIÓN - Interface.py + Sistema Distribuido")
    print("=" * 80)

    results = {
        "Coordinator API Status": test_coordinator_api(),
        "Workers API": test_workers_api(),
        "Results API": test_results_api(),
        "Log Files": test_log_files(),
        "Database Access": test_database_access(),
        "PID Files": test_pid_files(),
        "Work Unit Creation": test_work_unit_creation()
    }

    print("\n" + "=" * 80)
    print("📊 RESUMEN DE TESTS")
    print("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("=" * 80)
    print(f"\n{'✅' if passed == total else '⚠️'} Total: {passed}/{total} tests pasados ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 TODOS LOS TESTS PASARON - Interfaz lista para usar")
    else:
        print("\n⚠️  Algunos tests fallaron - Revisar configuración")

    print("=" * 80)

if __name__ == "__main__":
    main()
