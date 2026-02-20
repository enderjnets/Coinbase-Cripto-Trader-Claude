#!/usr/bin/env python3
"""
TELEGRAM BOT SMART - Con Superpoderes de Claude
===============================================
- Comunicación bidireccional con Claude Code
- Bot inteligente con Claude API (funciona 24/7)
- Monitoreo del sistema de trading
"""

import requests
import time
import json
import subprocess
import threading
import os
from datetime import datetime
from pathlib import Path

# ============================================
# CONFIGURACIÓN
# ============================================
BOT_TOKEN = "TELEGRAM_BOT_TOKEN_REDACTED"
CHAT_ID = "771213858"
COORDINATOR_URL = "http://localhost:5001"
LINUX_HOST = "enderj@10.0.0.240"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Archivos de comunicación con Claude Code
MESSAGES_FILE = Path("/tmp/telegram_messages.json")
CLAUDE_OUTBOX = Path("/tmp/claude_outbox.json")

# Estado
last_update_id = 0
last_completed = 0
monitoring = True

# ============================================
# FUNCIONES DE TELEGRAM
# ============================================
def send_message(text, parse_mode="HTML"):
    """Envía mensaje a Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": parse_mode}
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Error enviando mensaje: {e}")
        return None

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

# ============================================
# FUNCIONES DEL SISTEMA
# ============================================
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
    """Obtiene progreso de workers Linux"""
    try:
        all_progress = []
        for i in range(1, 6):
            try:
                result = subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=3", "-o", "BatchMode=yes", LINUX_HOST,
                     f"grep -a -E 'Gen [0-9]+.*PnL' ~/crypto_worker/worker_{i}.log 2>/dev/null | tail -1"],
                    capture_output=True, text=True, timeout=8
                )
                if result.stdout.strip():
                    all_progress.append(f"W{i}: {result.stdout.strip()}")
            except:
                pass
        return '\n'.join(all_progress) if all_progress else "Sin conexión"
    except:
        return "Sin conexión"

def get_macpro_progress():
    """Obtiene progreso de workers MacBook Pro"""
    try:
        all_progress = []
        for i in range(1, 4):
            try:
                result = subprocess.run(
                    ["grep", "-a", "-E", "Gen [0-9]+.*PnL", f"/tmp/worker_{i}.log"],
                    capture_output=True, text=True, timeout=5
                )
                if result.stdout.strip():
                    last_line = result.stdout.strip().split('\n')[-1].strip()
                    all_progress.append(f"W{i}: {last_line}")
            except:
                pass
        return '\n'.join(all_progress) if all_progress else "Sin datos"
    except:
        return "Sin datos"

def get_system_context():
    """Genera contexto del sistema para Claude"""
    status = get_coordinator_status()
    workers = get_workers()

    active_workers = [w for w in workers if w.get('status') == 'active'] if workers else []
    mac_workers = [w for w in active_workers if 'Darwin' in w.get('id', '')]
    linux_workers = [w for w in active_workers if 'Linux' in w.get('id', '')]

    context = f"""
SISTEMA: Crypto Strategy Miner - Sistema de trading distribuido
ESTADO ACTUAL ({datetime.now().strftime('%Y-%m-%d %H:%M')}):

COORDINATOR: {'Activo' if status else 'Inactivo'}
"""

    if status:
        wu = status.get('work_units', {})
        best = status.get('best_strategy', {})
        context += f"""
WORK UNITS:
- Total: {wu.get('total', 0)}
- Completados: {wu.get('completed', 0)}
- En progreso: {wu.get('in_progress', 0)}
- Pendientes: {wu.get('pending', 0)}

MEJOR ESTRATEGIA:
- PnL: ${best.get('pnl', 0):.2f}
- Win Rate: {best.get('win_rate', 0)*100:.0f}%
- Trades: {best.get('trades', 0)}

