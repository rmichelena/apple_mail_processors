#!/usr/bin/env python3
"""
Extract From Email - Procesa un .eml de estado de cuenta

Extrae el PDF protegido, le quita la contraseña, y lo procesa con extract_movements.py

Uso:
    python extract_from_email.py <archivo.eml> [--message-id ID]

El --message-id es opcional y se usa para marcar como leído y mover el mensaje
en Mail.app después de un procesamiento exitoso.
"""

import sys
import email
from email import policy
import tempfile
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Importar configuración
from config import (
    OUTPUT_FOLDER, 
    QPDF_PATH, 
    PDF_PASSWORD,
    EECC_FOLDER,
    EECC_ERROR_LOG,
    ensure_folders
)
from mail_actions import mark_read_and_move


def log(msg: str):
    """Log con timestamp"""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] {msg}")


def extract_pdfs_from_eml(eml_path: Path) -> list[tuple[str, bytes]]:
    """
    Extrae todos los PDFs de un archivo .eml
    
    Returns:
        Lista de tuplas (filename, contenido_bytes)
    """
    with open(eml_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    
    pdfs = []
    
    for part in msg.walk():
        content_type = part.get_content_type()
        filename = part.get_filename()
        
        # Buscar PDFs
        if content_type == 'application/pdf' or (filename and filename.lower().endswith('.pdf')):
            payload = part.get_payload(decode=True)
            if payload:
                name = filename or f"attachment_{len(pdfs)}.pdf"
                pdfs.append((name, payload))
                log(f"📎 Encontrado PDF: {name} ({len(payload)} bytes)")
    
    return pdfs


def is_password_protected(pdf_path: Path) -> bool:
    """Verifica si un PDF está protegido con contraseña"""
    result = subprocess.run(
        [QPDF_PATH, '--is-encrypted', str(pdf_path)],
        capture_output=True
    )
    return result.returncode == 0


def remove_password(input_path: Path, output_path: Path) -> bool:
    """Quita la contraseña de un PDF"""
    result = subprocess.run(
        [
            QPDF_PATH,
            '--decrypt',
            f'--password={PDF_PASSWORD}',
            str(input_path),
            str(output_path)
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        log(f"❌ Error qpdf: {result.stderr}")
        return False
    
    return True


def find_and_decrypt_statement(pdfs: list[tuple[str, bytes]], temp_dir: Path) -> Path | None:
    """
    De la lista de PDFs, encuentra el estado de cuenta (el que tiene password)
    y lo descifra.
    
    Returns:
        Path al PDF descifrado, o None si no encuentra
    """
    for filename, content in pdfs:
        # Guardar temporalmente
        temp_pdf = temp_dir / filename
        with open(temp_pdf, 'wb') as f:
            f.write(content)
        
        # ¿Tiene password?
        if is_password_protected(temp_pdf):
            log(f"🔐 PDF protegido encontrado: {filename}")
            
            # Descifrar
            decrypted = temp_dir / f"decrypted_{filename}"
            if remove_password(temp_pdf, decrypted):
                log(f"🔓 PDF descifrado: {decrypted.name}")
                return decrypted
            else:
                log(f"❌ No se pudo descifrar {filename}")
                return None
        else:
            log(f"ℹ️  {filename} no tiene password, ignorando")
    
    return None


def process_eml(eml_path: str, message_id: str = None):
    """
    Procesa un archivo .eml completo:
    1. Extrae PDFs
    2. Encuentra el estado de cuenta (el protegido)
    3. Le quita la contraseña
    4. Lo procesa con extract_movements.py
    5. Si tiene message_id, marca leído y mueve en Mail
    """
    
    ensure_folders()
    eml_path = Path(eml_path)
    
    log(f"📧 Procesando: {eml_path.name}")
    
    # Crear directorio temporal
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Extraer PDFs
        pdfs = extract_pdfs_from_eml(eml_path)
        
        if not pdfs:
            log("❌ No se encontraron PDFs en el correo")
            return False
        
        log(f"📎 {len(pdfs)} PDF(s) encontrado(s)")
        
        # Encontrar y descifrar el estado de cuenta
        decrypted_pdf = find_and_decrypt_statement(pdfs, temp_dir)
        
        if not decrypted_pdf:
            log("❌ No se encontró un estado de cuenta protegido")
            return False
        
        # Copiar a carpeta de salida con nombre temporal
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_pdf = OUTPUT_FOLDER / f"temp_eecc_{ts}.pdf"
        
        import shutil
        shutil.copy(decrypted_pdf, output_pdf)
        log(f"📁 PDF guardado temporalmente: {output_pdf}")
        
        # Procesar con extract_movements.py
        log("🤖 Procesando con Gemini...")
        
        # Importar y ejecutar directamente
        from extract_movements import process_pdf
        
        try:
            success, _ = process_pdf(str(output_pdf), OUTPUT_FOLDER)
            
            if success:
                log("✅ Procesamiento exitoso")
                
                # Marcar y mover en Mail si tenemos message_id
                if message_id:
                    log(f"📬 Moviendo mensaje {message_id} a {EECC_FOLDER}...")
                    if mark_read_and_move(message_id, EECC_FOLDER):
                        log("✅ Mensaje movido exitosamente")
                    else:
                        log("⚠️  No se pudo mover el mensaje (pero el PDF se procesó)")
                
                return True
            else:
                log("❌ El documento no es un estado de cuenta válido")
                # Limpiar PDF temporal si no se procesó
                if output_pdf.exists():
                    output_pdf.unlink()
                return False
                
        except Exception as e:
            log(f"❌ Error en procesamiento: {e}")
            
            # Guardar error
            with open(EECC_ERROR_LOG, 'a') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"[{datetime.now()}] Error procesando {eml_path.name}\n")
                f.write(f"{e}\n")
                import traceback
                f.write(traceback.format_exc())
            
            return False


def main():
    parser = argparse.ArgumentParser(description='Procesa un .eml de estado de cuenta')
    parser.add_argument('eml_file', help='Archivo .eml a procesar')
    parser.add_argument('--message-id', help='ID del mensaje en Mail para mark+move')
    
    args = parser.parse_args()
    
    eml_path = Path(args.eml_file)
    
    if not eml_path.exists():
        log(f"❌ Error: '{eml_path}' no existe")
        sys.exit(1)
    
    try:
        success = process_eml(str(eml_path), args.message_id)
        
        # Eliminar .eml temporal
        try:
            eml_path.unlink()
            log(f"🗑️  EML temporal eliminado")
        except:
            pass
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        log(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

