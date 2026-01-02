(*
	EECC Handler - Procesa Estados de Cuenta de Tarjetas de Crédito
	
	Este script es invocado por una regla de Mail.
	Paths configurados por el instalador.
*)

-- Configuración (actualizada por el instalador)
property appPath : "__APP_PATH__"
property pythonPath : "__PYTHON_PATH__"

-- Constantes
property emlFolder : "~/Library/MailEML"
property logFile : "~/Library/Logs/MailProcessors_EECC.log"

using terms from application "Mail"
	on perform mail action with messages theMessages for rule theRule
		
		set emlFolderPOSIX to do shell script "echo " & emlFolder
		set logFilePOSIX to do shell script "echo " & logFile
		set processorPath to appPath & "/Contents/Resources/processors/eecc/processor.py"
		
		do shell script "mkdir -p " & quoted form of emlFolderPOSIX
		
		set ts to do shell script "date '+%Y-%m-%d %H:%M:%S'"
		do shell script "echo '[" & ts & "] EECC: " & (count of theMessages) & " mensaje(s)' >> " & quoted form of logFilePOSIX
		
		tell application "Mail"
			repeat with i from 1 to (count of theMessages)
				set this_message to item i of theMessages
				
				try
					set msgSubject to subject of this_message
					set msgSource to source of this_message
					set msgId to id of this_message
					
					do shell script "echo '  → " & msgSubject & "' >> " & quoted form of logFilePOSIX
					
					set ts2 to do shell script "date '+%Y%m%d_%H%M%S'"
					set emlFileName to "eecc_" & ts2 & "_" & i & ".eml"
					set emlPathPOSIX to emlFolderPOSIX & "/" & emlFileName
					
					set emlPathHFS to POSIX file emlPathPOSIX as text
					set fileRef to open for access file emlPathHFS with write permission
					write msgSource to fileRef
					close access fileRef
					
					set pythonCmd to quoted form of pythonPath & " " & quoted form of processorPath & " " & quoted form of emlPathPOSIX & " --message-id " & quoted form of (msgId as text)
					
					do shell script pythonCmd & " >> " & quoted form of logFilePOSIX & " 2>&1 &"
					
					do shell script "echo '  ✓ Lanzado' >> " & quoted form of logFilePOSIX
					
				on error errMsg number errNum
					do shell script "echo '  ✗ ERROR: " & errMsg & "' >> " & quoted form of logFilePOSIX
				end try
			end repeat
		end tell
		
	end perform mail action with messages
end using terms from

