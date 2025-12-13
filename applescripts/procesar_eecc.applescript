(*
	Procesar Estados de Cuenta de Tarjetas de Crédito
	
	Este script es invocado por una regla de Mail.
	Guarda el mensaje como .eml y lo pasa al script Python para procesar.
	
	El script Python se encarga de:
	- Extraer el PDF
	- Quitarle el password
	- Extraer los movimientos
	- Marcar como leído y mover a la carpeta EECC
*)

-- ============================================================================
-- CONFIGURACIÓN
-- ============================================================================

-- Ruta a la instalación de MailProcessors (actualizado por install.sh)
property installPath : "__INSTALL_PATH__"

-- Carpeta temporal para .eml
property emlFolder : "~/Library/MailEML"

-- Archivo de log
property logFile : "~/Library/Logs/MailEECCRule.log"


-- ============================================================================
-- HANDLER PRINCIPAL (invocado por Mail Rule)
-- ============================================================================

using terms from application "Mail"
	on perform mail action with messages theMessages for rule theRule
		
		-- Expandir paths
		set emlFolderPOSIX to do shell script "echo " & emlFolder
		set logFilePOSIX to do shell script "echo " & logFile
		set pythonPath to "__PYTHON_PATH__"
		set scriptPath to installPath & "/scripts/extract_from_email.py"
		
		-- Crear carpeta EML si no existe
		do shell script "mkdir -p " & quoted form of emlFolderPOSIX
		
		-- Timestamp para log
		set ts to do shell script "date '+%Y-%m-%d %H:%M:%S'"
		
		-- Log inicio
		do shell script "echo '[" & ts & "] Regla EECC: " & (count of theMessages) & " mensaje(s)' >> " & quoted form of logFilePOSIX
		
		tell application "Mail"
			set msgCount to count of theMessages
			
			repeat with i from 1 to msgCount
				set this_message to item i of theMessages
				
				try
					-- Obtener propiedades del mensaje
					set msgSubject to subject of this_message
					set msgSender to sender of this_message
					set msgSource to source of this_message
					set msgId to id of this_message
					
					-- Log
					do shell script "echo '  → Procesando: " & msgSubject & "' >> " & quoted form of logFilePOSIX
					
					-- Generar nombre único para el .eml
					set ts2 to do shell script "date '+%Y%m%d_%H%M%S'"
					set emlFileName to "eecc_" & ts2 & "_" & i & ".eml"
					set emlPathPOSIX to emlFolderPOSIX & "/" & emlFileName
					
					-- Guardar como .eml
					set emlPathHFS to POSIX file emlPathPOSIX as text
					set fileRef to open for access file emlPathHFS with write permission
					write msgSource to fileRef
					close access fileRef
					
					-- Construir comando Python con message-id
					set pythonCmd to quoted form of pythonPath & " " & quoted form of scriptPath & " " & quoted form of emlPathPOSIX & " --message-id " & msgId
					
					-- Log del comando
					do shell script "echo '  → Comando: " & pythonCmd & "' >> " & quoted form of logFilePOSIX
					
					-- Ejecutar en background
					do shell script pythonCmd & " >> " & quoted form of logFilePOSIX & " 2>&1 &"
					
					do shell script "echo '  ✓ Script lanzado' >> " & quoted form of logFilePOSIX
					
				on error errMsg number errNum
					do shell script "echo '  ✗ ERROR: " & errMsg & " (" & errNum & ")' >> " & quoted form of logFilePOSIX
				end try
				
			end repeat
		end tell
		
	end perform mail action with messages
end using terms from

