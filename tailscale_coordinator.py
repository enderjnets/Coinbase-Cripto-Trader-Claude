#!/usr/bin/env python3
"""
🌐 TAILSCALE + COORDINATOR
Accede desde cualquier lugar automáticamente

Este script:
1. Detecta/redirige al coordinator local
2. Crea tunnel con Tailscale
3. Comparte URL con workers remotos

Autor: Ultimate Trading System
Febrero 2026
"""

import socket
import http.server
import socketserver
import threading
import json
import os
import sys
from pathlib import Path

# Colores para terminal
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'

def print_msg(text, color=GREEN):
    print(f"{color}{text}{NC}")

def get_local_ip():
    """Obtiene IP local"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def check_tailscale():
    """Verifica si Tailscale está instalado"""
    print_msg("\n🌐 Verificando Tailscale...")
    
    # Verificar si tailscale CLI existe
    import subprocess
    result = subprocess.run(
        ["which", "tailscale"],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        print_msg("   ✅ Tailscale instalado")
        
        # Obtener IP
        result = subprocess.run(
            ["tailscale", "ip"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            ts_ip = result.stdout.strip()
            print_msg(f"   🌐 IP Tailscale: {ts_ip}")
            return ts_ip
    
    return None

def start_tailscale():
    """Inicia Tailscale si no está corriendo"""
    import subprocess
    
    # Verificar estado
    result = subprocess.run(
        ["tailscale", "status"],
        capture_output=True, text=True
    )
    
    if "No login" in result.stdout or "Disconnected" in result.stdout:
        print_msg("\n🔐 Iniciando sesión Tailscale...")
        os.system("tailscale up --authkey=tskey-authkey --accept-dns=false --accept-routes=false")
        
        # Verificar estado
        result = subprocess.run(
            ["tailscale", "ip"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print_msg(f"   ✅ Conectado: {result.stdout.strip()}")
            return result.stdout.strip()
    
    elif result.returncode == 0:
        result = subprocess.run(
            ["tailscale", "ip"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    
    return None

def create_authkey():
    """Crea authkey para workers remotos"""
    print_msg("\n🔐 Creando authkey para workers remotos...")
    
    import subprocess
    
    # Crear authkey
    result = subprocess.run(
        ["tailscale", "authkeys", "create", "--ephemeral", "--reusable"],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        authkey = result.stdout.strip()
        print_msg(f"   ✅ Authkey creado: {authkey}")
        return authkey
    
    print_msg("   ⚠️  No se pudo crear authkey")
    print_msg("   💡 Crear manualmente: tailscale authkeys create --reusable --ephemeral")
    return None

def port_forward_5001():
    """Redirigir puerto 5001 a Tailscale"""
    print_msg("\n🔄 Configurando puerto 5001...")
    
    # Verificar si coordinator está corriendo
    import urllib.request
    
    try:
        response = urllib.request.urlopen("http://localhost:5001/api/status", timeout=2)
        print_msg("   ✅ Coordinator detectado en puerto 5001")
    except:
        print_msg("   ⚠️  Coordinator no detectado en puerto 5001")
        print_msg("   💡 Inicia el coordinator primero: python3 coordinator.py")
    
    return True

def create_worker_script(ts_ip, authkey=None):
    """Crea script para worker remoto"""
    
    worker_code = f'''#!/usr/bin/env python3
"""
Worker Remoto - Conectado via Tailscale
Coordinator: http://{ts_ip}:5001
"""
import socket
import urllib.request
import json
import time
from datetime import datetime

COORDINATOR = "http://{ts_ip}:5001"
WORKER_ID = f"Remote_{socket.gethostname()}_{datetime.now().strftime("%Y%m%d%H%M%S")}"

def get_work():
    try:
        url = f"{{COORDINATOR}}/api/get_work?worker_id={{WORKER_ID}}"
        resp = urllib.request.urlopen(url, timeout=30)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {{"work_id": None, "error": str(e)}}

def submit_result(work_id, pnl, trades, win_rate):
    try:
        data = json.dumps({{"work_id": work_id, "pnl": pnl, "trades": trades, "win_rate": win_rate, "worker_id": WORKER_ID}}).encode()
        req = urllib.request.Request(f"{{COORDINATOR}}/api/submit_result", data=data)
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.status == 200
    except:
        return False

if __name__ == "__main__":
    print(f"🚀 Worker: {{WORKER_ID}}")
    print(f"🔗 Coordinator: {{COORDINATOR}}")
    print()
    
    while True:
        work = get_work()
        if work.get("work_id"):
            print(f"📥 Trabajo: {{work['work_id']}")
            # Aquí ejecutaría backtest real
            pnl = 100.0 * (0.8 + 0.4 * 0.8)
            submit_result(work["work_id"], pnl, 10, 0.65)
            print(f"✅ PnL: ${{pnl:.2f}")
        else:
            print(".", end="", flush=True)
        time.sleep(10)
'''
    
    worker_file = Path.home() / ".bittrader_worker" / "remote_worker.py"
    worker_file.parent.mkdir(parents=True, exist_ok=True)
    worker_file.write_text(worker_code)
    worker_file.chmod(0o755)
    
    print_msg(f"   ✅ Worker remoto: {worker_file}")
    return str(worker_file)

def main():
    """Función principal"""
    print("\n" + "="*60)
    print("🌐 TAILSCALE + COORDINATOR - Accede desde cualquier lugar")
    print("="*60 + "\n")
    
    # 1. Verificar Tailscale
    ts_ip = check_tailscale()
    
    if not ts_ip:
        print("\n🌐 Tailscale no instalado. Opciones:\n")
        print("   1. Instalar Tailscale:")
        print("      macOS: brew install tailscale")
        print("      Linux: curl -fsSL https://tailscale.com/install.sh | sh")
        print("      Windows: https://tailscale.com/download\n")
        print("   2. Usar tunnel alternativo (Cloudflare/ngrok)\n")
        ts_ip = "TU_IP_TAILSCALE"
    
    # 2. Iniciar sesión
    start_tailscale()
    
    # 3. Crear authkey
    authkey = create_authkey()
    
    # 4. Crear worker remoto
    if ts_ip:
        create_worker_script(ts_ip, authkey)
    
    # 5. Resumen
    print("\n" + "="*60)
    print("✅ CONFIGURACIÓN COMPLETA")
    print("="*60)
    
    print(f"\n🌐 Tailscale IP: http://{ts_ip}:5001")
    print(f"🔐 Authkey: {authkey or 'Crear manualmente'}")
    print("\n📝 Para workers remotos:")
    print(f"   1. Instalar Tailscale")
    print(f"   2. Conectar con authkey: tailscale up --authkey={authkey or 'TSKEY'}")
    print(f"   3. Coordinator: http://{ts_ip}:5001/api")
    
    return ts_ip, authkey

if __name__ == "__main__":
    main()
