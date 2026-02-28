#!/usr/bin/env python3
"""
TELEGRAM BOT - Strategy Miner Monitor
Escucha comandos y envía notificaciones de progreso
"""

import os
import requests
import time
import json
import sqlite3
import subprocess
import threading

# Configuración - desde variables de entorno
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("ERROR: TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID deben estar configurados en .env")
COORDINATOR_URL = "http://localhost:5001"
LINUX_HOST = "enderj@10.0.0.240"
PAPER_DB = "/tmp/paper_trading_pipeline.db"

# Estado
last_update_id = 0
last_completed = 0
monitoring = True

def send_message(text):
    """Envía mensaje a Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def get_updates():
    """Obtiene mensajes nuevos"""
    global last_update_id
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 30}
    try:
        response = requests.get(url, params=params, timeout=35)
        return response.json().get("result", [])
    except:
        return []

def get_coordinator_status():
    """Obtiene estado del coordinador"""
    try:
        response = requests.get(f"{COORDINATOR_URL}/api/status", timeout=5)
        return response.json()
    except:
        return None

def get_workers():
    """Obtiene lista de workers"""
    try:
        response = requests.get(f"{COORDINATOR_URL}/api/workers", timeout=5)
        return response.json().get("workers", [])
    except:
        return []

def get_linux_progress():
    """Obtiene progreso de todos los workers Linux (multi-worker)"""
    try:
        all_progress = []
        for i in range(1, 6):  # Workers 1, 2, 3, 4, 5
            try:
                result = subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", LINUX_HOST,
                     f"grep -a -E 'Gen [0-9]+.*PnL' ~/crypto_worker/worker_{i}.log 2>/dev/null | tail -1"],
                    capture_output=True, text=True, timeout=10
                )
                if result.stdout.strip():
                    last_line = result.stdout.strip()
                    all_progress.append(f"W{i}: {last_line}")
            except:
                pass
        return '\n'.join(all_progress) if all_progress else "Sin datos"
    except:
        return "Sin datos"

def get_macpro_progress():
    """Obtiene progreso de todos los workers MacBook Pro (multi-worker)"""
    try:
        all_progress = []
        for i in range(1, 4):  # Workers 1, 2, 3
            log_file = f"/tmp/worker_{i}.log"
            try:
                result = subprocess.run(
                    ["grep", "-a", "-E", "Gen [0-9]+.*PnL", log_file],
                    capture_output=True, text=True, timeout=5
                )
                if result.stdout.strip():
                    last_line = result.stdout.strip().split('\n')[-1].strip()
                    all_progress.append(f"W{i}: {last_line}")
            except:
                pass
        return '\n'.join(all_progress) if all_progress else "No disponible"
    except:
        return "No disponible"

def get_paper_status():
    """Get paper trading status from pipeline DB."""
    if not os.path.exists(PAPER_DB):
        return None
    try:
        conn = sqlite3.connect(PAPER_DB)
        c = conn.cursor()
        c.execute("""SELECT strategy_id, contract, paper_pnl, paper_trades,
                     paper_winrate, train_pnl, degradation_vs_paper, status
                     FROM paper_strategies ORDER BY paper_pnl DESC""")
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception:
        return None

def get_paper_trades_recent(limit=10):
    """Get recent paper trades."""
    if not os.path.exists(PAPER_DB):
        return None
    try:
        conn = sqlite3.connect(PAPER_DB)
        c = conn.cursor()
        c.execute("""SELECT strategy_id, contract, direction, entry_price,
                     exit_price, pnl, timestamp
                     FROM paper_trades ORDER BY timestamp DESC LIMIT ?""", (limit,))
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception:
        return None

def handle_command(text):
    """Procesa comandos"""
    text = text.lower().strip()

    if text in ["/start", "/help", "hola", "help"]:
        return """<b>Strategy Miner Bot</b>

Comandos disponibles:
/status - Estado del sistema
/workers - Workers activos
/progress - Progreso actual
/linux - Progreso worker Linux
/paper - Paper trading status
/paper_trades - Ultimos 10 paper trades
/paper_compare - Paper vs backtest
/daily_report - Reporte diario de P&L
/kill - EMERGENCIA: cerrar todas las posiciones
/help - Este mensaje"""

    elif text == "/status":
        status = get_coordinator_status()
        if status:
            wu = status["work_units"]
            workers = status["workers"]["active"]
            return f"""<b>Estado del Sistema</b>

