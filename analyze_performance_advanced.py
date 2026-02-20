#!/usr/bin/env python3
"""
📊 ADVANCED PERFORMANCE ANALYZER v2.0
Analiza resultados de Work Units para identificar patrones ganadores
y detectar oportunidades de mejora.

Uso: python3 analyze_performance_advanced.py
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter

class PerformanceAnalyzer:
    """Analizador avanzado de rendimiento del sistema de trading"""
    
    def __init__(self):
        self.db_path = "coordinator.db"
        self.output_dir = "optimization_history"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_db_connection(self):
        """Crea conexión a la base de datos"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def analyze_overall_stats(self):
        """Estadísticas generales del sistema"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        stats = {}
        
        # Work Units
        c.execute("SELECT COUNT(*) FROM work_units")
        stats['total_wu'] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM work_units WHERE status='completed'")
        stats['completed_wu'] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
        stats['pending_wu'] = c.fetchone()[0]
        
        # Workers
        c.execute("SELECT COUNT(*) FROM workers")
        stats['total_workers'] = c.fetchone()[0]
        
        # Results
        c.execute("SELECT COUNT(*) FROM results")
        stats['total_results'] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM results WHERE pnl > 0")
        stats['positive_results'] = c.fetchone()[0]
        
        c.execute("SELECT MIN(pnl), MAX(pnl), AVG(pnl), SUM(pnl) FROM results WHERE pnl IS NOT NULL")
        pnl_stats = c.fetchone()
        stats['min_pnl'] = pnl_stats[0]
        stats['max_pnl'] = pnl_stats[1]
        stats['avg_pnl'] = pnl_stats[2]
        stats['total_pnl'] = pnl_stats[3]
        
        conn.close()
        
        return stats
    
    def analyze_top_strategies(self, min_pnl=0, limit=20):
        """Analiza las estrategias con mejor rendimiento"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT r.pnl, r.trades, r.win_rate, r.sharpe_ratio, r.max_drawdown,
                   r.execution_time, w.strategy_params, r.worker_id
            FROM results r
            JOIN work_units w ON r.work_unit_id = w.id
            WHERE r.pnl >= ?
            ORDER BY r.pnl DESC
            LIMIT ?
        ''', (min_pnl, limit))
        
        strategies = []
        for row in c.fetchall():
            params = json.loads(row[6])
            strategies.append({
                'pnl': row[0],
                'trades': row[1],
                'win_rate': row[2],
                'sharpe': row[3],
                'max_dd': row[4],
                'exec_time': row[5],
                'name': params.get('name', 'Unknown'),
                'category': params.get('category', 'Unknown'),
                'pop_size': params.get('population_size'),
                'generations': params.get('generations'),
                'risk_level': params.get('risk_level'),
                'stop_loss': params.get('stop_loss'),
                'take_profit': params.get('take_profit'),
                'worker': row[7]
            })
        
        conn.close()
        return strategies
    
    def analyze_parameter_patterns(self, min_pnl=300):
        """Identifica patrones en los parámetros de estrategias exitosas"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT w.strategy_params
            FROM results r
            JOIN work_units w ON r.work_unit_id = w.id
            WHERE r.pnl >= ?
        ''', (min_pnl,))
        
        params_list = []
        for (row,) in c.fetchall():
            params_list.append(json.loads(row))
        
        conn.close()
        
        if not params_list:
            return {}
        
        # Analizar patrones
        patterns = {
            'population_sizes': Counter(),
            'generations': Counter(),
            'risk_levels': Counter(),
            'stop_losses': Counter(),
            'take_profits': Counter(),
            'categories': Counter(),
            'mutation_rates': [],
            'crossover_rates': [],
        }
        
        for p in params_list:
            patterns['population_sizes'][p.get('population_size', 'N/A')] += 1
            patterns['generations'][p.get('generations', 'N/A')] += 1
            patterns['risk_levels'][p.get('risk_level', 'N/A')] += 1
            patterns['stop_losses'][f"{p.get('stop_loss', 0)}%"] += 1
            patterns['take_profits'][f"{p.get('take_profit', 0)}%"] += 1
            patterns['categories'][p.get('category', 'Unknown')] += 1
            
            if p.get('mutation_rate'):
                patterns['mutation_rates'].append(p['mutation_rate'])
            if p.get('crossover_rate'):
                patterns['crossover_rates'].append(p['crossover_rate'])
        
        # Calcular promedios
        patterns['avg_mutation_rate'] = sum(patterns['mutation_rates']) / len(patterns['mutation_rates']) if patterns['mutation_rates'] else 0
        patterns['avg_crossover_rate'] = sum(patterns['crossover_rates']) / len(patterns['crossover_rates']) if patterns['crossover_rates'] else 0
        
        return patterns
    
    def analyze_worker_performance(self):
        """Analiza el rendimiento por worker"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT worker_id, COUNT(*) as count, AVG(pnl) as avg_pnl, MAX(pnl) as max_pnl
            FROM results
            WHERE pnl IS NOT NULL
            GROUP BY worker_id
            ORDER BY avg_pnl DESC
        ''')
        
        workers = []
        for row in c.fetchall():
            workers.append({
                'id': row[0],
                'wu_count': row[1],
                'avg_pnl': row[2],
                'max_pnl': row[3]
            })
        
        conn.close()
        return workers
    
    def generate_report(self):
        """Genera un reporte completo del sistema"""
        stats = self.analyze_overall_stats()
        top_strategies = self.analyze_top_strategies(min_pnl=400)
        patterns = self.analyze_parameter_patterns(min_pnl=350)
        workers = self.analyze_worker_performance()
        
        report = []
        report.append("=" * 80)
        report.append("📊 REPORTE DE RENDIMIENTO AVANZADO")
        report.append(f"   Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        
        # Estadísticas Generales
        report.append("\n📈 ESTADÍSTICAS GENERALES")
        report.append("-" * 40)
        report.append(f"Work Units Totales:    {stats['total_wu']}")
        report.append(f"Work Units Completados: {stats['completed_wu']}")
        report.append(f"Workers Registrados:   {stats['total_workers']}")
        report.append(f"Resultados Totales:    {stats['total_results']}")
        report.append(f"Resultados Positivos:   {stats['positive_results']} ({stats['positive_results']/max(1,stats['total_results'])*100:.1f}%)")
        report.append(f"\n💰 PnL:")
        report.append(f"   Mínimo: ${stats['min_pnl']:,.2f}")
        report.append(f"   Máximo: ${stats['max_pnl']:,.2f}")
        report.append(f"   Promedio: ${stats['avg_pnl']:,.2f}")
        report.append(f"   Total: ${stats['total_pnl']:,.2f}")
        
        # Récord actual
        report.append(f"\n🏆 RÉCORD ACTUAL: ${stats['max_pnl']:,.2f}")
        if stats['max_pnl'] >= 443.99:
            report.append("   ✅ ¡RÉCORD SUPERADO!")
        else:
            report.append(f"   📍 Faltan: ${443.99 - stats['max_pnl']:,.2f}")
        
        # Top Estrategias
        report.append("\n🏆 TOP 10 ESTRATEGIAS GANADORAS")
        report.append("-" * 80)
        for i, s in enumerate(top_strategies[:10], 1):
            report.append(f"\n{i}. {s['name']}")
            report.append(f"   💰 PnL: ${s['pnl']:,.2f} | Trades: {s['trades']} | Win: {s['win_rate']:.1%}")
            report.append(f"   📊 Sharpe: {s['sharpe']:.2f} | Max DD: {s['max_dd']:.2%}")
            report.append(f"   ⚙️  Pop: {s['pop_size']} | Gen: {s['generations']} | Risk: {s['risk_level']}")
            report.append(f"   🛡️  SL: {s['stop_loss']}% | TP: {s['take_profit']}% | {s['category']}")
        
        # Patrones Exitosos
        if patterns:
            report.append("\n\n📊 PATRONES EN ESTRATEGIAS EXITOSAS (PnL > $350)")
            report.append("-" * 40)
            
            report.append("\nPopulation Sizes más frecuentes:")
            for size, count in patterns['population_sizes'].most_common(10):
                report.append(f"   {size}: {count} estrategias")
            
            report.append("\nGenerations más frecuentes:")
            for gen, count in patterns['generations'].most_common(10):
                report.append(f"   {gen}: {count} estrategias")
            
            report.append("\nRisk Levels:")
            for risk, count in patterns['risk_levels'].most_common():
                report.append(f"   {risk}: {count} estrategias")
            
            report.append("\nCategorías:")
            for cat, count in patterns['categories'].most_common():
                report.append(f"   {cat}: {count} estrategias")
            
            report.append(f"\nPromedio Mutation Rate: {patterns['avg_mutation_rate']:.3f}")
            report.append(f"Promedio Crossover Rate: {patterns['avg_crossover_rate']:.3f}")
        
        # Worker Performance
        report.append("\n\n👥 TOP 10 WORKERS POR RENDIMIENTO")
        report.append("-" * 40)
        for i, w in enumerate(workers[:10], 1):
            report.append(f"{i}. {w['id'][:40]}...")
            report.append(f"   WUs completados: {w['wu_count']} | Avg PnL: ${w['avg_pnl']:,.2f} | Max PnL: ${w['max_pnl']:,.2f}")
        
        report.append("\n" + "=" * 80)
        report.append("FIN DEL REPORTE")
        report.append("=" * 80)
        
        report_text = "\n".join(report)
        
        # Guardar reporte
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.output_dir, f"performance_report_{timestamp}.txt")
        with open(report_file, 'w') as f:
            f.write(report_text)
        
        return report_text, report_file
    
    def predict_next_breakthrough(self):
        """Predice qué parámetros podrían dar el próximo breakthrough"""
        patterns = self.analyze_parameter_patterns(min_pnl=400)
        
        predictions = []
        
        if patterns:
            # Encontrar los parámetros más exitosos
            top_pop = patterns['population_sizes'].most_common(3)
            top_gen = patterns['generations'].most_common(3)
            top_cat = patterns['categories'].most_common(5)
            
            predictions.append("🔮 PREDICCIÓN PARA PRÓXIMO BREAKTHROUGH:")
            predictions.append("-" * 50)
            predictions.append(f"\n📊 Parámetros sugeridos:")
            
            # Sugerencias basadas en análisis
            best_pop = max(top_pop, key=lambda x: x[1])[0]
            best_gen = max(top_gen, key=lambda x: x[1])[0]
            
            predictions.append(f"   Population Size: {best_pop}")
            predictions.append(f"   Generations: {best_gen}")
            predictions.append(f"   Risk Level: HIGH")
            predictions.append(f"   Mutation Rate: {patterns['avg_mutation_rate']:.2f}")
            predictions.append(f"   Crossover Rate: {patterns['avg_crossover_rate']:.2f}")
            
            predictions.append(f"\n🏷️  Categorías con mayor potencial:")
            for cat, count in top_cat[:3]:
                predictions.append(f"   - {cat} ({count} estrategias exitosas)")
        
        return "\n".join(predictions)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("📊 ADVANCED PERFORMANCE ANALYZER v2.0")
    print("="*80 + "\n")
    
    analyzer = PerformanceAnalyzer()
    
    # Generar reporte completo
    report, report_file = analyzer.generate_report()
    print(report)
    
    print(f"\n📁 Reporte guardado en: {report_file}")
    
    # Predicciones
    print("\n")
    predictions = analyzer.predict_next_breakthrough()
    print(predictions)
    
    print("\n💡 Para generar nuevos WUs avanzados:")
    print("   python3 generate_advanced_wus.py")
