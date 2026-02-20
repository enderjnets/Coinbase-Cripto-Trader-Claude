#!/usr/bin/env python3
"""
Monitor continuo para Work Unit #17
Reporta progreso hasta completar
"""

import time
import sqlite3
import json
import os
import requests
from datetime import datetime

BASE_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
COORDINATOR_DB = os.path.join(BASE_DIR, "coordinator.db")
COORDINATOR_URL = "http://localhost:5001"
LOG_FILE = os.path.join(BASE_DIR, "monitor_wu17.log")
REPORT_FILE = os.path.join(BASE_DIR, "REPORTE_WU17.txt")

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + "\n")

def get_work_unit_status(wu_id=17):
    """Get status of work unit from database"""
    try:
        conn = sqlite3.connect(COORDINATOR_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT id, status, strategy_params FROM work_units WHERE id=?', (wu_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            params = json.loads(result[2])
            return {
                'id': result[0],
                'status': result[1],
                'population': params.get('population_size'),
                'generations': params.get('generations'),
                'risk': params.get('risk_level'),
                'data_file': params.get('data_file')
            }
        return None
    except Exception as e:
        log(f"❌ Error getting WU status: {str(e)}")
        return None

def get_current_processing():
    """Get currently processing work unit"""
    try:
        conn = sqlite3.connect(COORDINATOR_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT id, status, strategy_params FROM work_units WHERE status="assigned" LIMIT 1')
        result = cursor.fetchone()
        conn.close()

        if result:
            params = json.loads(result[2])
            return {
                'id': result[0],
                'population': params.get('population_size'),
                'generations': params.get('generations')
            }
        return None
    except:
        return None

def get_queue_position(wu_id=17):
    """Get position in queue"""
    try:
        conn = sqlite3.connect(COORDINATOR_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM work_units WHERE status="pending" ORDER BY id')
        pending = [row[0] for row in cursor.fetchall()]
        conn.close()

        if wu_id in pending:
            return pending.index(wu_id) + 1
        return 0
    except:
        return -1

def get_results(wu_id=17):
    """Get results for work unit"""
    try:
        response = requests.get(f"{COORDINATOR_URL}/api/results/all?limit=100", timeout=2)
        if response.status_code == 200:
            results = response.json()
            wu_results = [r for r in results if r.get('work_unit_id') == wu_id]
            return wu_results
        return []
    except:
        return []

def get_worker_progress():
    """Get current worker progress from log"""
    try:
        log_path = os.path.join(BASE_DIR, "worker_air.log")
        with open(log_path, 'r') as f:
            lines = f.readlines()

        # Find latest generation info
        for line in reversed(lines[-200:]):
            if 'Gen' in line and '/' in line:
                return line.strip()
        return "No progress info"
    except:
        return "Log not accessible"

def create_report(wu_status, current_proc, queue_pos, results, progress):
    """Create status report"""
    report = f"""
════════════════════════════════════════════════════════════════════════════
📊 REPORTE DE MONITOREO - WORK UNIT #17
════════════════════════════════════════════════════════════════════════════

🕐 Actualizado: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

────────────────────────────────────────────────────────────────────────────
📋 TU WORK UNIT #17
────────────────────────────────────────────────────────────────────────────

Status: {wu_status['status'].upper()}
Población: {wu_status['population']}
Generaciones: {wu_status['generations']}
Risk Level: {wu_status['risk']}
Data File: {wu_status['data_file']}

"""

    if wu_status['status'] == 'pending':
        report += f"""
🔄 ESTADO: EN COLA (Esperando procesamiento)
📍 Posición en cola: #{queue_pos}

"""
    elif wu_status['status'] == 'assigned':
        report += f"""
🚀 ESTADO: PROCESANDO AHORA
📈 Progreso: {progress}

"""
    elif wu_status['status'] == 'completed':
        report += f"""
✅ ESTADO: COMPLETADO
🎉 Resultados disponibles: {len(results)}

"""

    if current_proc and current_proc['id'] != 17:
        report += f"""
────────────────────────────────────────────────────────────────────────────
⏳ WORK UNIT ACTUAL EN PROCESAMIENTO
────────────────────────────────────────────────────────────────────────────

Work Unit #{current_proc['id']}
Población: {current_proc['population']}
Generaciones: {current_proc['generations']}
Progreso: {progress}

"""

    if results:
        report += f"""
────────────────────────────────────────────────────────────────────────────
🏆 RESULTADOS
────────────────────────────────────────────────────────────────────────────

Total de resultados: {len(results)}

Mejores 3 estrategias:
"""
        sorted_results = sorted(results, key=lambda x: x.get('pnl', -999999), reverse=True)
        for i, r in enumerate(sorted_results[:3], 1):
            report += f"""
#{i}: PnL=${r.get('pnl', 0):.2f} | Trades:{r.get('trades', 0)} | Win Rate:{r.get('win_rate', 0)*100:.1f}%
    Worker: {r.get('worker_id', 'N/A')[:40]}
"""

    report += f"""
────────────────────────────────────────────────────────────────────────────
📊 ESTADÍSTICAS DEL SISTEMA
────────────────────────────────────────────────────────────────────────────

"""

    try:
        response = requests.get(f"{COORDINATOR_URL}/api/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            report += f"""
Workers activos: {data['workers']['active']}
Work Units total: {data['work_units']['total']}
Work Units pendientes: {data['work_units']['pending']}
Work Units en progreso: {data['work_units']['in_progress']}
Work Units completados: {data['work_units']['completed']}
"""
    except:
        report += "❌ No se pudo obtener estadísticas del coordinator\n"

    report += f"""
════════════════════════════════════════════════════════════════════════════
Monitor activo - Próxima actualización en 2 minutos
════════════════════════════════════════════════════════════════════════════
"""

    return report

def main():
    log("="*70)
    log("🤖 MONITOR DE WORK UNIT #17 INICIADO")
    log("="*70)
    log("")

    last_status = None
    last_queue_pos = None
    iteration = 0

    while True:
        iteration += 1
        log(f"📊 Iteración #{iteration}")

        # Get current status
        wu_status = get_work_unit_status(17)

        if not wu_status:
            log("❌ No se pudo obtener estado del Work Unit #17")
            time.sleep(120)
            continue

        current_status = wu_status['status']
        current_proc = get_current_processing()
        queue_pos = get_queue_position(17)
        results = get_results(17)
        progress = get_worker_progress()

        # Check for status changes
        if current_status != last_status:
            log(f"🔔 CAMBIO DE STATUS: {last_status or 'N/A'} → {current_status}")

            if current_status == 'assigned':
                log("🚀 ¡TU WORK UNIT #17 ESTÁ SIENDO PROCESADO AHORA!")
            elif current_status == 'completed':
                log("✅ ¡TU WORK UNIT #17 HA COMPLETADO!")
                log(f"🏆 Resultados disponibles: {len(results)}")

                # Create final report
                final_report = create_report(wu_status, current_proc, queue_pos, results, progress)
                with open(REPORT_FILE, 'w') as f:
                    f.write(final_report)

                log("="*70)
                log("🎉 MONITOREO COMPLETADO - Work Unit #17 finalizado")
                log(f"📄 Reporte final guardado en: {REPORT_FILE}")
                log("="*70)

                # Print final results
                if results:
                    log("")
                    log("🏆 MEJORES RESULTADOS:")
                    sorted_results = sorted(results, key=lambda x: x.get('pnl', -999999), reverse=True)
                    for i, r in enumerate(sorted_results[:5], 1):
                        log(f"   #{i}: PnL=${r.get('pnl', 0):.2f} | Trades:{r.get('trades', 0)} | Win Rate:{r.get('win_rate', 0)*100:.1f}%")

                break

        # Check for queue position changes
        if queue_pos != last_queue_pos and current_status == 'pending':
            log(f"📍 Posición en cola: #{queue_pos}")

        last_status = current_status
        last_queue_pos = queue_pos

        # Create and save report
        report = create_report(wu_status, current_proc, queue_pos, results, progress)
        with open(REPORT_FILE, 'w') as f:
            f.write(report)

        # Log summary
        log(f"   Status: {current_status.upper()}")
        if current_status == 'pending':
            log(f"   Cola: Posición #{queue_pos}")
        elif current_status == 'assigned':
            log(f"   Procesando: {progress}")
        elif current_status == 'completed':
            log(f"   Completado: {len(results)} resultados")

        # Wait 2 minutes before next check
        log("⏳ Esperando 2 minutos para próxima verificación...")
        log("")
        time.sleep(120)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("")
        log("🛑 Monitor detenido por usuario")
    except Exception as e:
        log(f"❌ Error fatal: {str(e)}")
        import traceback
        log(traceback.format_exc())
