#!/usr/bin/env python3
"""
Extract Taxi Trip - Extrae info de viajes de taxi desde correos

Procesa correos de Uber, Cabify, Beat, etc. y extrae:
- Empresa, fecha, hora, origen, destino, moneda, precio

Los datos se agregan a un CSV consolidado.

Uso:
    python extract_taxi_trip.py <archivo.eml> [--message-id ID]

El --message-id es opcional y se usa para marcar como leído y mover el mensaje
en Mail.app después de un procesamiento exitoso.
"""

import sys
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

# Importar configuración
from config import (
    GEMINI_API_KEY,
    TAXI_CSV,
    TAXI_FOLDER,
    TAXI_ERROR_LOG,
    ensure_folders
)
from mail_actions import mark_read_and_move


# ============================================================================
# MODELOS
# ============================================================================

class TaxiTrip(BaseModel):
    """Información de un viaje de taxi"""
    empresa: str = Field(description="Empresa de taxi: Uber, Cabify, Beat, InDriver, DiDi, etc.")
    fecha: str = Field(description="Fecha del viaje en formato YYYY-MM-DD")
    hora: str = Field(description="Hora del viaje en formato HH:MM (24 horas)")
    origen: str = Field(description="Dirección o lugar de origen del viaje")
    destino: str = Field(description="Dirección o lugar de destino del viaje")
    moneda: str = Field(description="Moneda: PEN o USD")
    precio: float = Field(description="Precio total del viaje")
    es_viaje: bool = Field(default=True, description="True si es un recibo de viaje, False si es publicidad u otro")


def log(msg: str):
    """Log con timestamp"""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] {msg}")


# ============================================================================
# PROCESAMIENTO
# ============================================================================

def html_to_markdown(html_content: str) -> str:
    """Convierte HTML a Markdown limpio"""
    
    # Limpiar con BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Eliminar scripts, styles, etc.
    for tag in soup(['script', 'style', 'meta', 'link', 'head']):
        tag.decompose()
    
    # Convertir a markdown
    markdown = md(str(soup), heading_style="ATX", strip=['img'])
    
    # Limpiar líneas vacías excesivas
    lines = [line.strip() for line in markdown.split('\n')]
    cleaned = '\n'.join(line for line in lines if line)
    
    return cleaned


def extract_trip_info(markdown_content: str) -> TaxiTrip:
    """Usa Gemini para extraer información del viaje"""
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = """
Analiza este correo de un servicio de taxi/transporte (Uber, Cabify, Beat, InDriver, DiDi, etc.)
y extrae la información del viaje.

## PRIMERO: VALIDACIÓN
- **es_viaje**: Si el correo es un recibo/comprobante de viaje realizado, pon true.
  Si es publicidad, promoción, código de descuento, encuesta, o NO contiene info de un viaje específico, pon false.

## SI ES UN RECIBO DE VIAJE, EXTRAE:

1. **empresa**: Uber, Cabify, Beat, InDriver, DiDi, etc.
2. **fecha**: En formato YYYY-MM-DD
3. **hora**: En formato HH:MM (24 horas)
4. **origen**: Dirección o punto de recogida
5. **destino**: Dirección o punto de llegada
6. **moneda**: PEN (soles peruanos) o USD
7. **precio**: Monto total cobrado (número decimal)

## IMPORTANTE
- Si no puedes determinar algún campo, usa valores razonables o "Desconocido"
- El precio debe ser un número (sin símbolos de moneda)
- La moneda en Perú generalmente es PEN (soles)

CONTENIDO DEL CORREO:
"""
    
    log("🤖 Extrayendo información con Gemini...")
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[prompt + "\n\n" + markdown_content],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=TaxiTrip,
            temperature=0.1,
        ),
    )
    
    data = json.loads(response.text)
    trip = TaxiTrip(**data)
    
    return trip


def append_to_csv(trip: TaxiTrip):
    """Agrega el viaje al CSV consolidado"""
    
    csv_path = TAXI_CSV
    file_exists = csv_path.exists()
    
    # Crear archivo con BOM si es nuevo
    if not file_exists:
        with open(csv_path, 'wb') as f:
            f.write(b'\xef\xbb\xbf')  # UTF-8 BOM para Excel
    
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
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
    
    log(f"✅ Viaje agregado a: {csv_path}")


def process_eml(eml_path: str, message_id: str = None) -> bool:
    """
    Procesa un archivo .eml de taxi:
    1. Extrae el HTML del correo
    2. Convierte a Markdown
    3. Extrae info con Gemini
    4. Agrega al CSV
    5. Si tiene message_id, marca leído y mueve en Mail
    """
    
    ensure_folders()
    eml_path = Path(eml_path)
    
    log(f"📧 Procesando: {eml_path.name}")
    
    # Leer correo
    with open(eml_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    
    # Obtener contenido HTML o texto
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
    
    # Preferir HTML, sino texto
    if html_content:
        markdown = html_to_markdown(html_content)
    elif text_content:
        markdown = text_content
    else:
        log("❌ No se encontró contenido en el correo")
        return False
    
    log(f"📝 Contenido extraído: {len(markdown)} caracteres")
    
    # Extraer información
    try:
        trip = extract_trip_info(markdown)
        
        if not trip.es_viaje:
            log("⚠️  El correo NO es un recibo de viaje (publicidad u otro)")
            return False
        
        log(f"🚗 {trip.empresa}: {trip.origen} → {trip.destino}")
        log(f"📅 {trip.fecha} {trip.hora} - {trip.moneda} {trip.precio}")
        
        # Agregar al CSV
        append_to_csv(trip)
        
        # Marcar y mover en Mail si tenemos message_id
        if message_id:
            log(f"📬 Moviendo mensaje {message_id} a {TAXI_FOLDER}...")
            if mark_read_and_move(message_id, TAXI_FOLDER):
                log("✅ Mensaje movido exitosamente")
            else:
                log("⚠️  No se pudo mover el mensaje (pero el viaje se registró)")
        
        return True
        
    except Exception as e:
        log(f"❌ Error extrayendo información: {e}")
        
        # Guardar error
        with open(TAXI_ERROR_LOG, 'a') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"[{datetime.now()}] Error procesando {eml_path.name}\n")
            f.write(f"{e}\n")
            import traceback
            f.write(traceback.format_exc())
        
        return False


def main():
    parser = argparse.ArgumentParser(description='Procesa un .eml de viaje de taxi')
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

