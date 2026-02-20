#!/usr/bin/env python3
"""
DIAGNÓSTICO DE CONECTIVIDAD DEL WORKER
========================================
Ejecuta esto en la máquina del friend para verificar:
1. Si puede alcanzar el coordinator
2. Si el worker puede registrarse
3. Problemas comunes de conectividad

使用方法 (en la máquina del friend):
    python3 diagnose_worker_connection.py <COORDINATOR_URL>

Ejemplo:
    python3 diagnose_worker_connection.py http://localhost:5001
    python3 diagnose_worker_connection.py http://100.77.179.14:5001
"""

import sys
import socket
import requests
import json
import time
import os

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text):
    print(f"{BLUE}ℹ️  {text}{RESET}")

def get_worker_id():
    """Genera el ID del worker"""
    hostname = socket.gethostname()
    system = os.name
    instance = os.getenv('WORKER_INSTANCE', '1')
    return f"{hostname}_{system}_W{instance}"

def test_coordinator_connection(coordinator_url):
    """Prueba 1: ¿Podemos llegar al coordinator?"""
    print_header("PRUEBA 1: Conectividad al Coordinator")
    
    if not coordinator_url:
        coordinator_url = os.getenv('COORDINATOR_URL', 'http://localhost:5001')
    
    print_info(f"URL del Coordinator: {coordinator_url}")
    
    # Test 1a: DNS/Host resolution
    print("\n1a. Resolviendo hostname...")
    try:
        from urllib.parse import urlparse
        parsed = urlparse(coordinator_url)
        hostname = parsed.hostname
        port = parsed.port or (80 if parsed.scheme == 'http' else 443)
        
        ip = socket.gethostbyname(hostname)
        print_success(f"Hostname resuelto: {hostname} → {ip}")
    except socket.gaierror as e:
        print_error(f"No se puede resolver el hostname: {e}")
        print_warning("Solución: Verifica la URL o la conexión a internet")
        return False, coordinator_url
    
    # Test 1b: TCP Connection
    print("\n1b. Conectando al puerto TCP...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        result = sock.connect_ex((hostname, port))
        if result == 0:
            print_success(f"Puerto {port} abierto ✓")
        else:
            print_error(f"Puerto {port} cerrado (errno: {result})")
            print_warning("Solución: Verifica que el coordinator esté ejecutándose")
            return False, coordinator_url
    except Exception as e:
        print_error(f"Error de conexión: {e}")
        return False, coordinator_url
    finally:
        sock.close()
    
    # Test 1c: HTTP API
    print("\n1c. Conectando a la API HTTP...")
    try:
        response = requests.get(f"{coordinator_url}/api/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success(f"API respondiendo (status code: {response.status_code})")
            print_info(f"Work Units Totales: {data.get('work_units', {}).get('total', 'N/A')}")
            print_info(f"Workers Activos: {data.get('workers', {}).get('active', 'N/A')}")
            return True, coordinator_url
        else:
            print_error(f"API respondió con código: {response.status_code}")
            return False, coordinator_url
    except requests.exceptions.ConnectionError as e:
        print_error(f"No se puede conectar a la API: {e}")
        print_warning("Posibles causas:")
        print_warning("  - El coordinator no está ejecutándose")
        print_warning("  - Firewall bloqueando la conexión")
        print_warning("  - URL incorrecta")
        return False, coordinator_url
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        return False, coordinator_url

def test_worker_registration(coordinator_url, worker_id):
    """Prueba 2: ¿Podemos registrarnos como worker?"""
    print_header("PRUEBA 2: Registro del Worker")
    
    print_info(f"ID del Worker: {worker_id}")
    
    # Test 2a: Simular llamada get_work
    print("\n2a. Intentando registrarse (llamando /api/get_work)...")
    try:
        response = requests.get(
            f"{coordinator_url}/api/get_work",
            params={'worker_id': worker_id},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('work_id'):
                print_success(f"✅ ¡Worker REGISTRADO y con TRABAJO ASIGNADO!")
                print_info(f"Work ID: {data.get('work_id')}")
                print_info(f"Estrategia: {data.get('strategy_params', {})}")
                return True
            else:
                print_warning("Worker REGISTRADO pero sin trabajo disponible")
                print_info("Esto es normal si no hay work units pendientes")
                print_info("El worker seguirá intentando periódicamente")
                return True
        else:
            print_error(f"Error en registro: {response.status_code}")
            print_error(f"Respuesta: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print_error(f"No se puede conectar: {e}")
        return False
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        return False

def test_worker_env():
    """Prueba 3: Verificar configuración del worker"""
    print_header("PRUEBA 3: Configuración del Environment")
    
    worker_id = get_worker_id()
    coord_url = os.getenv('COORDINATOR_URL', 'NO CONFIGURADO')
    
    print_info(f"WORKER_ID: {worker_id}")
    print_info(f"COORDINATOR_URL: {coord_url}")
    print_info(f"WORKER_INSTANCE: {os.getenv('WORKER_INSTANCE', '1')}")
    print_info(f"USE_RAY: {os.getenv('USE_RAY', 'false')}")
    
    # Verificar que existe crypto_worker.py
    print("\n3a. Verificando archivos del worker...")
    if os.path.exists('crypto_worker.py'):
        print_success("crypto_worker.py existe ✓")
    else:
        print_error("crypto_worker.py NO encontrado")
        print_warning("Ejecuta este script desde el directorio del proyecto")
        return False
    
    # Verificar datos
    print("\n3b. Verificando datos...")
    if os.path.exists('data'):
        csv_files = [f for f in os.listdir('data') if f.endswith('.csv')]
        if csv_files:
            print_success(f"{len(csv_files)} archivos CSV encontrados")
            for f in csv_files[:3]:
                print_info(f"  - {f}")
        else:
            print_warning("No hay archivos CSV en data/")
            print_warning("Los workers pueden fallar sin datos")
    else:
        print_warning("Directorio 'data/' no encontrado")
    
    return True

def show_next_steps(coordinator_url, worker_id, connection_ok):
    """Muestra los siguientes pasos"""
    print_header("PASOS SIGUIENTES")
    
    if connection_ok:
        print_success("¡La conectividad está correcta!")
        print("\nPara iniciar el worker, ejecuta:")
        print(f"{BOLD}  COORDINATOR_URL={coordinator_url}{RESET}")
        print(f"{BOLD}  python3 crypto_worker.py{RESET}")
        print("\nO con múltiples workers:")
        print(f"{BOLD}  for i in 1 2 3; do{RESET}")
        print(f"{BOLD}    COORDINATOR_URL={coordinator_url} WORKER_INSTANCE=$i \\{RESET}")
        print(f"{BOLD}    nohup python3 -u crypto_worker.py > /tmp/worker_$i.log 2>&1 & \\{RESET}")
        print(f"{BOLD}    sleep 2{RESET}")
        print(f"{BOLD}  done{RESET}")
    else:
        print_error("Hay problemas de conectividad")
        print("\nVerificaciones recomendadas:")
        print("1. ¿El coordinator está ejecutándose?")
        print("   En la máquina del coordinator:")
        print("   $ cd <directorio_del_proyecto>")
        print("   $ python3 coordinator_port5001.py")
        print("\n2. ¿Es la URL correcta?")
        print("   - En red local: http://<IP_LOCAL>:5001")
        print("   - Con Tailscale: http://<IP_TAILSCALE>:5001")
        print("\n3. ¿Hay firewall bloqueando?")
        print("   - En macOS: System Settings > Firewall")
        print("   - En Linux: sudo ufw status")
        print("\n4. Verificar en el coordinator:")
        print("   $ curl http://localhost:5001/api/workers")

def main():
    print(f"{BOLD}")
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     🔍 DIAGNÓSTICO DE CONECTIVIDAD DEL WORKER               ║
    ║     Sistema Distribuido de Strategy Mining                  ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    print(f"{RESET}")
    
    # Get coordinator URL from args or env
    coordinator_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv('COORDINATOR_URL', 'http://localhost:5001')
    worker_id = get_worker_id()
    
    print_info(f"Worker ID: {worker_id}")
    print_info(f"Coordinator URL: {coordinator_url}\n")
    
    # Run tests
    conn_ok, final_url = test_coordinator_connection(coordinator_url)
    
    if conn_ok:
        test_worker_registration(final_url, worker_id)
    
    test_worker_env()
    
    show_next_steps(final_url, worker_id, conn_ok)

if __name__ == "__main__":
    main()
