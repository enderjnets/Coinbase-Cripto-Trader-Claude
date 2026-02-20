#!/usr/bin/env python3
"""
TELEGRAM BOT - Strategy Miner Monitor
Escucha comandos y envía notificaciones de progreso
"""

import requests
import time
import json
import subprocess
import threading

# Configuración
BOT_TOKEN = "TELEGRAM_BOT_TOKEN_REDACTED"
CHAT_ID = "771213858"
COORDINATOR_URL = "http://localhost:5001"
LINUX_HOST = "enderj@10.0.0.240"

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
