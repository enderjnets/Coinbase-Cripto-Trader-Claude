#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
                    🔧 AUTO-DIAGNÓSTICO Y ARREGLO DEL WORKER
                    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    
    Para usar cuando estás FUERA de la red del coordinator.
    
    Este script:
    1. Pide la URL del coordinator
    2. Diagnostica problemas de conectividad
    3. Arregla automáticamente los problemas
    4. Inicia el worker
    
    USAR ASÍ:
        python3 auto_worker_setup.py
    
    El script te guiará paso a paso.
    
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import socket
import requests
import time
import json
import subprocess
from datetime import datetime

# Colores
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'═'*70}{RESET}")
    print(f"{BOLD}{BLUE}{text:^70}{RESET}")
    print(f"{BOLD}{BLUE}{'═'*70}{RESET}\n")

def print_step(num, text):
    print(f"{CYAN}📌 PASO {num}:{RESET} {text}")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text):
    print(f"{BLUE}ℹ️  {text}{RESET}")

def get_worker_id():
    """Genera ID único para este worker"""
    hostname = socket.gethostname()
    system = "Mac" if sys.platform == "darwin" else ("Linux" if sys.platform.startswith("linux") else "Win")
    instance = os.getenv('WORKER_INSTANCE', '1')
    return f"{hostname}_{system}_W{instance}"

def get_project_dir():
    """Detecta el directorio del proyecto"""
    possible_dirs = [
        os.path.expanduser("~/coinbase_trader"),
        os.path.expanduser("~/CryptoTrader"),
        os.path.expanduser("~/Desktop/Coinbase Cripto Trader Claude"),
        os.getcwd()
    ]
    
    for d in possible_dirs:
        if os.path.exists(d) and os.path.exists(os.path.join(d, "crypto_worker.py")):
            return d
    
    # Si no encontró, devuelve cwd
    return os.getcwd()

def check_python_packages():
    """Verifica e instala paquetes necesarios"""
    print_step(1, "Verificando dependencias de Python")
    
    required = ['requests']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
            print_success(f"{pkg} instalado")
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print_warning(f"Paquetes faltantes: {', '.join(missing)}")
        print_info("Instalando...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q"] + missing, check=True)
            print_success("Paquetes instalados")
        except subprocess.CalledProcessError:
            print_error("No se pudieron instalar los paquetes")
            return False
    
    return True