WORKERS:
- MacBook Pro: {len(mac_workers)} activos
- Linux ROG: {len(linux_workers)} activos
- Total: {len(active_workers)} activos
"""

    return context

# ============================================
# CLAUDE API INTEGRATION
# ============================================
def ask_claude(user_message, system_context=""):
    """Envía mensaje a Claude API y obtiene respuesta"""
    if not ANTHROPIC_API_KEY:
        return "Error: API key de Anthropic no configurada"

    try:
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        system_prompt = f"""Eres un asistente de trading que ayuda a monitorear y gestionar un sistema de trading de criptomonedas distribuido.

Tu dueño es Ender y te comunicas con él via Telegram. Responde de forma concisa y útil.
Puedes usar emojis para hacer los mensajes más claros.
Si te preguntan sobre el sistema, usa el contexto proporcionado.
Si no sabes algo, dilo honestamente.

CONTEXTO DEL SISTEMA:
{system_context}
"""

        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}]
        }

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("content", [{}])[0].get("text", "Sin respuesta")
        else:
            return f"Error API: {response.status_code}"

    except Exception as e:
        return f"Error: {str(e)}"

# ============================================
# COMUNICACIÓN CON CLAUDE CODE
# ============================================
def save_incoming_message(text, from_user="Ender"):
    """Guarda mensaje entrante para que Claude Code lo lea"""
    messages = []
    if MESSAGES_FILE.exists():
        try:
            messages = json.loads(MESSAGES_FILE.read_text())
        except:
            messages = []

    messages.append({
        "timestamp": datetime.now().isoformat(),
        "from": from_user,
        "text": text,
        "read": False
    })

    # Mantener solo los últimos 50 mensajes
    messages = messages[-50:]
    MESSAGES_FILE.write_text(json.dumps(messages, indent=2))

def check_claude_outbox():
    """Verifica si Claude Code tiene mensajes para enviar"""
    if CLAUDE_OUTBOX.exists():
        try:
            messages = json.loads(CLAUDE_OUTBOX.read_text())
            if messages:
                for msg in messages:
                    send_message(msg.get("text", ""))
                # Limpiar outbox
                CLAUDE_OUTBOX.write_text("[]")
        except:
            pass

# ============================================
# COMANDOS
# ============================================
def handle_command(text):
    """Procesa comandos y mensajes"""
    text_lower = text.lower().strip()

    # Comandos básicos
    if text_lower in ["/start", "/help", "help"]:
        return """<b>🤖 Bot Smart con Claude</b>

<b>Comandos:</b>
/status - Estado del sistema
/workers - Workers activos
/progress - Progreso actual
/ask [pregunta] - Preguntar a Claude

<b>Chat libre:</b>
Escribe cualquier cosa y Claude te responderá con contexto del sistema de trading.

<b>Comunicación con Claude Code:</b>
Tus mensajes se guardan para que Claude Code los lea cuando esté activo."""

    elif text_lower == "/status":
        status = get_coordinator_status()
        if status:
            wu = status["work_units"]
            best = status.get("best_strategy", {})
            return f"""<b>📊 Estado del Sistema</b>

<b>Work Units:</b>
✅ Completados: {wu['completed']}/{wu['total']}
⏳ En progreso: {wu['in_progress']}
📋 Pendientes: {wu['pending']}

<b>Mejor Estrategia:</b>
💰 PnL: ${best.get('pnl', 0):.2f}
📈 Win Rate: {best.get('win_rate', 0)*100:.0f}%