Work Units:
- Completados: {wu['completed']}/{wu['total']}
- En progreso: {wu['in_progress']}
- Pendientes: {wu['pending']}

Workers activos: {workers}"""
        else:
            return "Error: No se pudo conectar al coordinador"

    elif text == "/workers":
        workers = get_workers()
        if workers:
            msg = f"<b>Workers Activos ({len(workers)})</b>\n\n"
            for i, w in enumerate(workers, 1):
                # Determinar icono según sistema
                if "Linux" in w['id']:
                    icon = "🐧"
                elif "Darwin" in w['id'] or "Mac" in w['id']:
                    icon = "🍎"
                else:
                    icon = "💻"

                # Formatear tiempo de ejecución
                exec_time = w.get('total_execution_time', 0)
                hours = int(exec_time // 3600)
                mins = int((exec_time % 3600) // 60)

                # Nombre corto
                name = w['id'].split('_')[0].replace('.local', '')

                msg += f"{icon} <b>{name}</b>\n"
                msg += f"   Sistema: {w['id'].split('_')[-1]}\n"
                msg += f"   WU Completados: {w['work_units_completed']}\n"
                msg += f"   Tiempo: {hours}h {mins}m\n"
                msg += f"   Estado: {w['status']}\n\n"
            return msg
        else:
            return "No hay workers conectados"

    elif text == "/progress":
        linux_progress = get_linux_progress()
        macpro_progress = get_macpro_progress()

        msg = "<b>Progreso de Workers</b>\n\n"

        msg += "🐧 <b>Linux:</b>\n"
        if linux_progress and linux_progress != "No disponible":
            msg += f"<code>{linux_progress}</code>\n\n"
        else:
            msg += "<code>No disponible</code>\n\n"

        msg += "🍎 <b>MacBook Pro:</b>\n"
        if macpro_progress and macpro_progress != "No disponible":
            msg += f"<code>{macpro_progress}</code>"
        else:
            msg += "<code>No disponible</code>"

        return msg

    elif text == "/linux":
        progress = get_linux_progress()
        if progress:
            return f"<b>Progreso Worker Linux</b>\n\n<code>{progress}</code>"
        else:
            return "No hay progreso disponible"

    elif text == "/macpro":
        progress = get_macpro_progress()
        if progress:
            return f"<b>Progreso Worker MacBook Pro</b>\n\n<code>{progress}</code>"
        else:
            return "No hay progreso disponible"

    elif text == "/paper":
        rows = get_paper_status()
        if not rows:
            return "No hay paper trading activo."
        msg = "<b>Paper Trading Status</b>\n\n"
        total_pnl = 0
        for r in rows:
            sid, contract, ppnl, ptrades, pwr, tpnl, deg, status = r
            ppnl = ppnl or 0
            ptrades = ptrades or 0
            icon = "+" if ppnl >= 0 else "-"
            total_pnl += ppnl
            msg += f"[{icon}] {sid}\n"
            msg += f"  PnL: ${ppnl:.2f} | Trades: {ptrades}\n"
            msg += f"  Status: {status}\n\n"
        msg += f"<b>Total PnL: ${total_pnl:.2f}</b>"
        return msg

    elif text == "/paper_trades":
        rows = get_paper_trades_recent(10)
        if not rows:
            return "No hay paper trades recientes."
        msg = "<b>Ultimos 10 Paper Trades</b>\n\n"
        for r in rows:
            sid, contract, direction, entry, exit_p, pnl, ts = r
            pnl = pnl or 0
            icon = "+" if pnl >= 0 else "-"
            msg += f"[{icon}] {direction} {contract}\n"
            msg += f"  Entry: ${entry:.2f} -> Exit: ${exit_p:.2f}\n"
            msg += f"  PnL: ${pnl:.2f} | {ts}\n\n"
        return msg

    elif text == "/paper_compare":
        rows = get_paper_status()
        if not rows:
            return "No hay paper trading para comparar."
        msg = "<b>Paper vs Backtest</b>\n\n"
        for r in rows:
            sid, contract, ppnl, ptrades, pwr, tpnl, deg, status = r
            ppnl = ppnl or 0
            tpnl = tpnl or 0
            deg = deg or 0
            deg_icon = "OK" if deg < 0.25 else "WARN" if deg < 0.5 else "BAD"
            msg += f"<b>{sid}</b>\n"
            msg += f"  Paper: ${ppnl:.2f} | Train: ${tpnl:.2f}\n"
            msg += f"  Degradation: {deg*100:.1f}% [{deg_icon}]\n\n"
        return msg

    elif text == "/daily_report":
        try:
            from daily_trading_report import generate_report
            report = generate_report()
            return report if report else "No hay datos para el reporte."
        except ImportError:
            return "daily_trading_report.py no disponible."
        except Exception as e:
            return f"Error generando reporte: {e}"

    elif text == "/kill":
        try:
            from live_spot_executor import LiveSpotExecutor
            from risk_manager_live import emergency_close_all, RiskManager, SPOT_RISK_CONFIG
            executor = LiveSpotExecutor(dry_run=False)
            rm = RiskManager(initial_balance=500, config=SPOT_RISK_CONFIG)
            emergency_close_all(executor, rm)
            return "<b>KILL SWITCH ACTIVADO</b>\n\nTodas las posiciones cerradas.\nTrading HALT activado."
        except Exception as e:
            return f"Error en kill switch: {e}"

    else:
        return "Comando no reconocido. Usa /help para ver comandos disponibles."

def check_notifications():
    """Verifica si hay que enviar notificaciones"""
    global last_completed

    status = get_coordinator_status()
    if status:
        completed = status["work_units"]["completed"]
        if completed > last_completed:
            send_message(f"""<b>Work Unit Completado!</b>