def test_coordinator_connection(url):
    """Prueba conexión al coordinator"""
    print_step(2, f"Probando conexión a: {url}")
    
    if not url:
        print_error("URL vacía")
        return False
    
    # Parse URL
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port or (80 if parsed.scheme == 'http' else 443)
    except Exception as e:
        print_error(f"URL inválida: {e}")
        return False
    
    # Test DNS
    try:
        ip = socket.gethostbyname(hostname)
        print_info(f"Hostname resuelto: {hostname} → {ip}")
    except socket.gaierror:
        print_error(f"No se puede resolver: {hostname}")
        return False
    
    # Test TCP port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        result = sock.connect_ex((hostname, port))
        if result == 0:
            print_success(f"Puerto {port} abierto")
        else:
            print_error(f"Puerto {port} cerrado (errno: {result})")
            return False
    except Exception as e:
        print_error(f"Error de conexión: {e}")
        return False
    finally:
        sock.close()
    
    # Test HTTP API
    try:
        response = requests.get(f"{url}/api/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success("API respondiendo")
            print_info(f"  Workers activos: {data.get('workers', {}).get('active', 'N/A')}")
            print_info(f"  Work Units: {data.get('work_units', {}).get('completed', 'N/A')}/{data.get('work_units', {}).get('total', 'N/A')}")
            return True
        else:
            print_error(f"API respondió: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("No se puede conectar a la API")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def register_worker(url, worker_id):
    """Registra este worker con el coordinator"""
    print_step(3, f"Registrando worker: {worker_id}")
    
    try:
        response = requests.get(f"{url}/api/get_work", params={'worker_id': worker_id}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('work_id'):
                print_success(f"Worker registrado y asignado work ID: {data['work_id']}")
            else:
                print_success("Worker registrado (sin trabajo disponible)")
            return True
        else:
            print_error(f"Error registrando: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def check_data_files():
    """Verifica que existan datos para backtesting"""
    print_step(4, "Verificando archivos de datos")
    
    project_dir = get_project_dir()
    data_dir = os.path.join(project_dir, "data")
    
    if not os.path.exists(data_dir):
        print_warning("Directorio 'data/' no encontrado")
        return False
    
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    
    if csv_files:
        print_success(f"{len(csv_files)} archivos CSV encontrados:")
        for f in csv_files[:3]:
            print_info(f"  - {f}")
        if len(csv_files) > 3:
            print_info(f"  ... y {len(csv_files) - 3} más")
        return True
    else:
        print_warning("No hay archivos CSV en data/")
        print_info("El worker puede fallar sin datos")
        return False  # Warning pero no fatal

def start_worker(url, worker_id):
    """Inicia el worker"""
    print_step(5, "Iniciando worker")
    
    project_dir = get_project_dir()
    worker_script = os.path.join(project_dir, "crypto_worker.py")
    
    if not os.path.exists(worker_script):
        print_error(f"crypto_worker.py no encontrado en: {project_dir}")
        print_info("Asegúrate de estar en el directorio correcto del proyecto")
        return False
    
    # Crear script de inicio
    script_content = f'''#!/bin/bash
# Auto-generated worker startup script
# Generated: {datetime.now().isoformat()}

COORDINATOR_URL="{url}"
WORKER_INSTANCE="1"
USE_RAY="false"
PYTHONUNBUFFERED=1

cd "{project_dir}"

echo "Iniciando worker..."
echo "Coordinator: $COORDINATOR_URL"
echo "Worker ID: {worker_id}"

nohup python3 -u crypto_worker.py > /tmp/worker_1.log 2>&1 &

echo "Worker iniciado (PID: $!)"
echo "Logs en: /tmp/worker_1.log"
'''
    
    script_path = os.path.join(project_dir, "auto_worker.sh")
    with open(script_path, 'w') as f:
        f.write(script_content)
    os.chmod(script_path, 0o755)
    
    print_success(f"Script creado: {script_path}")
    
    # Ofrecer iniciar
    print_info("\n¿Quieres iniciar el worker ahora? (s/n): ", end="")
    choice = input().lower().strip()
    
    if choice in ['s', 'si', 'sí', 'yes', 'y']:
        print_info("Iniciando worker...")
        try:
            result = subprocess.run(
                f'cd "{project_dir}" && bash auto_worker.sh',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print_success("Worker iniciado correctamente")
                print_info(result.stdout)
                
                # Dar tiempo para que se registre
                print_info("Esperando registro...")
                time.sleep(3)
                
                # Verificar que se registró
                print_info("Verificando registro...")
                response = requests.get(f"{url}/api/workers", timeout=10)
                workers = response.json().get('workers', [])
                worker_names = [w['id'] for w in workers]
                
                if any(worker_id in w for w in worker_names):
                    print_success(f"✅ Worker {worker_id} APARECE en la lista del coordinator!")
                else:
                    print_warning("Worker iniciado pero no aparece aún (puede tomar unos segundos)")
                
                return True
            else:
                print_error(f"Error iniciando: {result.stderr}")
                return False
        except Exception as e:
            print_error(f"Error: {e}")
            return False
    else:
        print_info("Worker no iniciado")
        print_info(f"Para iniciar manualmente: cd {project_dir} && bash auto_worker.sh")
        return True

def show_summary(connected, worker_id, coordinator_url):
    """Muestra resumen final"""
    print_header("📋 RESUMEN")
    
    print(f"Worker ID: {BOLD}{worker_id}{RESET}")
    print(f"Coordinator URL: {BOLD}{coordinator_url}{RESET}")
    print()
    
    if connected:
        print_success("✅ ¡Todo configurado correctamente!")
        print()
        print("Próximos pasos:")
        print("  1. El worker debería aparecer en la interfaz del coordinator")
        print("  2. Ver logs: tail -f /tmp/worker_1.log")
        print("  3. Para detener: pkill -f crypto_worker")
    else:
        print_warning("⚠️ Hay problemas de conectividad")
        print()
        print("Verifica:")
        print("  1. Que el coordinator esté ejecutándose")
        print("  2. Que la URL sea correcta")
        print("  3. Que no haya firewall bloqueando")

def main():
    # Banner
    print(f"""
{BOLD}{CYAN}
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║     🔧  AUTO-DIAGNÓSTICO Y ARREGLO DEL WORKER                           ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                         ║
║                                                                          ║
║     Sistema Distribuido de Strategy Mining                              ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
{RESET}
""")
    
    print_info("Este script diagnosticará y configurará tu worker automáticamente.\n")
    
    # Detectar worker ID
    worker_id = get_worker_id()
    print_info(f"Tu worker ID será: {worker_id}")
    print_info(f"Directorio del proyecto: {get_project_dir()}\n")
    
    # Pedir URL del coordinator
    print_warning("Necesitamos la URL del coordinator (pregúntale al owner):")
    print()
    print("  Si el owner te dio una IP Tailscale, usa algo como:")
    print("    http://100.xx.xx.xx:5001")
    print()
    print("  Si estás en la misma red local, usa:")
    print("    http://192.168.x.x:5001  o  http://10.x.x.x:5001")
    print()
    
    print("  URL del Coordinator (ej: http://100.77.179.14:5001): ", end="")
    coordinator_url = input().strip()
    
    if not coordinator_url:
        print_error("URL requerida")
        sys.exit(1)
    
    print()
    
    # Ejecutar diagnóstico y reparación
    all_ok = True
    
    # 1. Verificar paquetes
    if not check_python_packages():
        all_ok = False
    
    # 2. Probar conexión
    if not test_coordinator_connection(coordinator_url):
        print_error("No se puede conectar al coordinator")
        print()
        print("Posibles causas:")
        print("  1. El coordinator no está ejecutándose")
        print("  2. La URL es incorrecta")
        print("  3. Firewall bloqueando conexión")
        print()
        print("¿Quieres continuar de todos modos? (s/n): ", end="")
        if input().lower().strip() not in ['s', 'si', 'sí', 'yes']:
            sys.exit(1)
    
    # 3. Verificar datos
    check_data_files()
    
    # 4. Registrar worker
    if test_coordinator_connection(coordinator_url):  # Solo si hay conexión
        register_worker(coordinator_url, worker_id)
    
    # 5. Iniciar worker (con confirmación)
    start_worker(coordinator_url, worker_id)
    
    # Resumen
    show_summary(test_coordinator_connection(coordinator_url) if 'test_coordinator_connection' in dir() else False, worker_id, coordinator_url)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Operación cancelada por el usuario{RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{RED}Error inesperado: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
