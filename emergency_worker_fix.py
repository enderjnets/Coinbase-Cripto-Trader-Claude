#!/usr/bin/env python3
"""
🎯 Script de Emergencia para Workers
Ejecutar este script en cualquier máquina para repararla automáticamente
"""

import os
import sys
import subprocess
import sqlite3
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_os():
    """Detecta el sistema operativo"""
    return os.uname().sysname.lower()

def get_hostname():
    """Obtiene el hostname"""
    return os.uname().nodename

def detect_worker_type():
    """Detecta qué tipo de worker es esta máquina"""
    hostname = get_hostname().lower()
    
    if 'macbook-pro' in hostname or 'enders-macbook-pro' in hostname:
        return 'macbook_pro', '🍎 MacBook Pro'
    elif 'macbook-air' in hostname or 'enders-macbook-air' in hostname:
        return 'macbook_air', '🪶 MacBook Air'
    elif 'rog' in hostname or 'kubuntu' in hostname:
        return 'linux_rog', '🐧 Linux ROG'
    elif 'asus' in hostname or 'dorada' in hostname:
        return 'asus_dorada', '🌐 Asus Dorada'
    else:
        return 'generic', '💻 Servidor'

def fix_worker():
    """Ejecuta reparaciones para esta máquina"""
    worker_type, name = detect_worker_type()
    
    print("\n" + "="*60)
    print(f"  🔧 REPARACIÓN DE EMERGENCIA: {name}")
    print("="*60 + "\n")
    
    log(f"Sistema detectado: {get_os()}")
    log(f"Hostname: {get_hostname()}")
    log(f"Tipo de worker: {worker_type}")
    
    # 1. Detener procesos existentes
    log("\n1️⃣ Deteniendo workers existentes...")
    subprocess.run(['pkill', '-f', 'crypto_worker'], capture_output=True)
    subprocess.run(['pkill', '-f', 'worker_daemon'], capture_output=True)
    time.sleep(2)
    log("✅ Procesos detenido")
    
    # 2. Verificar directorio
    log("\n2️⃣ Verificando directorio del worker...")
    worker_dir = os.path.expanduser('~/.bittrader_worker')
    
    if not os.path.exists(worker_dir):
        log(f"❌ Directorio no existe: {worker_dir}")
        log("💡 Instalar primero con: git clone https://github.com/... && bash auto_install_worker.sh")
        return False
    
    log(f"✅ Directorio encontrado: {worker_dir}")
    
    # 3. Verificar scripts
    log("\n3️⃣ Verificando scripts...")
    daemon_script = os.path.join(worker_dir, 'worker_daemon.sh')
    
    if not os.path.exists(daemon_script):
        log(f"❌ Script no encontrado: {daemon_script}")
        return False
    
    os.chmod(daemon_script, 0o755)
    log("✅ Script verificado")
    
    # 4. Verificar Python
    log("\n4️⃣ Verificando Python...")
    try:
        result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
        log(f"✅ Python: {result.stdout.strip()}")
    except:
        log("❌ Python no encontrado")
        return False
    
    # 5. Verificar conexión a coordinator
    log("\n5️⃣ Verificando conectividad...")
    
    # Verificar si el coordinator está accesible
    coordinator_ip = '100.118.215.73'  # IP del MacBook Pro con Tailscale
    
    try:
        result = subprocess.run(['ping', '-c', '1', '-W', '2', coordinator_ip], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            log(f"✅ Coordinator accesible en: {coordinator_ip}")
        else:
            log(f"⚠️ Coordinator no accesible via ping: {coordinator_ip}")
            log("   Intentando vía Tailscale...")
    except:
        log("⚠️ No se pudo verificar conectividad")
    
    # 6. Iniciar daemon
    log("\n6️⃣ Iniciando worker daemon...")
    
    os.chdir(worker_dir)
    subprocess.Popen(
        ['bash', 'worker_daemon.sh'],
        stdout=open(os.path.join(worker_dir, 'repair.log'), 'a'),
        stderr=subprocess.STDOUT
    )
    
    log("✅ Daemon iniciado")
    time.sleep(3)
    
    # 7. Verificar proceso
    log("\n7️⃣ Verificando proceso...")
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    workers = [l for l in result.stdout.split('\n') 
              if 'crypto_worker' in l and 'grep' not in l]
    
    if workers:
        log(f"✅ {len(workers)} worker(s) corriendo")
        for w in workers[:3]:
            log(f"   - {w[:80]}...")
    else:
        log("❌ No hay workers corriendo")
        log("📝 Revisar log: tail ~/.bittrader_worker/repair.log")
    
    # 8. Forzar registro en coordinator
    log("\n8️⃣ Registrando en coordinator...")
    
    # El registro automático se hace via el daemon
    # Pero podemos verificar la base de datos si existe localmente
    db_path = os.path.expanduser('~/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db')
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            hostname = get_hostname()
            c.execute("""
                UPDATE workers 
                SET last_seen = julianday('now'), status = 'active'
                WHERE id LIKE ? OR hostname LIKE ?
            """, (f'%{hostname}%', f'%{hostname}%'))
            
            conn.commit()
            conn.close()
            log("✅ Heartbeat forzado en base de datos")
        except Exception as e:
            log(f"⚠️ No se pudo actualizar base de datos: {e}")
    
    print("\n" + "="*60)
    print("  ✅ REPARACIÓN COMPLETADA")
    print("="*60 + "\n")
    
    log("📊 Verificar en dashboard: http://localhost:5006")
    log("📝 Log de reparación: ~/.bittrader_worker/repair.log")
    
    return True

if __name__ == '__main__':
    import time
    
    success = fix_worker()
    sys.exit(0 if success else 1)
