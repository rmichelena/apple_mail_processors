#!/usr/bin/env python3
"""
Mail Actions - Acciones sobre mensajes de Mail vía osascript

Permite que los scripts Python marquen como leído y muevan mensajes
después de procesarlos exitosamente.
"""

import subprocess
from typing import Optional


def mark_read_and_move(message_id: str, target_folder: str) -> bool:
    """
    Marca un mensaje como leído y lo mueve a una carpeta destino.
    
    Args:
        message_id: ID único del mensaje (obtenido de AppleScript)
        target_folder: Nombre de la carpeta destino (ej: "EECC", "Taxis")
    
    Returns:
        True si tuvo éxito, False si falló
    """
    
    # AppleScript para buscar el mensaje por ID, marcarlo y moverlo
    script = f'''
    tell application "Mail"
        -- Buscar el mensaje por ID en todas las cuentas
        set targetMessage to missing value
        set targetMailbox to missing value
        
        repeat with acct in accounts
            -- Buscar en inbox y subcarpetas
            repeat with mbx in mailboxes of acct
                try
                    set msgs to (messages of mbx whose id is {message_id})
                    if (count of msgs) > 0 then
                        set targetMessage to item 1 of msgs
                        -- Buscar carpeta destino en esta cuenta
                        try
                            set targetMailbox to mailbox "{target_folder}" of acct
                        end try
                        exit repeat
                    end if
                end try
            end repeat
            if targetMessage is not missing value then exit repeat
        end repeat
        
        -- Si no encontramos en mailboxes directos, buscar en inbox
        if targetMessage is missing value then
            repeat with acct in accounts
                try
                    set inb to inbox of acct
                    set msgs to (messages of inb whose id is {message_id})
                    if (count of msgs) > 0 then
                        set targetMessage to item 1 of msgs
                        try
                            set targetMailbox to mailbox "{target_folder}" of acct
                        end try
                        exit repeat
                    end if
                end try
            end repeat
        end if
        
        if targetMessage is missing value then
            error "Mensaje no encontrado"
        end if
        
        if targetMailbox is missing value then
            error "Carpeta destino no encontrada"
        end if
        
        -- Marcar como leído y mover
        set read status of targetMessage to true
        move targetMessage to targetMailbox
        
        return "OK"
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True
        else:
            print(f"❌ Error moviendo mensaje: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout ejecutando osascript")
        return False
    except Exception as e:
        print(f"❌ Error ejecutando osascript: {e}")
        return False


def mark_read_only(message_id: str) -> bool:
    """
    Solo marca un mensaje como leído (sin mover).
    Útil para falsos positivos que queremos marcar pero no mover.
    
    Args:
        message_id: ID único del mensaje
    
    Returns:
        True si tuvo éxito, False si falló
    """
    
    script = f'''
    tell application "Mail"
        repeat with acct in accounts
            repeat with mbx in mailboxes of acct
                try
                    set msgs to (messages of mbx whose id is {message_id})
                    if (count of msgs) > 0 then
                        set read status of item 1 of msgs to true
                        return "OK"
                    end if
                end try
            end repeat
            -- También buscar en inbox
            try
                set msgs to (messages of inbox of acct whose id is {message_id})
                if (count of msgs) > 0 then
                    set read status of item 1 of msgs to true
                    return "OK"
                end if
            end try
        end repeat
        error "Mensaje no encontrado"
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except:
        return False


def flag_message(message_id: str, flag_index: int = 1) -> bool:
    """
    Pone un flag (bandera de color) a un mensaje.
    Útil para marcar mensajes que fallaron en el procesamiento.
    
    Args:
        message_id: ID único del mensaje
        flag_index: Color del flag (0=none, 1=red, 2=orange, 3=yellow, 
                                     4=green, 5=blue, 6=purple, 7=gray)
    
    Returns:
        True si tuvo éxito, False si falló
    """
    
    script = f'''
    tell application "Mail"
        repeat with acct in accounts
            repeat with mbx in mailboxes of acct
                try
                    set msgs to (messages of mbx whose id is {message_id})
                    if (count of msgs) > 0 then
                        set flag index of item 1 of msgs to {flag_index}
                        return "OK"
                    end if
                end try
            end repeat
            -- También buscar en inbox
            try
                set msgs to (messages of inbox of acct whose id is {message_id})
                if (count of msgs) > 0 then
                    set flag index of item 1 of msgs to {flag_index}
                    return "OK"
                end if
            end try
        end repeat
        error "Mensaje no encontrado"
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except:
        return False


if __name__ == '__main__':
    # Test
    import sys
    if len(sys.argv) >= 3:
        msg_id = sys.argv[1]
        folder = sys.argv[2]
        success = mark_read_and_move(msg_id, folder)
        print(f"Resultado: {'OK' if success else 'FALLO'}")
    else:
        print("Uso: python mail_actions.py <message_id> <folder>")

