#!/usr/bin/env python3
"""
EECC Processor - Extrae movimientos de estados de cuenta de tarjetas de crédito

Uso:
    python processor.py <archivo.eml> [--message-id ID]
"""

import sys
import os

# Agregar lib al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))

import csv
import json
import email
from email import policy
import shutil
import tempfile
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from config import (
    GEMINI_API_KEY, OUTPUT_FOLDER, QPDF_PATH, PDF_PASSWORD,
    EECC_FOLDER, EECC_ERROR_LOG, ensure_folders
)
from mail_actions import mark_read_and_move


# ============================================================================
# MODELOS
# ============================================================================

class Movement(BaseModel):
    """Un movimiento individual de tarjeta de crédito"""
    fecha: str = Field(description="Fecha de CONSUMO del movimiento en formato YYYY-MM-DD")
    descripcion: str = Field(description="Descripción exacta del comercio o movimiento")
    monto: float = Field(description="Monto (positivo para cargos, negativo para pagos/abonos)")
    moneda: str = Field(description="PEN o USD")
    tipo: str = Field(description="Tipo: consumo, pago, interes, comision, seguro, ajuste, otro")


class StatementMetadata(BaseModel):
    """Metadatos del estado de cuenta"""
    banco: str = Field(description="Nombre del banco emisor")
    tipo_tarjeta: str = Field(description="Tipo de tarjeta: Visa o Mastercard")
    fecha_cierre: str = Field(description="Fecha de cierre en formato YYYY-MM-DD")
    saldo_apertura_pen: Optional[float] = Field(default=None)
    saldo_cierre_pen: Optional[float] = Field(default=None)
    saldo_apertura_usd: Optional[float] = Field(default=None)
    saldo_cierre_usd: Optional[float] = Field(default=None)
    es_estado_cuenta: bool = Field(default=True, description="False si es publicidad")


class ExtractedStatement(BaseModel):
    """Estado de cuenta completo"""
    metadata: StatementMetadata
    movimientos: List[Movement]


# ============================================================================
# FUNCIONES
# ============================================================================

def log(msg: str):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] {msg}")


def extract_pdfs_from_eml(eml_path: Path) -> list[tuple[str, bytes]]:
    """Extrae todos los PDFs de un .eml"""
    with open(eml_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    
    pdfs = []
    for part in msg.walk():
        content_type = part.get_content_type()
        filename = part.get_filename()
        
        if content_type == 'application/pdf' or (filename and filename.lower().endswith('.pdf')):
            payload = part.get_payload(decode=True)
            if payload:
                name = filename or f"attachment_{len(pdfs)}.pdf"
                pdfs.append((name, payload))
    
    return pdfs


def is_password_protected(pdf_path: Path) -> bool:
    result = subprocess.run([QPDF_PATH, '--is-encrypted', str(pdf_path)], capture_output=True)
    return result.returncode == 0


def remove_password(input_path: Path, output_path: Path) -> bool:
    result = subprocess.run(
        [QPDF_PATH, '--decrypt', f'--password={PDF_PASSWORD}', str(input_path), str(output_path)],
        capture_output=True, text=True
    )
    return result.returncode == 0


def extract_statement(pdf_path: str) -> ExtractedStatement:
    """Extrae movimientos del PDF usando Gemini"""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    uploaded_file = client.files.upload(file=pdf_path)
    
    prompt = """
Analiza este documento y determina si es un estado de cuenta de tarjeta de crédito.

## VALIDACIÓN
- es_estado_cuenta: true si es estado de cuenta real, false si es publicidad

## SI ES ESTADO DE CUENTA, EXTRAE:

### METADATA
- banco: Nombre del banco (Interbank, Scotiabank, BCP, Falabella, BBVA)
- tipo_tarjeta: Solo "Visa" o "Mastercard"
- fecha_cierre: Fecha de cierre en YYYY-MM-DD
- saldo_apertura_pen, saldo_cierre_pen: Balances en soles
- saldo_apertura_usd, saldo_cierre_usd: Balances en dólares

### MOVIMIENTOS
- fecha: FECHA DE CONSUMO (no de proceso) en YYYY-MM-DD
- descripcion: Tal como aparece
- monto: Positivo para cargos, negativo para pagos
- moneda: PEN o USD
- tipo: consumo, pago, interes, comision, seguro, ajuste, otro
"""
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[prompt, uploaded_file],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=ExtractedStatement,
            temperature=0.1,
        ),
    )
    
    return ExtractedStatement(**json.loads(response.text))


