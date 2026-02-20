#!/usr/bin/env python3
"""
🚀 MASTER ORCHESTRATOR v1.0
Orquestador principal de todo el sistema de trading

Este script coordina:
1. Descarga de datos
2. Generación de Work Units
3. Entrenamiento de IA
4. Trading automático
5. Mejora continua

Uso: python3 master_orchestrator.py --mode full
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime

class MasterOrchestrator:
    """
    Orquestador maestro de todo el sistema.
    """
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.state_file = self.base_dir / "orchestrator_state.json"
        self.state = self.cargar_estado()
        
    def cargar_estado(self):
        """Cargar estado del orchestrator."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {
            'fase': 'inicial',
            'progress': 0,
            'ultima_ejecucion': None,
            'errores': [],
            'config': {
                'capital_base': 500,
                'objetivo_diario': 0.05,
                'max_activos': 30,
                'timeframes': ['1m', '5m', '15m', '30m', '1h'],
            }
        }
    
    def guardar_estado(self):
        """Guardar estado del orchestrator."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def log(self, msg):
        """Log con timestamp."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {msg}")
    
    def fase_descargar_datos(self):
        """Fase 1: Descargar datos de mercado."""
        self.log("="*60)
        self.log("FASE 1: DESCARGANDO DATOS DE MERCADO")
        self.log("="*60)
        
        self.state['fase'] = 'descargando_datos'
        self.guardar_estado()
        
        # Ejecutar descarga
        os.chdir(self.base_dir)
        result = os.system("python3 download_multi_data.py")
        
        if result == 0:
            self.log("✅ Datos descargados exitosamente")
            return True
        else:
            self.log(f"❌ Error descargando datos: {result}")
            self.state['errores'].append(f"Datos: {result}")
            return False
    
    def fase_generar_wus(self):
        """Fase 2: Generar Work Units optimizados."""
        self.log("="*60)
        self.log("FASE 2: GENERANDO WORK UNITS OPTIMIZADOS")
        self.log("="*60)
        
        self.state['fase'] = 'generando_wus'
        self.guardar_estado()
        
        # Generar WUs
        result = os.system("python3 generate_optimized_wus.py")
        
        if result == 0:
            self.log("✅ Work Units generados")
            return True
        else:
            self.log(f"❌ Error generando WUs: {result}")
            self.state['errores'].append(f"WUs: {result}")
            return False
    
    def fase_entrenar_ia(self):
        """Fase 3: Entrenar IA."""
        self.log("="*60)
        self.log("FASE 3: ENTRENANDO IA")
        self.log("="*60)
        
        self.state['fase'] = 'entrenando_ia'
        self.guardar_estado()
        
        # Entrenar IA
        result = os.system("python3 ia_trading_agent.py --train")
        
        if result == 0:
            self.log("✅ IA entrenada")
            return True
        else:
            self.log(f"❌ Error entrenando IA: {result}")
            self.state['errores'].append(f"IA: {result}")
            return False
    
    def fase_trading_automatico(self):
        """Fase 4: Trading automático."""
        self.log("="*60)
        self.log("FASE 4: TRADING AUTOMÁTICO")
        self.log("="*60)
        
        self.state['fase'] = 'trading'
        self.guardar_estado()
        
        # Trading loop
        result = os.system("python3 autonomous_trading_loop.py")
        
        if result == 0:
            self.log("✅ Trading completado")
            return True
        else:
            self.log(f"❌ Error en trading: {result}")
            self.state['errores'].append(f"Trading: {result}")
            return False
    
    def ejecutar_modo_autonomo(self):
        """Ejecutar sistema completo en modo autónomo."""
        self.log("="*60)
        self.log("🚀 MODO AUTÓNOMO INICIADO")
        self.log("="*60)
        
        while True:
            fases = [
                ('datos', self.fase_descargar_datos),
                ('wus', self.fase_generar_wus),
                ('ia', self.fase_entrenar_ia),
                ('trading', self.fase_trading_automatico),
            ]
            
            for nombre, funcion in fases:
                self.state['progress'] = 0
                self.guardar_estado()
                
                try:
                    funcion()
                    time.sleep(10)  # Pausa entre fases
                except KeyboardInterrupt:
                    self.log("\n🛑 Detenido por usuario")
                    break
                except Exception as e:
                    self.log(f"❌ Error crítico: {e}")
                    self.state['errores'].append(str(e))
            
            self.log("\n⌛ Esperando 1 hora para siguiente ciclo...")
            time.sleep(3600)  # 1 hora
    
    def ejecutar_modo_unico(self):
        """Ejecutar cada fase una vez."""
        self.log("="*60)
        self.log("🚀 EJECUTANDO SISTEMA COMPLETO")
        self.log("="*60)
        
        fases = [
            ('Datos', self.fase_descargar_datos),
            ('Work Units', self.fase_generar_wus),
            ('IA', self.fase_entrenar_ia),
            ('Trading', self.fase_trading_automatico),
        ]
        
        resultados = []
        for nombre, funcion in fases:
            try:
                success = funcion()
                resultados.append((nombre, success))
            except Exception as e:
                self.log(f"❌ Error en {nombre}: {e}")
                resultados.append((nombre, False))
        
        # Resumen
        self.log("\n" + "="*60)
        self.log("📊 RESUMEN DE EJECUCIÓN")
        self.log("="*60)
        
        for nombre, success in resultados:
            emoji = "✅" if success else "❌"
            self.log(f"{emoji} {nombre}")
        
        exitos = sum(1 for _, s in resultados if s)
        self.log(f"\n{exitos}/{len(resultados)} fases completadas")
        
        self.state['ultima_ejecucion'] = datetime.now().isoformat()
        self.guardar_estado()
    
    def estado_actual(self):
        """Obtener estado actual del sistema."""
        return self.state

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Master Trading Orchestrator')
    parser.add_argument('--mode', choices=['full', 'once', 'status'], default='once',
                        help='Modo de ejecución')
    parser.add_argument('--continuous', action='store_true',
                        help='Ejecutar continuamente')
    
    args = parser.parse_args()
    
    orchestrator = MasterOrchestrator()
    
    if args.mode == 'status':
        state = orchestrator.estado_actual()
        print(json.dumps(state, indent=2))
    elif args.mode == 'full' or args.continuous:
        if args.continuous:
            orchestrator.ejecutar_modo_autonomo()
        else:
            orchestrator.ejecutar_modo_unico()
    else:
        orchestrator.ejecutar_modo_unico()
