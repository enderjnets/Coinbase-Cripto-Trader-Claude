#!/bin/bash
# Script para ejecutar coordinator en puerto 5001 (evitando conflicto con AirPlay)

cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

# Crear versión modificada del coordinator con puerto 5001
cat coordinator.py | sed 's/port=5000/port=5001/g' | sed 's/localhost:5000/localhost:5001/g' > coordinator_port5001.py

# Modificar create_test_work_units para crear work units pequeños
cat >> coordinator_port5001.py << 'EOF'

# Sobrescribir función para testing
def create_test_work_units_small():
    test_configs = [
        {'population_size': 5, 'generations': 3, 'risk_level': 'LOW', 'test': True},
        {'population_size': 5, 'generations': 3, 'risk_level': 'MEDIUM', 'test': True}
    ]
    ids = create_work_units(test_configs)
    print(f"✅ {len(ids)} work units de PRUEBA creados (5 pop × 3 gen)")
    return ids

# Reemplazar en __main__
import sys
if '--test' in sys.argv:
    create_test_work_units = create_test_work_units_small
EOF

echo "✅ Coordinator modificado para puerto 5001"
echo "🚀 Iniciando coordinator..."

python3 coordinator_port5001.py --test
