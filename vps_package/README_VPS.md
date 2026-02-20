# 🚀 Guía de Instalación en VPS (Linux/Ubuntu)

Esta carpeta contiene todo lo necesario para correr el **Coinbase Trading Bot** en tu servidor.

## Pasos la primera vez

1.  **Subir archivos**: Copia toda esta carpeta `vps_package` a tu VPS (usando FileZilla, scp, etc).
2.  **Permisos**: Dale permisos de ejecución al script de inicio:
    ```bash
    chmod +x start.sh
    ```
3.  **Ejecutar**:
    ```bash
    ./start.sh
    ```

## Acceso

- Una vez corriendo, abre tu navegador y ve a: `http://TU_IP_DEL_VPS:8501`.
- Si cierras la terminal, el bot podría detenerse. Para dejarlo corriendo siempre, usa `tmux` o `nohup`.

### Opción "Siempre Activo" (Recomendada)
Para que no se cierre al salir del VPS:

1. Instala tmux: `sudo apt install tmux`
2. Crea nueva sesión: `tmux new -s bot`
3. Corre el script: `./start.sh`
4. Sal de la sesión (sin cerrar): Presiona `Ctrl+B` y luego `D`.

Para volver a ver el bot: `tmux attach -t bot`

## Notas
- **API Key**: El archivo `cdp_api_key.json` ya está incluido. ¡No lo compartas!
- **Modo**: Recuerda seleccionar "Live Trading" o "Paper Trading" desde la web.
