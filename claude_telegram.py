#!/usr/bin/env python3
"""
CLAUDE CODE <-> TELEGRAM BRIDGE
===============================
Funciones para que Claude Code se comunique con el usuario via Telegram
"""

import requests
import json
from pathlib import Path
from datetime import datetime

BOT_TOKEN = "TELEGRAM_BOT_TOKEN_REDACTED"
CHAT_ID = "771213858"
MESSAGES_FILE = Path("/tmp/telegram_messages.json")
CLAUDE_OUTBOX = Path("/tmp/claude_outbox.json")

def send(text, parse_mode="HTML"):
    """
    Envía un mensaje directamente a Telegram.

    Uso desde Claude Code:
        from claude_telegram import send
        send("Hola! El sistema está funcionando correctamente")
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": parse_mode}
    try:
        r = requests.post(url, data=data, timeout=10)
        result = r.json()
        return result.get('ok', False)
    except Exception as e:
        print(f"Error enviando: {e}")
        return False

def queue(text):
    """
    Agrega mensaje a la cola para que el bot lo envíe.
    Útil cuando el bot está corriendo como proceso separado.
    """
    messages = []
    if CLAUDE_OUTBOX.exists():
        try:
            messages = json.loads(CLAUDE_OUTBOX.read_text())
        except:
            messages = []

    messages.append({
        "timestamp": datetime.now().isoformat(),
        "text": text
    })
    CLAUDE_OUTBOX.write_text(json.dumps(messages, indent=2))
    return True

def read_messages(unread_only=True, mark_read=True):
    """
    Lee mensajes del usuario desde Telegram.

    Uso desde Claude Code:
        from claude_telegram import read_messages
        messages = read_messages()
        for msg in messages:
            print(f"{msg['from']}: {msg['text']}")
    """
    if not MESSAGES_FILE.exists():
        return []

    try:
        messages = json.loads(MESSAGES_FILE.read_text())

        if unread_only:
            result = [m for m in messages if not m.get('read', False)]
        else:
            result = messages

        if mark_read and result:
            for m in messages:
                m['read'] = True
            MESSAGES_FILE.write_text(json.dumps(messages, indent=2))

        return result
    except:
        return []

def clear_messages():
    """Limpia todos los mensajes"""
    if MESSAGES_FILE.exists():
        MESSAGES_FILE.write_text("[]")
    if CLAUDE_OUTBOX.exists():
        CLAUDE_OUTBOX.write_text("[]")

def ask(question, wait_seconds=60):
    """
    Envía una pregunta al usuario y espera respuesta.

    Uso:
        from claude_telegram import ask
        respuesta = ask("¿Quieres que reinicie los workers?")
        if "si" in respuesta.lower():
            # hacer algo
    """
    import time

    # Limpiar mensajes viejos
    read_messages(mark_read=True)

    # Enviar pregunta
    send(f"🤖 <b>Claude Code pregunta:</b>\n\n{question}")

    # Esperar respuesta
    start = time.time()
    while time.time() - start < wait_seconds:
        messages = read_messages(unread_only=True)
        if messages:
            return messages[-1].get('text', '')
        time.sleep(2)

    return None

def notify(title, message):
    """Envía notificación formateada"""
    text = f"<b>🔔 {title}</b>\n\n{message}"
    return send(text)

def alert(message):
    """Envía alerta urgente"""
    text = f"⚠️ <b>ALERTA</b>\n\n{message}"
    return send(text)

def report(title, data):
    """Envía reporte con datos"""
    text = f"<b>📊 {title}</b>\n\n"
    if isinstance(data, dict):
        for k, v in data.items():
            text += f"• <b>{k}:</b> {v}\n"
    else:
        text += str(data)
    return send(text)

# ============================================
# FUNCIONES DE CONVENIENCIA
# ============================================
def status_update(workers_active, work_completed, best_pnl):
    """Envía actualización de estado rápida"""
    return send(f"""📊 <b>Status Update</b>

Workers: {workers_active} activos
Completados: {work_completed}
Mejor PnL: ${best_pnl:.2f}""")

def error_alert(error_message):
    """Envía alerta de error"""
    return send(f"❌ <b>Error detectado:</b>\n<code>{error_message}</code>")

def task_complete(task_name, result="OK"):
    """Notifica tarea completada"""
    return send(f"✅ <b>{task_name}</b> completado\n\nResultado: {result}")

# ============================================
# CLI para pruebas
# ============================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "send" and len(sys.argv) > 2:
            msg = " ".join(sys.argv[2:])
            if send(msg):
                print("✅ Mensaje enviado")
            else:
                print("❌ Error enviando")

        elif cmd == "read":
            msgs = read_messages(unread_only=False)
            if msgs:
                for m in msgs:
                    status = "📖" if m.get('read') else "📩"
                    print(f"{status} [{m['timestamp'][:16]}] {m['from']}: {m['text']}")
            else:
                print("No hay mensajes")

        elif cmd == "ask" and len(sys.argv) > 2:
            question = " ".join(sys.argv[2:])
            print(f"Enviando pregunta y esperando respuesta...")
            response = ask(question, wait_seconds=120)
            if response:
                print(f"Respuesta: {response}")
            else:
                print("Sin respuesta (timeout)")

        else:
            print("""
Uso:
    python claude_telegram.py send "mensaje"
    python claude_telegram.py read
    python claude_telegram.py ask "pregunta"
""")
    else:
        print("Claude Telegram Bridge - Importa las funciones para usar")
        print("Ejemplo: from claude_telegram import send, read_messages, ask")