<b>Workers:</b> {status['workers']['active']} activos"""
        else:
            return "❌ No se pudo conectar al coordinator"

    elif text_lower == "/workers":
        workers = get_workers()
        active = [w for w in workers if w.get('status') == 'active']
        if active:
            msg = f"<b>👥 Workers Activos ({len(active)})</b>\n\n"
            for w in active:
                icon = "🐧" if "Linux" in w['id'] else "🍎"
                name = w['id'].split('_')[0].replace('.local', '')
                msg += f"{icon} {name} - {w['id'].split('_')[-1]}\n"
            return msg
        else:
            return "No hay workers activos"

    elif text_lower == "/progress":
        linux = get_linux_progress()
        macpro = get_macpro_progress()
        status = get_coordinator_status()

        msg = "<b>📈 Progreso Actual</b>\n\n"

        if status:
            msg += f"<b>Workers activos:</b> {status['workers']['active']}\n\n"

        msg += f"🐧 <b>Linux ROG:</b>\n<code>{linux}</code>\n\n"
        msg += f"🍎 <b>MacBook Pro:</b>\n<code>{macpro}</code>"

        return msg

    elif text_lower.startswith("/ask "):
        question = text[5:].strip()
        if question:
            context = get_system_context()
            response = ask_claude(question, context)
            return response
        else:
            return "Uso: /ask [tu pregunta]"

    else:
        # Chat libre - guardar mensaje y responder con Claude
        save_incoming_message(text)

        # Si no empieza con /, responder con Claude
        if not text.startswith("/"):
            context = get_system_context()
            response = ask_claude(text, context)
            return response
        else:
            return "Comando no reconocido. Usa /help para ver comandos."

# ============================================
# NOTIFICACIONES AUTOMÁTICAS
# ============================================
def check_notifications():
    """Verifica si hay que enviar notificaciones"""
    global last_completed

    status = get_coordinator_status()
    if status:
        completed = status["work_units"]["completed"]
        if completed > last_completed and last_completed > 0:
            best = status.get('best_strategy', {})
            send_message(f"""<b>✅ Work Unit Completado!</b>

Completados: {completed}/{status['work_units']['total']}
Mejor PnL: ${best.get('pnl', 0):.2f}
Workers: {status['workers']['active']}""")
        last_completed = completed

def send_progress_report():
    """Envía reporte de progreso"""
    status = get_coordinator_status()
    linux = get_linux_progress()
    macpro = get_macpro_progress()

    if status:
        wu = status["work_units"]
        best = status.get("best_strategy", {})

        msg = f"""<b>📊 Reporte de Progreso</b>

<b>Work Units:</b>
✅ Completados: {wu['completed']}/{wu['total']}
⏳ En progreso: {wu['in_progress']}
📋 Pendientes: {wu['pending']}

<b>Mejor PnL:</b> ${best.get('pnl', 0):.2f}
<b>Workers activos:</b> {status['workers']['active']}

🐧 <b>Linux:</b>
<code>{linux}</code>

🍎 <b>MacBook Pro:</b>
<code>{macpro}</code>"""
        send_message(msg)

def notification_loop():
    """Loop de notificaciones"""
    report_counter = 0
    while monitoring:
        check_notifications()
        check_claude_outbox()  # Verificar mensajes de Claude Code
        report_counter += 1

        # Reporte cada 30 minutos
        if report_counter >= 6:
            send_progress_report()
            report_counter = 0

        time.sleep(300)

# ============================================
# MAIN
# ============================================
def main():
    global last_update_id, monitoring

    print("=" * 50)
    print("🤖 TELEGRAM BOT SMART - Con Claude")
    print("=" * 50)
    print(f"API Key: {'✅ Configurada' if ANTHROPIC_API_KEY else '❌ No configurada'}")
    print(f"Coordinator: {COORDINATOR_URL}")
    print()

    # Mensaje de inicio
    send_message("""<b>🤖 Bot Smart Iniciado</b>

Ahora puedo:
• Responder preguntas con IA (Claude)
• Monitorear el sistema de trading
• Comunicarme con Claude Code

Escribe cualquier cosa o usa /help""")

    # Iniciar thread de notificaciones
    notification_thread = threading.Thread(target=notification_loop, daemon=True)
    notification_thread.start()

    # Loop principal
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
                        print(f"[{time.strftime('%H:%M:%S')}] 📩 {text[:50]}...")
                        response = handle_command(text)
                        send_message(response)

        except KeyboardInterrupt:
            print("\n👋 Bot detenido")
            monitoring = False
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
