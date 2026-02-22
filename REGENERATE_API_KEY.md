# 🔐 GUIA PARA REGENERAR API KEY DE COINBASE

## Pasos para Regenerar tu API Key

### 1. Ve al Portal de Coinbase

Abre en tu navegador:
```
https://portal.coinbase.com/portal/api-keys
```

### 2. Inicia Sesión

Inicia sesión con tu cuenta de Coinbase.

### 3. Busca tu API Key

Busca la key con ID:
```
f2b19384-cbfd-4e6b-ab21-38a29f53650b
```

### 4. Verifica los Permisos

Asegúrate que tenga estos permisos ACTIVOS:
```
[✓] view
[✓] trade  
[✓] wallet
[✓] data
```

### 5. Si no funciona, CREA UNA NUEVA API Key

Haz clic en **"+ Create API Key** o **"+ New API Key**

### 6. Configura la Nueva API Key

```
Name: Trading Bot
Permissions:
  [✓] read
  [✓] trade
  [✓] transfers
Access: Programmatic Access
```

### 7. Descarga la Private Key

**MUY IMPORTANTE:**
- Descarga el archivo JSON
- Guárdalo en un lugar seguro
- **NO LO PIERDAS** - solo se puede descargar una vez

### 8. Copia la Nueva Key al Proyecto

El archivo descargado tendrá este formato:
```json
{
   "id": "nuevo-id-aqui",
   "privateKey": "base64-encoded-key-aqui"
}
```

### 9. Actualiza el archivo

Reemplaza el contenido de:
```
/Users/enderj/Downloads/cdp_api_key.json
```

con el nuevo archivo descargado.

---

## Alternativa: Crear API Key desde la Terminal

Si tienes `coinbase` CLI instalado:
```bash
coinbase api-keys create --name "Trading Bot"
```

---

## Después de Regenerar

1. Descarga el nuevo archivo JSON
2. Copialo a: `/Users/enderj/Downloads/cdp_api_key.json`
3. Ejecuta:
```bash
python3 test_auth_methods.py
```

---

## Preguntas Frecuentes

**P: ¿Puedo usar la misma key varias veces?**
R: Sí, pero la Private Key solo se descarga una vez.

**P: ¿La key tiene vencimiento?**
R: No, pero puede ser revocada manualmente.

**P: ¿Cuántas keys puedo crear?**
R: Depende de tu cuenta.

---

## Soporte

- Documentacion: https://docs.coinbase.com/advanced-trade
- Soporte: https://help.coinbase.com
