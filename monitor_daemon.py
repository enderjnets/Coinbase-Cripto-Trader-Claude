#!/usr/bin/env python3
"""
monitor_daemon.py - Sistema de Monitoreo y Auto-Restart
=======================================================

Monitorea el sistema de trading y reinicia servicios automáticamente:
- Coordinator (puerto 5001)
- Workers (MacBook Pro y Linux ROG)
- Telegram Bot
- Streamlit Dashboard

Uso:
    python monitor_daemon.py [--interval 60]

    # O como daemon en background:
    nohup python monitor_daemon.py > /tmp/monitor.log 2>&1 &
"""

import time
import subprocess
import requests
import sqlite3
import os
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configuración
MONITOR_INTERVAL = 60  # Segundos entre checks
COORDINATOR_URL = "http://localhost:5001"
DB_PATH = "coordinator.db"
LOG_FILE = "/tmp/monitor.log"

# Workers por máquina
MACBOOK_PRO_WORKERS = 3
MACBOOK_AIR_IP = "10.0.0.97"
MACBOOK_AIR_WORKERS = 4
LINUX_ROG_IP = "10.0.0.240"
LINUX_ROG_WORKERS = 5
ASUS_DORADA_IP = "10.0.0.56"
ASUS_DORADA_WORKERS = 0  # Deshabilitado por ahora

# Timeouts
WORKER_TIMEOUT_MINUTES = 5  # Workers sin reportar por 5 min = problema
COORDINATOR_TIMEOUT_SECONDS = 10


