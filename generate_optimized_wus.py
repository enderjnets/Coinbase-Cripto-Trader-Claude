#!/usr/bin/env python3
"""
🧬 WORK UNIT GENERATOR v1.0
Genera Work Units optimizados para el sistema de trading

Usa:
- Capital: $500
- Risk: 2% por trade
- Stop Loss: 5%
- Take Profit: 10%
- Timeframes: 1m, 5m, 15m, 30m, 1h
- Activos: Top 30
- 24 meses de datos mínimo

Uso: python3 generate_optimized_wus.py
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

class OptimizedWUGenerator:
    """
    Genera Work Units optimizados para trading.
    """
    
    def __init__(self):
        self.db_path = Path("data_multi/download_tracker.db")
        self.coordinator_db = Path("coordinator.db")
        self.config = {
            # 💰 CAPITAL Y RENDIMIENTO
            'capital_base': 500.0,           # $500
            'objetivo_diario': 0.05,          # 5% diario
            'risk_per_trade': 0.02,         # 2% por trade
            'stop_loss': 0.05,              # 5%
            'take_profit': 0.10,             # 10%
            
            # 🧬 ALGORITMO GENÉTICO
            'population_size': 100,
            'generations': 100,
            'mutation_rate': 0.15,
            'crossover_rate': 0.8,
            'elite_rate': 0.1,              # Top 10%
            
            # 📊 PARAMETROS ADICIONALES
            'max_positions': 5,              # Máx. 5 posiciones
            'trailing_stop': True,           # Trailing stop
            'trailing_stop_pct': 0.03,      # 3%
            'breakeven_after': 0.02,         # Move to breakeven después de 2%
        }
        
    def obtener_activos_descargados(self):
        """Obtener lista de activos con datos descargados."""
        if not self.db_path.exists():
            return []
        
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        
        c.execute('SELECT DISTINCT symbol FROM descargas ORDER BY symbol')
        activos = [row[0] for row in c.fetchall()]
        
        conn.close()
        
        return activos
    
    def obtener_timeframes_disponibles(self, symbol):
        """Obtener timeframes disponibles para un símbolo."""
        if not self.db_path.exists():
            return []
        
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        
        c.execute(
            'SELECT timeframe FROM descargas WHERE symbol = ? AND estado = "completado"',
            (symbol,)
        )
        tfs = [row[0] for row in c.fetchall()]
        
        conn.close()
        
        return tfs
    
    def crear_wu_params(self, symbol, timeframe):
        """Crear parámetros optimizados para un WU."""
        return {
            # Parámetros básicos
            'symbol': symbol,
            'timeframe': timeframe,
            'population_size': self.config['population_size'],
            'generations': self.config['generations'],
            'mutation_rate': self.config['mutation_rate'],
            'crossover_rate': self.config['crossover_rate'],
            'elite_rate': self.config['elite_rate'],
            
            # Capital y gestión de riesgo
            'capital_base': self.config['capital_base'],
            'risk_per_trade': self.config['risk_per_trade'],
            'stop_loss': self.config['stop_loss'],
            'take_profit': self.config['take_profit'],
            'max_positions': self.config['max_positions'],
            
            # Configuración avanzada
            'trailing_stop': self.config['trailing_stop'],
            'trailing_stop_pct': self.config['trailing_stop_pct'],
            'breakeven_after': self.config['breakeven_after'],
            
            # Archivo de datos
            'data_file': f'{symbol}_{timeframe}.csv',
        }
    
    def generar_work_units(self):
        """
        Generar WUs para todos los activos/timeframes descargados.
        """
        activos = self.obtener_activos_descargados()
        
        if not activos:
            print("❌ No hay datos descargados. Ejecuta download_multi_data.py primero.")
            return []
        
        print("\n" + "="*60)
        print("🧬 GENERANDO WORK UNITS OPTIMIZADOS")
        print("="*60)
        print(f"\n💰 Capital base: ${self.config['capital_base']}")
        print(f"🎯 Risk por trade: {self.config['risk_per_trade']*100}%")
        print(f"🛑 Stop Loss: {self.config['stop_loss']*100}%")
        print(f"🎯 Take Profit: {self.config['take_profit']*100}%")
        print(f"\n📊 Activos con datos: {len(activos)}")
        
        # Conectar a coordinator
        conn = sqlite3.connect(str(self.coordinator_db))
        c = conn.cursor()
        
        wus_creados = []
        
        for symbol in activos:
            timeframes = self.obtener_timeframes_disponibles(symbol)
            
            for tf in timeframes:
                params = self.crear_wu_params(symbol, tf)
                
                # Verificar si ya existe WU similar
                c.execute(
                    'SELECT id FROM work_units WHERE strategy_params LIKE ?',
                    (f'%{symbol}_{tf}%',)
                )
                existe = c.fetchone()
                
                if existe:
                    print(f"   ⏭️ {symbol}/{tf}: Ya existe")
                    continue
                
                # Crear WU
                c.execute('''
                    INSERT INTO work_units 
                    (strategy_params, replicas_needed, status)
                    VALUES (?, 2, 'pending')
                ''', (json.dumps(params),))
                
                wu_id = c.lastrowid
                wus_creados.append((wu_id, symbol, tf))
                
                print(f"   ✅ {symbol}/{tf}: WU #{wu_id}")
        
        conn.commit()
        conn.close()
        
        # Resumen
        print("\n" + "="*60)
        print(f"✅ {len(wus_creados)} Work Units creados")
        print("="*60)
        
        return wus_creados

# ============================================================================
# IA TRAINING DATA GENERATOR
# ============================================================================

class TrainingDataGenerator:
    """
    Genera datos de entrenamiento para la IA.
    """
    
    def __init__(self):
        self.data_dir = Path("data_multi")
        self.training_data_dir = Path("ia_training_data")
        self.training_data_dir.mkdir(exist_ok=True)
    
    def generar_dataset_para_ia(self, symbol, timeframe):
        """
        Generar dataset de entrenamiento para la IA.
        
        Features:
        - Indicadores técnicos (RSI, MACD, BB, etc.)
        - Patrones de precio
        - Labels: buy/sell/hold
        """
        data_file = self.data_dir / f"{symbol}_{timeframe}.csv"
        
        if not data_file.exists():
            return None
        
        try:
            df = pd.read_csv(data_file)
            
            # Calcular indicadores
            df = self.agregar_indicadores(df)
            
            # Generar labels
            df = self.generar_labels(df)
            
            # Guardar
            output_file = self.training_data_dir / f"{symbol}_{timeframe}_training.csv"
            df.to_csv(output_file, index=False)
            
            return output_file
            
        except Exception as e:
            print(f"   ❌ Error generando training data: {e}")
            return None
    
    def agregar_indicadores(self, df):
        """Agregar indicadores técnicos."""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        
        # SMA 50/200
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # Volatilidad
        df['volatility'] = df['close'].pct_change().rolling(window=20).std()
        
        # Volumen relativo
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        return df
    
    def generar_labels(self, df):
        """
        Generar labels para entrenamiento.
        
        Futuro: 5% en 24 horas = BUY
        Futuro: -5% en 24 horas = SELL
        = HOLD
        """
        df['future_return'] = df['close'].shift(-24) / df['close'] - 1
        
        def labelizar(ret):
            if pd.isna(ret):
                return 'hold'
            elif ret > 0.05:
                return 'buy'
            elif ret < -0.05:
                return 'sell'
            else:
                return 'hold'
        
        df['label'] = df['future_return'].apply(labelizar)
        
        return df

# ============================================================================
# DASHBOARD API
# ============================================================================

def obtener_estado_sistema():
    """Obtener estado completo del sistema."""
    data_dir = Path("data_multi")
    training_dir = Path("ia_training_data")
    coordinator_db = Path("coordinator.db")
    
    # Contar archivos
    data_files = list(data_dir.glob("*.csv")) if data_dir.exists() else []
    training_files = list(training_dir.glob("*.csv")) if training_dir.exists() else []
    
    # Workers
    workers_activos = 0
    if coordinator_db.exists():
        conn = sqlite3.connect(str(coordinator_db))
        c = conn.cursor()
        c.execute(
            "SELECT COUNT(*) FROM workers WHERE (julianday('now') - last_seen) < (10.0/1440.0)"
        )
        workers_activos = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM work_units")
        wus_totales = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM work_units WHERE status = 'completed'")
        wus_completados = c.fetchone()[0]
        conn.close()
    else:
        wus_totales = 0
        wus_completados = 0
    
    return {
        'data_files': len(data_files),
        'training_files': len(training_files),
        'workers_activos': workers_activos,
        'work_units_totales': wus_totales,
        'work_units_completados': wus_completados,
        'capital_base': 500,
        'objetivo_diario': '5%',
    }

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    import pandas as pd
    from pathlib import Path
    
    print("\n" + "="*60)
    print("🧬 OPTIMIZED WORK UNIT GENERATOR v1.0")
    print("="*60)
    
    # Generar WUs
    generator = OptimizedWUGenerator()
    wus = generator.generar_work_units()
    
    print(f"\n📊 Resumen:")
    print(f"   WUs creados: {len(wus)}")
    print(f"   Activos procesados: {len(set([w[1] for w in wus]))}")
