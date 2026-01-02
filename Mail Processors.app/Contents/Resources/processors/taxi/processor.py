#!/usr/bin/env python3
"""
Taxi Processor - Extrae información de viajes de taxi

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
import argparse
from pathlib import Path
from datetime import datetime

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import httpx
import httpcore
import logging

from config import (
    GEMINI_API_KEY, OUTPUT_FOLDER, TAXI_FOLDER,
    TAXI_CSV, TAXI_ERROR_LOG, ensure_folders
)
from mail_actions import mark_read_and_move, flag_message

# Logger para reintentos
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Decorador de reintento para errores de red transitorios
network_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type((
        httpx.ReadError,
        httpx.ConnectError,
        httpx.TimeoutException,
        httpcore.ReadError,
        httpcore.ConnectError,
        ConnectionResetError,
        ConnectionError,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


# ============================================================================
# MODELOS
# ============================================================================

class TaxiTrip(BaseModel):
    """Información de un viaje de taxi"""
    empresa: str = Field(description="Uber, Cabify, Beat, InDriver, DiDi, etc.")
    fecha: str = Field(description="Fecha en formato YYYY-MM-DD")
    hora: str = Field(description="Hora en formato HH:MM")
    origen: str = Field(description="Dirección de origen")
    destino: str = Field(description="Dirección de destino")
    moneda: str = Field(description="PEN o USD")
    precio: float = Field(description="Precio total")
    es_viaje: bool = Field(default=True, description="False si es publicidad")


# ============================================================================
# FUNCIONES
# ============================================================================

def log(msg: str):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] {msg}")


def html_to_markdown(html_content: str) -> str:
    """Convierte HTML a Markdown limpio"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for tag in soup(['script', 'style', 'meta', 'link', 'head']):
        tag.decompose()
    
    markdown = md(str(soup), heading_style="ATX", strip=['img'])
    lines = [line.strip() for line in markdown.split('\n')]
    return '\n'.join(line for line in lines if line)


@network_retry
def extract_trip_info(markdown_content: str) -> TaxiTrip:
    """Usa Gemini para extraer información del viaje (con reintentos automáticos)"""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = """
Analiza este correo de taxi (Uber, Cabify, Beat, InDriver, DiDi).

## VALIDACIÓN
- es_viaje: true si es recibo de viaje realizado, false si es publicidad/promoción

## SI ES RECIBO, EXTRAE:
- empresa: Uber, Cabify, Beat, InDriver, DiDi
- fecha: YYYY-MM-DD
- hora: HH:MM (24h)
- origen: Dirección de recogida
- destino: Dirección de llegada
- moneda: PEN o USD
- precio: Monto total

CONTENIDO:
"""
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[prompt + "\n\n" + markdown_content],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=TaxiTrip,
            temperature=0.1,
        ),
    )
    
    return TaxiTrip(**json.loads(response.text))


def append_to_csv(trip: TaxiTrip):
    """Agrega el viaje al CSV consolidado"""
    file_exists = TAXI_CSV.exists()
    
    if not file_exists:
        with open(TAXI_CSV, 'wb') as f:
            f.write(b'\xef\xbb\xbf')  # BOM para Excel
    
    with open(TAXI_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'fecha', 'hora', 'empresa', 'origen', 'destino', 'moneda', 'precio'
        ])
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            'fecha': trip.fecha,
            'hora': trip.hora,
            'empresa': trip.empresa,
            'origen': trip.origen,
            'destino': trip.destino,
            'moneda': trip.moneda,
            'precio': trip.precio
        })


def process_eml(eml_path: str, message_id: str = None) -> bool:
    """Procesa un .eml de viaje de taxi"""
    ensure_folders()
    eml_path = Path(eml_path)
    
    log(f"📧 Procesando: {eml_path.name}")
    
    try:
        # Leer correo
        with open(eml_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
        
        # Obtener contenido
        html_content = None
        text_content = None
        
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/html':
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                html_content = payload.decode(charset, errors='replace')
            elif content_type == 'text/plain' and not html_content:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                text_content = payload.decode(charset, errors='replace')
        
        if html_content:
            markdown = html_to_markdown(html_content)
        elif text_content:
            markdown = text_content
        else:
            log("❌ No se encontró contenido")
            # Flag naranja - no pudimos leer el contenido
            if message_id:
                log("🟠 Marcando con flag naranja (sin contenido)...")
                flag_message(message_id, flag_index=2)
            return False
        
        # Extraer información (con reintentos automáticos)
        log("🤖 Extrayendo con Gemini...")
        trip = extract_trip_info(markdown)
        
        if not trip.es_viaje:
            log("⚠️ No es un recibo de viaje")
            # Flag naranja - no es lo que esperábamos (queda unread)
            if message_id:
                log("🟠 Marcando con flag naranja (no es viaje)...")
                flag_message(message_id, flag_index=2)
            return False
        
        log(f"🚗 {trip.empresa}: {trip.origen} → {trip.destino}")
        log(f"📅 {trip.fecha} {trip.hora} - {trip.moneda} {trip.precio}")
        
        # Agregar al CSV
        append_to_csv(trip)
        log(f"✅ Agregado a {TAXI_CSV}")
        
        # Solo mover y marcar read si procesamos OK
        if message_id:
            if mark_read_and_move(message_id, TAXI_FOLDER):
                log("📬 Mensaje movido")
        
        return True
        
    except Exception as e:
        log(f"❌ Error en procesamiento: {e}")
        
        # Guardar error en log
        with open(TAXI_ERROR_LOG, 'a') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"[{datetime.now()}] Error procesando {eml_path.name}\n")
            f.write(f"{e}\n")
            import traceback
            f.write(traceback.format_exc())
        
        # Flag rojo - error de procesamiento (queda unread)
        if message_id:
            log("🚩 Marcando con flag rojo (error)...")
            flag_message(message_id, flag_index=1)
        
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('eml_file')
    parser.add_argument('--message-id')
    args = parser.parse_args()
    
    success = process_eml(args.eml_file, args.message_id)
    
    # Eliminar .eml temporal
    try:
        Path(args.eml_file).unlink()
        log("🗑️  EML temporal eliminado")
    except:
        pass
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

