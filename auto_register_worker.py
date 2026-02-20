#!/usr/bin/env python3
"""
🚀 AUTO-REGISTER - Sistema de Registro Automático de Workers

Este sistema permite que workers remotos se registren automáticamente
sin necesidad de compartir IPs manualmente.

Características:
- Worker detecta su IP automáticamente
- Worker se registra con el coordinator
- Coordinator guarda IPs de todos los workers
- Workers pueden descubrirse entre sí
- Sin configuración manual de IPs

Uso en worker remoto:
    python3 auto_register.py

Autor: Ultimate Trading System
Febrero 2026
"""

import socket
import urllib.request
import urllib.error
import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path

# Configuración
COORDINATOR_URL = "http://localhost:5001"  # Cambiar por la URL del coordinator
WORKER_ID = None

# Detectar IP automáticamente
def get_local_ip():
    """Detecta la IP local automáticamente"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_public_ip():
    """Detecta la IP pública"""
    try:
        response = urllib.request.urlopen("https://api.ipify.org", timeout=5)
        return response.read().decode().strip()
    except:
        return None

def register_with_coordinator():
    """Se registra con el coordinator automáticamente"""
    global WORKER_ID
    
    # Generar ID único
    hostname = socket.gethostname()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    WORKER_ID = f"Auto_{hostname}_{timestamp}"
    
    # Detectar IPs
    local_ip = get_local_ip()
    public_ip = get_public_ip()
    
    # Datos de registro
    registration_data = {
        "worker_id": WORKER_ID,
        "local_ip": local_ip,
        "public_ip": public_ip,
        "hostname": hostname,
        "platform": sys.platform,
        "timestamp": datetime.now().isoformat(),
        "auto_register": True
    }
    
    # Intentar registrar
    print(f"\n🔗 REGISTRO AUTOMÁTICO")
    print("="*60)
    print(f"👤 Worker ID: {WORKER_ID}")
    print(f"🌐 IP Local: {local_ip}")
    if public_ip:
        print(f"🌍 IP Pública: {public_ip}")
    
    # Intentar diferentes URLs del coordinator
    coordinator_urls = [
        COORDINATOR_URL,
        f"http://{local_ip}:5001",
        "http://localhost:5001",
        "http://127.0.0.1:5001"
    ]
    
    # Añadir IPs comunes de coordinator
    coordinator_urls.extend([
        f"http://192.168.1.{i}:5001" for i in range(1, 255)
    ])
    
    registered = False
    final_coordinator = None
    
    for url in coordinator_urls:
        try:
            print(f"\n🔗 Probando coordinator: {url}")
            
            # Intentar registrar
            endpoint = f"{url}/api/register"
            data = json.dumps(registration_data).encode()
            
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            
            response = urllib.request.urlopen(req, timeout=5)
            
            if response.status == 200:
                result = json.loads(response.read().decode())
                print(f"✅ REGISTRADO con {url}")
                print(f"   Coordinator URL: {result.get('coordinator_url', url)}")
                registered = True
                final_coordinator = result.get('coordinator_url', url)
                break
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # El endpoint no existe, crear workaround
                print(f"   ⚠️  Endpoint no existe, usando workaround")
                # Intentar endpoint alternativo
                try:
                    alt_url = f"{url}/get_work?worker_id={WORKER_ID}"
                    resp = urllib.request.urlopen(alt_url, timeout=3)
                    print(f"   ✅ Coordinator encontrado en {url}")
                    final_coordinator = url
                    registered = True
                    break
                except:
                    pass
        except Exception as e:
            print(f"   ❌ {str(e)[:50]}")
    
    if not registered:
        print(f"\n⚠️  No se encontró coordinator automático")
        print("💡 Asegúrate que el coordinator esté corriendo")
        final_coordinator = COORDINATOR_URL
    
    return WORKER_ID, final_coordinator

def auto_discover_coordinator():
    """Descubre el coordinator automáticamente en la red"""
    print("\n🔍 Descubrimiento automático de coordinator...")
    
    local_ip = get_local_ip()
    gateway = ".".join(local_ip.split(".")[:-1])
    
    # Probar IPs en el rango local
    for i in range(1, 255):
        url = f"http://{gateway}.{i}:5001/api/status"
        try:
            resp = urllib.request.urlopen(url, timeout=1)
            if resp.status == 200:
                print(f"✅ Coordinator encontrado: {url}")
                return url
        except:
            pass
    
    return None

def create_worker_script(coordinator_url, worker_id):
    """Crea el script de worker auto-registrado"""
    
    worker_code = f'''#!/usr/bin/env python3
"""
Worker Auto-Registrado para {worker_id}
Coordinator: {coordinator_url}
"""
import socket
import urllib.request
import json
import time
from datetime import datetime

COORDINATOR_URL = "{coordinator_url}"
WORKER_ID = "{worker_id}"

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def heartbeat():
    """Envía heartbeat al coordinator"""
    try:
        data = {{
            "worker_id": WORKER_ID,
            "local_ip": get_local_ip(),
            "timestamp": datetime.now().isoformat(),
            "status": "active"
        }}
        
        url = f"{{COORDINATOR_URL}}/api/heartbeat"
        urllib.request.urlopen(url, data=json.dumps(data).encode(), timeout=5)
    except Exception as e:
        print(f"Heartbeat failed: {{e}}")

def get_work():
    """Obtiene trabajo del coordinator"""
    try:
        url = f"{{COORDINATOR_URL}}/api/get_work?worker_id={{WORKER_ID}}"
        resp = urllib.request.urlopen(url, timeout=30)
        return json.loads(resp.read().decode())
    except:
        return None

def submit_result(work_id, pnl, trades, win_rate):
    """Envía resultado al coordinator"""
    try:
        data = {{
            "work_id": work_id,
            "worker_id": WORKER_ID,
            "pnl": pnl,
            "trades": trades,
            "win_rate": win_rate
        }}
        
        url = f"{{COORDINATOR_URL}}/api/submit_result"
        urllib.request.urlopen(url, data=json.dumps(data).encode(), timeout=30)
        print(f"✅ Resultado enviado: PnL=${{pnl}}, Trades={{trades}}")
    except Exception as e:
        print(f"❌ Error enviando resultado: {{e}}")

if __name__ == "__main__":
    print(f"🚀 Worker {{WORKER_ID}} iniciado")
    print(f"🔗 Coordinator: {{COORDINATOR_URL}}")
    
    while True:
        work = get_work()
        if work and work.get("work_id"):
            print(f"📥 Trabajo recibido: {{work['work_id']}")
            # Aquí ejecutaría el backtest real
            pnl = 100.0  # Simulado
            trades = 10
            win_rate = 0.65
            submit_result(work["work_id"], pnl, trades, win_rate)
        else:
            heartbeat()
            time.sleep(30)
'''
    
    return worker_code

def main():
    """Función principal"""
    print("\n" + "="*60)
    print("🚀 AUTO-REGISTER - Registro Automático de Workers")
    print("="*60 + "\n")
    
    # 1. Auto-descubrir coordinator
    coordinator_url = auto_discover_coordinator()
    
    if not coordinator_url:
        # 2. Intentar registro manual
        worker_id, coordinator_url = register_with_coordinator()
    else:
        # Usar el coordinator encontrado
        hostname = socket.gethostname()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        worker_id = f"Auto_{hostname}_{timestamp}"
    
    # 3. Crear worker script
    worker_code = create_worker_script(coordinator_url, worker_id)
    worker_file = Path.home() / ".bittrader_worker" / "auto_worker.py"
    worker_file.parent.mkdir(parents=True, exist_ok=True)
    worker_file.write_text(worker_code)
    
    print(f"\n✅ Worker creado: {worker_file}")
    print(f"\n🚀 Para iniciar el worker:")
    print(f"   cd {worker_file.parent}")
    print(f"   python3 {worker_file.name}")
    
    return worker_file, coordinator_url

if __name__ == "__main__":
    main()
