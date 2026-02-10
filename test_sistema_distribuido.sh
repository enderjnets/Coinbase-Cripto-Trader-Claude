#!/bin/bash
# Test del Sistema Distribuido
# Verifica que todos los componentes estén listos

echo ""
echo "================================================================================"
echo "🧪 TEST - Sistema Distribuido"
echo "================================================================================"
echo ""

ERRORS=0

# Test 1: Archivos principales
echo "📁 Test 1: Verificando archivos..."
files=("coordinator.py" "crypto_worker.py" "strategy_miner.py" "backtester.py" "dynamic_strategy.py" "data/BTC-USD_FIVE_MINUTE.csv")

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file NO ENCONTRADO"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""

# Test 2: Python version
echo "🐍 Test 2: Verificando Python..."
python3 --version > /dev/null 2>&1
if [ $? -eq 0 ]; then
    PY_VERSION=$(python3 --version)
    echo "   ✅ $PY_VERSION"
else
    echo "   ❌ Python 3 no encontrado"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# Test 3: Dependencias Python
echo "📦 Test 3: Verificando dependencias..."
deps=("flask" "pandas" "numpy" "requests")

for dep in "${deps[@]}"; do
    python3 -c "import $dep" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✅ $dep"
    else
        echo "   ❌ $dep NO INSTALADO"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""

# Test 4: Datos
echo "💾 Test 4: Verificando datos..."
if [ -f "data/BTC-USD_FIVE_MINUTE.csv" ]; then
    lines=$(wc -l < "data/BTC-USD_FIVE_MINUTE.csv")
    size=$(ls -lh "data/BTC-USD_FIVE_MINUTE.csv" | awk '{print $5}')
    echo "   ✅ BTC-USD_FIVE_MINUTE.csv"
    echo "      Líneas: $lines"
    echo "      Tamaño: $size"
else
    echo "   ❌ Datos no encontrados"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# Test 5: Scripts ejecutables
echo "🔧 Test 5: Verificando permisos..."
scripts=("start_coordinator.sh" "start_worker.sh" "coordinator.py" "crypto_worker.py")

for script in "${scripts[@]}"; do
    if [ -x "$script" ]; then
        echo "   ✅ $script (ejecutable)"
    else
        echo "   ⚠️  $script (no ejecutable)"
    fi
done

echo ""

# Test 6: Importación de módulos
echo "🧪 Test 6: Verificando imports..."
python3 -c "from strategy_miner import StrategyMiner; print('   ✅ StrategyMiner')" 2>/dev/null || echo "   ❌ Error importando StrategyMiner"

echo ""

# Test 7: Sintaxis de scripts
echo "🔍 Test 7: Verificando sintaxis Python..."
python3 -m py_compile coordinator.py 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ coordinator.py (sintaxis OK)"
else
    echo "   ❌ coordinator.py (errores de sintaxis)"
    ERRORS=$((ERRORS + 1))
fi

python3 -m py_compile crypto_worker.py 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ crypto_worker.py (sintaxis OK)"
else
    echo "   ❌ crypto_worker.py (errores de sintaxis)"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# Resumen
echo "================================================================================"
if [ $ERRORS -eq 0 ]; then
    echo "✅ TODOS LOS TESTS PASARON"
    echo "================================================================================"
    echo ""
    echo "🚀 Sistema listo para usar!"
    echo ""
    echo "Próximos pasos:"
    echo "  1. Iniciar coordinator: ./start_coordinator.sh"
    echo "  2. Iniciar worker(s): ./start_worker.sh http://COORDINATOR_IP:5000"
    echo "  3. Abrir dashboard: http://localhost:5000"
    echo ""
else
    echo "❌ $ERRORS ERROR(ES) ENCONTRADO(S)"
    echo "================================================================================"
    echo ""
    echo "Revisa los errores arriba y corrige antes de continuar"
    echo ""
fi

exit $ERRORS