def generate_base_name(metadata: StatementMetadata) -> str:
    try:
        fecha = datetime.strptime(metadata.fecha_cierre, '%Y-%m-%d')
        year_month = fecha.strftime('%Y-%m')
    except ValueError as e:
        log(f"⚠️ Fecha malformada '{metadata.fecha_cierre}': {e}")
        year_month = metadata.fecha_cierre[:7] if len(metadata.fecha_cierre) >= 7 else "0000-00"
    
    return f"{metadata.tipo_tarjeta} {metadata.banco} {year_month}"


def export_csv(movements: List[Movement], output_path: str, moneda: str):
    filtered = [m for m in movements if m.moneda == moneda]
    if not filtered:
        return False
    
    file_exists = Path(output_path).exists()
    if not file_exists:
        with open(output_path, 'wb') as f:
            f.write(b'\xef\xbb\xbf')
    
    with open(output_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['fecha', 'descripcion', 'monto', 'tipo'])
        if not file_exists:
            writer.writeheader()
        for mov in filtered:
            writer.writerow({'fecha': mov.fecha, 'descripcion': mov.descripcion, 
                           'monto': mov.monto, 'tipo': mov.tipo})
    return True


def process_eml(eml_path: str, message_id: str = None) -> bool:
    """Procesa un .eml de estado de cuenta"""
    ensure_folders()
    eml_path = Path(eml_path)
    
    log(f"📧 Procesando: {eml_path.name}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Extraer PDFs
        pdfs = extract_pdfs_from_eml(eml_path)
        if not pdfs:
            log("❌ No se encontraron PDFs")
            return False
        
        # Buscar PDF con password
        decrypted_pdf = None
        for filename, content in pdfs:
            temp_pdf = temp_dir / filename
            with open(temp_pdf, 'wb') as f:
                f.write(content)
            
            if is_password_protected(temp_pdf):
                decrypted = temp_dir / f"decrypted_{filename}"
                if remove_password(temp_pdf, decrypted):
                    decrypted_pdf = decrypted
                    break
        
        if not decrypted_pdf:
            log("❌ No se encontró PDF protegido")
            return False
        
        # Procesar con Gemini
        log("🤖 Extrayendo con Gemini...")
        statement = extract_statement(str(decrypted_pdf))
        
        if not statement.metadata.es_estado_cuenta:
            log("⚠️ No es un estado de cuenta válido")
            return False
        
        # Generar archivos
        base_name = generate_base_name(statement.metadata)
        log(f"📁 {base_name}")
        
        # CSVs
        if not export_csv(statement.movimientos, str(OUTPUT_FOLDER / f"{base_name} PEN.csv"), 'PEN'):
            log("ℹ️ Sin movimientos en PEN")
        if not export_csv(statement.movimientos, str(OUTPUT_FOLDER / f"{base_name} USD.csv"), 'USD'):
            log("ℹ️ Sin movimientos en USD")
        
        # JSON
        with open(OUTPUT_FOLDER / f"{base_name}.json", 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': statement.metadata.model_dump(),
                'movimientos': [m.model_dump() for m in statement.movimientos]
            }, f, indent=2, ensure_ascii=False)
        
        # Copiar PDF
        shutil.copy(decrypted_pdf, OUTPUT_FOLDER / f"{base_name}.pdf")
        
        log("✅ Procesado exitosamente")
        
        # Mover mensaje en Mail
        if message_id:
            if mark_read_and_move(message_id, EECC_FOLDER):
                log("📬 Mensaje movido")
        
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('eml_file')
    parser.add_argument('--message-id')
    args = parser.parse_args()
    
    try:
        success = process_eml(args.eml_file, args.message_id)
        
        # Eliminar .eml temporal
        try:
            Path(args.eml_file).unlink()
        except:
            pass
        
        sys.exit(0 if success else 1)
    except Exception as e:
        log(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