Completados: {completed}/{status['work_units']['total']}
Pendientes: {status['work_units']['pending']}
Workers: {status['workers']['active']}""")
            last_completed = completed

def send_progress_report():
    """Envía reporte de progreso"""
    status = get_coordinator_status()
    linux_progress = get_linux_progress()
    macpro_progress = get_macpro_progress()

    if status:
        wu = status["work_units"]
        msg = f"""<b>📊 Reporte de Progreso</b>

<b>Work Units:</b>
✅ Completados: {wu['completed']}/{wu['total']}
⏳ En progreso: {wu['in_progress']}
📋 Pendientes: {wu['pending']}

<b>Workers activos:</b> {status['workers']['active']}

🐧 <b>Linux:</b>
<code>{linux_progress if linux_progress and linux_progress != 'No disponible' else 'Sin datos'}</code>

🍎 <b>MacBook Pro:</b>
<code>{macpro_progress if macpro_progress and macpro_progress != 'No disponible' else 'Sin datos'}</code>"""
        send_message(msg)

def notification_loop():
    """Loop de notificaciones cada 30 minutos"""
    report_counter = 0
    while monitoring:
        check_notifications()
        report_counter += 1

        # Enviar reporte cada 30 minutos (6 ciclos de 5 min)
        if report_counter >= 6:
            send_progress_report()
            report_counter = 0

        time.sleep(300)

def main():
    global last_update_id, monitoring

    print("=" * 50)
    print("TELEGRAM BOT - Strategy Miner")
    print("=" * 50)
    print(f"Bot activo. Escuchando comandos...")
    print()

    # Enviar mensaje de inicio
    send_message("""<b>Bot Iniciado</b>

Ahora respondo a comandos:
/status - Estado del sistema
/workers - Workers activos
/progress - Progreso actual
/help - Ayuda""")

    # Iniciar thread de notificaciones
    notification_thread = threading.Thread(target=notification_loop, daemon=True)
    notification_thread.start()

    # Loop principal - escuchar comandos
    while True:
        try:
            updates = get_updates()

            for update in updates:
                last_update_id = update["update_id"]

                if "message" in update:
                    message = update["message"]
                    chat_id = message["chat"]["id"]
                    text = message.get("text", "")

                    if str(chat_id) == CHAT_ID and text:
                        print(f"[{time.strftime('%H:%M:%S')}] Comando: {text}")
                        response = handle_command(text)
                        send_message(response)

        except KeyboardInterrupt:
            print("\nBot detenido")
            monitoring = False
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