class SystemMonitor:
    """Monitor del sistema de trading distribuido."""

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.alerts_sent = set()  # Para evitar spam de alertas
        self.restart_count = {}  # Contador de reinicios por servicio

    def log(self, message: str, level: str = "INFO"):
        """Log con timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line)

        try:
            with open(LOG_FILE, "a") as f:
                f.write(log_line + "\n")
        except:
            pass

    def check_coordinator(self) -> Tuple[bool, Dict]:
        """
        Verifica que el coordinator esté funcionando.

        Returns:
            (is_healthy, details)
        """
        try:
            response = requests.get(
                f"{COORDINATOR_URL}/api/status",
                timeout=COORDINATOR_TIMEOUT_SECONDS
            )
            if response.status_code == 200:
                data = response.json()
                return True, {
                    'status': 'running',
                    'workers': data.get('workers', {}).get('active', 0),
                    'work_units': data.get('work_units', {}).get('total', 0)
                }
            else:
                return False, {'status': f'http_{response.status_code}'}
        except requests.exceptions.ConnectionError:
            return False, {'status': 'not_running'}
        except requests.exceptions.Timeout:
            return False, {'status': 'timeout'}
        except Exception as e:
            return False, {'status': 'error', 'error': str(e)}

    def check_database(self) -> Tuple[bool, Dict]:
        """Verifica que la base de datos esté accesible."""
        db_path = os.path.join(self.base_dir, DB_PATH)

        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()

            # Verificar tablas
            c.execute("SELECT COUNT(*) FROM work_units")
            work_units = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM results")
            results = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM workers")
            workers = c.fetchone()[0]

            conn.close()

            return True, {
                'work_units': work_units,
                'results': results,
                'workers': workers
            }
        except Exception as e:
            return False, {'error': str(e)}

    def check_workers_alive(self) -> Dict[str, List[str]]:
        """
        Verifica qué workers están vivos basándose en última vez vistos.

        Returns:
            {'alive': [...], 'dead': [...]}
        """
        db_path = os.path.join(self.base_dir, DB_PATH)

        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()

            # Workers activos en últimos 5 minutos
            c.execute("""
                SELECT worker_id, hostname, platform
                FROM workers
                WHERE status = 'active'
                AND (julianday('now') - last_seen) < (5.0 / 1440.0)
            """)
            alive = c.fetchall()

            # Workers no vistos en >5 minutos
            c.execute("""
                SELECT worker_id, hostname, platform
                FROM workers
                WHERE status = 'active'
                AND (julianday('now') - last_seen) >= (5.0 / 1440.0)
            """)
            dead = c.fetchall()

            conn.close()

            return {
                'alive': [w[0] for w in alive],
                'dead': [w[0] for w in dead],
                'alive_details': alive,
                'dead_details': dead
            }
        except Exception as e:
            return {'alive': [], 'dead': [], 'error': str(e)}

    def restart_coordinator(self) -> bool:
        """Reinicia el coordinator."""
        self.log("Reiniciando coordinator...")

        try:
            # Matar proceso existente
            subprocess.run(
                ["pkill", "-f", "coordinator_port5001"],
                capture_output=True
            )
            time.sleep(2)

            # Iniciar nuevo
            venv_python = os.path.expanduser("~/coinbase_trader_venv/bin/python")
            cmd = f"cd '{self.base_dir}' && {venv_python} -u coordinator_port5001.py > /tmp/coordinator.log 2>&1 &"

            subprocess.run(cmd, shell=True, executable="/bin/bash")
            time.sleep(3)

            # Verificar que inició
            is_healthy, _ = self.check_coordinator()
            if is_healthy:
                self.log("Coordinator reiniciado exitosamente", "SUCCESS")
                return True
            else:
                self.log("Fallo al reiniciar coordinator", "ERROR")
                return False

        except Exception as e:
            self.log(f"Error reiniciando coordinator: {e}", "ERROR")
            return False

    def restart_macbook_workers(self) -> bool:
        """Reinicia workers del MacBook Pro."""
        self.log("Reiniciando workers MacBook Pro...")

        try:
            # Matar existentes
            subprocess.run(["pkill", "-f", "crypto_worker"], capture_output=True)
            time.sleep(2)

            # Iniciar nuevos
            venv_python = os.path.expanduser("~/coinbase_trader_venv/bin/python")
            for i in range(1, MACBOOK_PRO_WORKERS + 1):
                cmd = f"""cd '{self.base_dir}' && \\
                    COORDINATOR_URL="http://localhost:5001" \\
                    NUM_WORKERS="{MACBOOK_PRO_WORKERS}" \\
                    WORKER_INSTANCE="{i}" \\
                    USE_RAY="false" \\
                    PYTHONUNBUFFERED=1 \\
                    {venv_python} -u crypto_worker.py > /tmp/worker_{i}.log 2>&1 &
                """
                subprocess.run(cmd, shell=True, executable="/bin/bash")
                time.sleep(2)

            self.log(f"{MACBOOK_PRO_WORKERS} workers MacBook Pro reiniciados", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"Error reiniciando workers MacBook: {e}", "ERROR")
            return False

    def restart_linux_workers(self) -> bool:
        """Reinicia workers de Linux ROG vía SSH."""
        self.log("Reiniciando workers Linux ROG vía SSH...")

        try:
            # Comando SSH para reiniciar workers
            ssh_cmd = f"""ssh enderj@{LINUX_ROG_IP} '
                killall python3 2>/dev/null
                sleep 2
                cd ~/crypto_worker
                for i in 1 2 3 4 5; do
                    COORDINATOR_URL="http://10.0.0.232:5001" \\
                    NUM_WORKERS="5" \\
                    WORKER_INSTANCE="$i" \\
                    USE_RAY="false" \\
                    PYTHONUNBUFFERED=1 \\
                    nohup python3 -u crypto_worker.py > /tmp/worker_$i.log 2>&1 &
                    sleep 2
                done
                echo "Workers started"
            '"""

            result = subprocess.run(
                ssh_cmd,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                timeout=60
            )

            if "Workers started" in result.stdout:
                self.log(f"{LINUX_ROG_WORKERS} workers Linux ROG reiniciados", "SUCCESS")
                return True
            else:
                self.log(f"Error en SSH: {result.stderr}", "ERROR")
                return False

        except subprocess.TimeoutExpired:
            self.log("Timeout conectando a Linux ROG", "ERROR")
            return False
        except Exception as e:
            self.log(f"Error reiniciando workers Linux: {e}", "ERROR")
            return False

    def restart_macbook_air_workers(self) -> bool:
        """Reinicia workers de MacBook Air vía SSH."""
        self.log("Reiniciando workers MacBook Air vía SSH...")

        try:
            # Comando SSH para reiniciar workers
            ssh_cmd = f"""ssh enderj@{MACBOOK_AIR_IP} '
                pkill -f crypto_worker 2>/dev/null
                sleep 2
                cd ~/crypto_worker
                source venv/bin/activate
                for i in 1 2 3 4; do
                    COORDINATOR_URL="http://10.0.0.232:5001" \\
                    NUM_WORKERS="4" \\
                    WORKER_INSTANCE="$i" \\
                    USE_RAY="false" \\
                    PYTHONUNBUFFERED=1 \\
                    nohup python -u crypto_worker.py > /tmp/worker_$i.log 2>&1 &
                    sleep 2
                done
                echo "Workers started"
            '"""

            result = subprocess.run(
                ssh_cmd,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                timeout=90
            )

            if "Workers started" in result.stdout:
                self.log(f"{MACBOOK_AIR_WORKERS} workers MacBook Air reiniciados", "SUCCESS")
                return True
            else:
                self.log(f"Error en SSH: {result.stderr}", "ERROR")
                return False

        except subprocess.TimeoutExpired:
            self.log("Timeout conectando a MacBook Air", "ERROR")
            return False
        except Exception as e:
            self.log(f"Error reiniciando workers MacBook Air: {e}", "ERROR")
            return False

    def restart_telegram_bot(self) -> bool:
        """Reinicia el Telegram bot."""
        self.log("Reiniciando Telegram bot...")

        try:
            # Matar existente
            subprocess.run(["pkill", "-f", "telegram_bot"], capture_output=True)
            time.sleep(2)

            # Iniciar nuevo
            venv_python = os.path.expanduser("~/coinbase_trader_venv/bin/python")
            cmd = f"cd '{self.base_dir}' && {venv_python} -u telegram_bot.py > /tmp/telegram_bot.log 2>&1 &"

            subprocess.run(cmd, shell=True, executable="/bin/bash")
            time.sleep(2)

            self.log("Telegram bot reiniciado", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"Error reiniciando Telegram bot: {e}", "ERROR")
            return False

    def check_all(self) -> Dict:
        """
        Ejecuta todas las verificaciones y retorna estado completo.

        Returns:
            Dict con estado de todos los componentes
        """
        status = {
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }

        # Coordinator
        is_healthy, details = self.check_coordinator()
        status['components']['coordinator'] = {
            'healthy': is_healthy,
            **details
        }

        # Database
        is_healthy, details = self.check_database()
        status['components']['database'] = {
            'healthy': is_healthy,
            **details
        }

        # Workers
        workers_status = self.check_workers_alive()
        status['components']['workers'] = {
            'alive_count': len(workers_status.get('alive', [])),
            'dead_count': len(workers_status.get('dead', [])),
            'alive': workers_status.get('alive', []),
            'dead': workers_status.get('dead', [])
        }

        # Telegram bot (check process)
        result = subprocess.run(
            ["pgrep", "-f", "telegram_bot"],
            capture_output=True
        )
        status['components']['telegram_bot'] = {
            'healthy': result.returncode == 0,
            'status': 'running' if result.returncode == 0 else 'not_running'
        }

        return status

    def run_auto_recovery(self) -> Dict:
        """
        Ejecuta recuperación automática si es necesario.

        Returns:
            Dict con acciones tomadas
        """
        actions = []

        # Check coordinator
        is_healthy, _ = self.check_coordinator()
        if not is_healthy:
            self.log("Coordinator no responde - reiniciando", "WARNING")
            if self.restart_coordinator():
                actions.append('coordinator_restarted')

        # Check workers
        workers_status = self.check_workers_alive()
        dead_count = len(workers_status.get('dead', []))
        alive_count = len(workers_status.get('alive', []))

        # Si hay menos de 8 workers vivos, reiniciar
        if alive_count < 8:
            self.log(f"Solo {alive_count} workers vivos - reiniciando todos", "WARNING")
            self.restart_macbook_workers()
            self.restart_linux_workers()
            self.restart_macbook_air_workers()
            actions.append('workers_restarted')

        # Check telegram bot
        result = subprocess.run(["pgrep", "-f", "telegram_bot"], capture_output=True)
        if result.returncode != 0:
            self.log("Telegram bot no está corriendo - reiniciando", "WARNING")
            self.restart_telegram_bot()
            actions.append('telegram_bot_restarted')

        return {'actions': actions}

    def run_monitoring_loop(self, interval: int = MONITOR_INTERVAL):
        """
        Loop principal de monitoreo.

        Args:
            interval: Segundos entre verificaciones
        """
        self.log("=" * 60)
        self.log("MONITOR DAEMON INICIADO")
        self.log(f"Intervalo: {interval} segundos")
        self.log("=" * 60)

        while True:
            try:
                # Check status
                status = self.check_all()

                # Log summary
                coord_healthy = status['components']['coordinator']['healthy']
                workers_alive = status['components']['workers']['alive_count']
                db_healthy = status['components']['database']['healthy']
                tg_healthy = status['components']['telegram_bot']['healthy']

                self.log(
                    f"Status: Coordinator={'OK' if coord_healthy else 'FAIL'} | "
                    f"Workers={workers_alive} | "
                    f"DB={'OK' if db_healthy else 'FAIL'} | "
                    f"Telegram={'OK' if tg_healthy else 'FAIL'}"
                )

                # Auto-recovery if needed
                if not coord_healthy or workers_alive < 5 or not tg_healthy:
                    self.log("Ejecutando auto-recovery...", "WARNING")
                    recovery = self.run_auto_recovery()
                    if recovery['actions']:
                        self.log(f"Acciones: {recovery['actions']}")

            except KeyboardInterrupt:
                self.log("Monitor detenido por usuario")
                break
            except Exception as e:
                self.log(f"Error en loop de monitoreo: {e}", "ERROR")

            time.sleep(interval)


def main():
    """Punto de entrada principal."""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor del sistema de trading")
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Intervalo de verificación en segundos"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Ejecutar solo una vez (no loop)"
    )
    parser.add_argument(
        "--recover",
        action="store_true",
        help="Ejecutar recuperación automática inmediatamente"
    )
    args = parser.parse_args()

    monitor = SystemMonitor()

    if args.recover:
        # Solo ejecutar recuperación
        print("Ejecutando recuperación automática...")
        actions = monitor.run_auto_recovery()
        print(f"Acciones: {actions}")
        return

    if args.once:
        # Solo verificar una vez
        status = monitor.check_all()
        import json
        print(json.dumps(status, indent=2))
        return

    # Loop continuo
    monitor.run_monitoring_loop(args.interval)


if __name__ == "__main__":
    main()
