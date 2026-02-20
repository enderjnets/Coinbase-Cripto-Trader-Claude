#!/usr/bin/env python3
"""
Fixer para Work Units Atascados del Coordinator
===============================================
Este script identifica y repara work units que estan bloqueados
esperando replicas que nunca llegaran.

Uso:
    python3 fix_stuck_work_units.py [--force-restart] [--mark-complete]
"""

import sqlite3
import sys
import argparse

DATABASE = 'coordinator.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    return conn


def analyze_stuck_work_units():
    """Analiza work units atascados"""
    conn = get_db_connection()
    c = conn.cursor()

    # Buscar work units en progreso con replicas incompletas
    c.execute("""
        SELECT id, replicas_needed, replicas_completed, status, created_at
        FROM work_units 
        WHERE status = 'in_progress'
        AND replicas_completed < replicas_needed
        ORDER BY (replicas_needed - replicas_completed) DESC
    """)

    stuck = []
    for row in c.fetchall():
        pending = row[2] - row[2]  # replicas_needed - replicas_completed
        stuck.append({
            'id': row[0],
            'needed': row[1],
            'completed': row[2],
            'pending': row[1] - row[2],
            'progress_pct': (row[2] / row[1]) * 100 if row[1] > 0 else 0
        })

    conn.close()
    return stuck


def get_workers_status():
    """Verifica estado de workers"""
    conn = get_db_connection()
    c = conn.cursor()

    # Workers activos (ultimos 5 mins)
    c.execute("""
        SELECT id, work_units_completed, status, last_seen
        FROM workers 
        WHERE last_seen > (julianday('now') - 5/1440)
    """)

    active = []
    for row in c.fetchall():
        active.append({
            'id': row[0][:50] + '...' if len(row[0]) > 50 else row[0],
            'completed': row[1],
            'status': row[2]
        })

    conn.close()
    return active


def restart_stuck_work_units(work_unit_ids):
    """
    Reinicia work units atascados poniendolos como pending
    para que puedan ser asignados a workers nuevamente.
    """
    if not work_unit_ids:
        print("No hay work units que reiniciar")
        return True

    conn = get_db_connection()
    c = conn.cursor()

    print(f"\nReiniciando {len(work_unit_ids)} work units...")

    # Resetear work units a pending
    placeholders = ','.join('?' * len(work_unit_ids))
    c.execute(f"""
        UPDATE work_units 
        SET status = 'pending', 
            replicas_completed = 0
        WHERE id IN ({placeholders})
    """, work_unit_ids)

    reset_count = c.rowcount
    conn.commit()
    conn.close()

    print(f" {reset_count} work units reiniciados")
    return True


def mark_near_complete_complete(work_unit_ids, threshold=0.99):
    """
    Marca work units que estan cerca de completar como completados.
    """
    if not work_unit_ids:
        print("No hay work units para marcar")
        return True

    conn = get_db_connection()
    c = conn.cursor()

    # Solo work units con > threshold completado
    c.execute(f"""
        SELECT id, replicas_needed, replicas_completed
        FROM work_units 
        WHERE id IN ({','.join('?' * len(work_unit_ids))})
        AND (CAST(replicas_completed AS FLOAT) / replicas_needed) >= ?
    """, work_unit_ids + [threshold])

    near_complete = [row[0] for row in c.fetchall()]

    if near_complete:
        print(f"\nMarcando {len(near_complete)} work units como completados (>={threshold*100:.0f}%)")
        
        placeholders = ','.join('?' * len(near_complete))
        c.execute(f"""
            UPDATE work_units 
            SET status = 'completed'
            WHERE id IN ({placeholders})
        """, near_complete)

        count = c.rowcount
        conn.commit()
        print(f" {count} work units marcados como completados")
    else:
        print(f"\nNo hay work units con >={threshold*100:.0f}% completado")

    conn.close()
    return True


def cleanup_old_workers():
    """Limpia workers antiguos (no vistos en 24 horas)"""
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""
        DELETE FROM workers 
        WHERE (julianday('now') - last_seen) > 1.0
    """)

    deleted = c.rowcount
    conn.commit()
    conn.close()

    print(f"\n {deleted} workers antiguos eliminados")
    return deleted


def print_report():
    """Imprime reporte del estado actual"""
    print("\n" + "="*70)
    print("REPORTE DEL SISTEMA DE WORK UNITS")
    print("="*70)

    # Work units totales
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT status, COUNT(*) FROM work_units GROUP BY status")
    status_counts = dict(c.fetchall())

    print(f"\nESTADO GENERAL:")
    print(f"   Total Work Units: {sum(status_counts.values())}")
    for status, count in sorted(status_counts.items()):
        print(f"   {status}: {count}")

    # Work units atascados
    stuck = analyze_stuck_work_units()

    print(f"\nWORK UNITS ATASCADOS: {len(stuck)}")
    for wu in stuck:
        print(f"   #{wu['id']}: {wu['completed']}/{wu['needed']} ({wu['progress_pct']:.1f}%)")

    # Workers
    workers = get_workers_status()

    print(f"\nWORKERS ACTIVOS (ultimos 5 min): {len(workers)}")
    for w in workers[:5]:
        print(f"   {w['id']} - {w['completed']} WUs")

    conn.close()

    return len(stuck) > 0


def main():
    parser = argparse.ArgumentParser(
        description='Fixer para Work Units Atascados del Coordinator'
    )
    parser.add_argument(
        '--force-restart', 
        action='store_true',
        help='Reinicia TODOS los work units atascados (los pone como pending)'
    )
    parser.add_argument(
        '--mark-complete', 
        action='store_true',
        help='Marca work units con >99 por ciento completado como completados'
    )
    parser.add_argument(
        '--threshold', 
        type=float, 
        default=0.99,
        help='Umbral para marcar como completado (default: 0.99)'
    )
    parser.add_argument(
        '--cleanup-workers',
        action='store_true',
        help='Limpia workers antiguos (no vistos en 24h)'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Solo muestra el reporte sin hacer cambios'
    )

    args = parser.parse_args()

    # Mostrar reporte
    has_stuck = print_report()

    if args.report_only:
        return 0

    # Opciones de limpieza
    if args.cleanup_workers:
        cleanup_old_workers()

    # Obtener work units atascados
    stuck_ids = [wu['id'] for wu in analyze_stuck_work_units()]

    if not stuck_ids:
        print("\nNo hay work units atascados")
        return 0

    # Marcar como completados (si estan muy cerca)
    if args.mark_complete:
        mark_near_complete_complete(stuck_ids, args.threshold)

    # Reiniciar work units
    if args.force_restart:
        restart_stuck_work_units(stuck_ids)

    return 0


if __name__ == '__main__':
    sys.exit(main())
