#!/usr/bin/env python3
"""
COORDINATOR TEST - Versión de prueba con work units pequeños
Para testing rápido del sistema distribuido
"""

import sys
import os

# Cargar coordinator.py y modificar create_test_work_units
exec(open('coordinator.py').read())

# Sobrescribir función de test work units
def create_test_work_units():
    """Crea work units PEQUEÑOS para testing rápido"""
    test_configs = [
        {
            'population_size': 5,
            'generations': 3,
            'risk_level': 'LOW',
            'test': True,
            'description': 'Test rápido LOW'
        },
        {
            'population_size': 5,
            'generations': 3,
            'risk_level': 'MEDIUM',
            'test': True,
            'description': 'Test rápido MEDIUM'
        }
    ]

    ids = create_work_units(test_configs)
    print(f"✅ {len(ids)} work units de PRUEBA creados: {ids}")
    print(f"⚡ Configuración: 5 población × 3 generaciones (~1-2 min cada uno)")
    return ids

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🧪 COORDINATOR TEST - Work Units Pequeños para Testing")
    print("="*80 + "\n")

    # Inicializar base de datos
    if not os.path.exists(DATABASE):
        print("🔧 Inicializando base de datos...")
        init_db()

        # Crear work units de prueba
        print("\n🧪 Creando work units de PRUEBA (rápidos)...")
        create_test_work_units()
    else:
        print("✅ Base de datos existente encontrada")
        # Verificar si hay work units pendientes
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as pending FROM work_units WHERE status='pending' OR replicas_completed < replicas_needed")
        pending = c.fetchone()['pending']
        conn.close()

        if pending == 0:
            print("\n🧪 No hay work units pendientes - Creando nuevos...")
            create_test_work_units()
        else:
            print(f"\n✅ {pending} work units pendientes en cola")

    print("\n" + "="*80)
    print("🚀 COORDINATOR TEST INICIADO")
    print("="*80)
    print(f"\n📡 Dashboard: http://localhost:5001")
    print(f"📡 API Status: http://localhost:5001/api/status")
    print("\nPresiona Ctrl+C para detener\n")

    # Iniciar servidor Flask en puerto 5001 (5000 ocupado por AirPlay)
    app.run(host='0.0.0.0', port=5001, debug=False)
