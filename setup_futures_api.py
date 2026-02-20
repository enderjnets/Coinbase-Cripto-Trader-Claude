#!/usr/bin/env python3
"""
🔐 Coinbase Futures Configuration Script v1.0
Detecta y configura las credenciales de Coinbase para futuros

Uso: python3 setup_futures_api.py
"""

import os
import sys

def check_existing_config():
    """Verifica si ya hay configuración de Coinbase"""
    
    print("="*60)
    print("🔍 VERIFICANDO CONFIGURACIÓN EXISTENTE")
    print("="*60)
    print()
    
    # Verificar .env
    env_file = ".env"
    
    config = {}
    
    if os.path.exists(env_file):
        print(f"✅ Archivo .env encontrado: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    config[key.strip()] = value.strip()
    else:
        print(f"⚠️  Archivo .env no encontrado")
    
    # Verificar variables de entorno
    env_keys = [
        'COINBASE_API_KEY',
        'COINBASE_PRIVATE_KEY',
        'COINBASE_SANDBOX'
    ]
    
    print()
    print("📋 Variables de entorno:")
    print("-"*40)
    
    for key in env_keys:
        value = os.getenv(key)
        if value:
            if 'KEY' in key or 'SECRET' in key:
                # Mostrar solo primeros y últimos caracteres
                display = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
                print(f"  ✅ {key}: {display}")
            else:
                print(f"  ✅ {key}: {value}")
        else:
            print(f"  ❌ {key}: No configurada")
            config[key] = None
    
    return config

def check_spot_api_keys():
    """Verifica si hay API keys de spot configuradas"""
    
    print()
    print("📊 Verificando API Keys de Spot:")
    print("-"*40)
    
    # Revisar archivo config.py o similar
    config_files = ['config.py', 'config.py', '../config.py']
    
    api_key = None
    api_secret = None
    
    for cf in config_files:
        if os.path.exists(cf):
            try:
                with open(cf, 'r') as f:
                    content = f.read()
                    if 'COINBASE_API_KEY' in content or 'api_key' in content.lower():
                        print(f"  ⚠️  Posibles keys en {cf}")
            except:
                pass
    
    # Intentar obtener del SDK
    try:
        from config import Config
        keys = Config.get_api_keys()
        if keys:
            print(f"  ✅ Keys encontradas via Config.get_api_keys()")
            api_key, api_secret = keys
    except ImportError:
        print(f"  ℹ️  No se encontró Config.get_api_keys()")
    
    return api_key, api_secret

def generate_private_key_template():
    """Genera template para la Private Key"""
    
    template = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7...REMPLAZA_ESTO_CON_TU_PRIVATE_KEY_COMPLETA...xZ
-----END PRIVATE KEY-----"""
    
    return template

def main():
    """Función principal de configuración"""
    
    print()
    print("="*60)
    print("🔐 CONFIGURACIÓN DE API DE FUTUROS DE COINBASE")
    print("="*60)
    print()
    print("Este script ayuda a configurar las credenciales para")
    print("acceder a la API de Futuros de Coinbase Advanced Trade.")
    print()
    
    # Verificar config existente
    config = check_existing_config()
    
    # Verificar API keys de spot
    spot_api_key, spot_secret = check_spot_api_keys()
    
    # Si tenemos API key de spot, usarla como referencia
    print()
    print("📝 INFORMACIÓN RELEVANTE:")
    print("-"*40)
    
    if spot_api_key:
        print(f"  ℹ️  API Key de Spot encontrada: {spot_api_key[:8]}...")
        print("  ⚠️  NOTA: Para futuros necesitas una Private Key en")
        print("      formato PEM (diferente al API Secret de spot)")
        print()
    
    # API Key Name proporcionada por el usuario
    print("  📌 Tu API Key Name: 069e2e6b-537d-463d-a42f-470e36eb94ed")
    print()
    
    # Instrucciones
    print("📋 PASOS PARA CONFIGURAR:")
    print("-"*40)
    print("""
  1. Ve a https://portal.coinbase.com/portal/api-keys
  2. Selecciona la clave: "069e2e6b-537d-463d-a42f-470eeb94ed"
  3. Haz clic en "Show Private Key" o "Reveal"
  4. Copia la clave privada COMPLETA (incluye -----BEGIN/END PRIVATE KEY-----)
  5. Edita el archivo .env y reemplaza:
     COINBASE_PRIVATE_KEY=tu_private_key_aqui
     con tu clave real (manten los \\n si los hay)
  6. Opcional: Configura COINBASE_SANDBOX=true para pruebas

EJEMPLO de .env:
  COINBASE_API_KEY=069e2e6b-537d-463d-a42f-470e36eb94ed
  COINBASE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\\nMIIE...\\n-----END PRIVATE KEY-----
  COINBASE_SANDBOX=false
""")
    
    # Verificar estado final
    print()
    print("="*60)
    print("📊 ESTADO DE CONFIGURACIÓN:")
    print("="*60)
    
    api_key = os.getenv('COINBASE_API_KEY') or config.get('COINBASE_API_KEY')
    private_key = os.getenv('COINBASE_PRIVATE_KEY') or config.get('COINBASE_PRIVATE_KEY')
    
    if api_key and api_key != 'tu_key_aqui':
        print("  ✅ COINBASE_API_KEY configurada")
    else:
        print("  ❌ COINBASE_API_KEY no configurada")
    
    if private_key and private_key != 'tu_private_key_aqui' and 'BEGIN' in private_key:
        print("  ✅ COINBASE_PRIVATE_KEY configurada")
        print("  🚀 ¡Listo para usar la API de Futuros!")
    elif private_key == 'tu_private_key_aqui' or not private_key:
        print("  ⚠️  COINBASE_PRIVATE_KEY requiere configuración")
        print("  📌 Sigue los pasos arriba para completar la configuración")
    
    print()
    return 0 if (api_key and api_key != 'tu_key_aqui' and 
                  private_key and private_key != 'tu_private_key_aqui' and
                  'BEGIN' in private_key) else 1

if __name__ == "__main__":
    sys.exit(main())
