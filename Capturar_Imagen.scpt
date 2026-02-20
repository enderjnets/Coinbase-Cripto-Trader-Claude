(**
 * 📋 Capturar imagen del portapapeles
 * 
 * Instrucciones:
 * 1. Copia una imagen (Cmd+C)
 * 2. Ejecuta este script (doble click)
 * 3. La imagen se guarda en el escritorio
 *)

tell application "System Events"
    try
        -- Verificar si hay imagen
        set the clipboard to the clipboard as «class PNGf»
        
        -- Obtener la fecha actual
        set now to do shell script "date +'%Y%m%d_%H%M%S'"
        set filename to "clipboard_" & now & ".png"
        set filepath to (path to desktop as text) & filename
        
        -- Guardar usando AppleScript nativo
        set imgData to the clipboard as «class PNGf»
        
        -- Escribir el archivo
        set fp to open for access file filepath with write permission
        write imgData to fp
        close access fp
        
        -- Mostrar notificación
        display notification "Imagen guardada: " & filename with title "Clipboard Image"
        
        return "✅ Guardado: " & filepath
        
    on error errMsg
        -- Si no hay imagen, ofrecer opción de capturar pantalla
        display dialog "No hay imagen en el portapapeles." & return & return & "¿Quieres capturar la pantalla?" buttons {"Cancelar", "Capturar Pantalla Completa", "Capturar Selección"} default button "Capturar Selección"
        
        set choice to button returned of result
        
        if choice is "Capturar Pantalla Completa" then
            do shell script "screencapture -x " & quoted form of ((path to desktop as text) & "screenshot_" & (do shell script "date +'%Y%m%d_%H%M%S'") & ".png")
            display notification "Captura de pantalla completada" with title "Screenshot"
            
        else if choice is "Capturar Selección" then
            do shell script "screencapture -is " & quoted form of ((path to desktop as text) & "screenshot_" & (do shell script "date +'%Y%m%d_%H%M%S'") & ".png")
            display notification "Captura de selección completada" with title "Screenshot"
            
        end if
        
        return "✅ Listo"
        
    end try
end tell
