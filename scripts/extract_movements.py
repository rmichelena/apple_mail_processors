#!/usr/bin/env python3
"""
Extractor de movimientos de tarjetas de crédito desde PDFs
usando Google Gemini Flash 2.5 con salida a CSV

Uso:
    python extract_movements.py <archivo.pdf>

Genera:
    - {TipoTarjeta} {Banco} {YYYY-MM} PEN.csv
    - {TipoTarjeta} {Banco} {YYYY-MM} USD.csv (si aplica)
    - {TipoTarjeta} {Banco} {YYYY-MM}.json
    - Renombra el PDF original al mismo formato
"""

import sys
import csv
import json
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Importar configuración
from config import GEMINI_API_KEY, OUTPUT_FOLDER


# ============================================================================
# MODELOS
# ============================================================================

class Movement(BaseModel):
    """Un movimiento individual de tarjeta de crédito"""
    fecha: str = Field(description="Fecha de CONSUMO del movimiento en formato YYYY-MM-DD")
    descripcion: str = Field(description="Descripción exacta del comercio o movimiento")
    monto: float = Field(description="Monto (positivo para cargos, negativo para pagos/abonos)")
    moneda: str = Field(description="PEN o USD")
    tipo: str = Field(
        description="Tipo: consumo, pago, interes, comision, seguro, ajuste, otro"
    )


class StatementMetadata(BaseModel):
    """Metadatos del estado de cuenta"""
    banco: str = Field(description="Nombre del banco emisor (ej: Interbank, Scotiabank, Falabella, BCP)")
    tipo_tarjeta: str = Field(description="Tipo de tarjeta: Visa o Mastercard")
    fecha_cierre: str = Field(description="Fecha de cierre del estado de cuenta en formato YYYY-MM-DD")
    # Balances
    saldo_apertura_pen: Optional[float] = Field(default=None, description="Saldo anterior/apertura en soles (PEN)")
    saldo_cierre_pen: Optional[float] = Field(default=None, description="Saldo actual/cierre en soles (PEN)")
    saldo_apertura_usd: Optional[float] = Field(default=None, description="Saldo anterior/apertura en dólares (USD)")
    saldo_cierre_usd: Optional[float] = Field(default=None, description="Saldo actual/cierre en dólares (USD)")
    # Validación
    es_estado_cuenta: bool = Field(default=True, description="True si es un estado de cuenta real, False si es publicidad u otro documento")


class ExtractedStatement(BaseModel):
    """Estado de cuenta completo con metadatos y movimientos"""
    metadata: StatementMetadata = Field(description="Información del estado de cuenta")
    movimientos: List[Movement] = Field(description="Todos los movimientos del estado de cuenta")


# ============================================================================
# EXTRACCIÓN
# ============================================================================

def extract_statement(pdf_path: str) -> ExtractedStatement:
    """
    Extrae metadatos y movimientos de un PDF de estado de cuenta
    """
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Subir PDF
    print(f"📄 Subiendo: {pdf_path}")
    uploaded_file = client.files.upload(file=pdf_path)
    print(f"✅ Archivo subido: {uploaded_file.name}")
    
    # Prompt mejorado
    prompt = """
Analiza este documento y determina si es un estado de cuenta de tarjeta de crédito.

## PRIMERO: VALIDACIÓN
- **es_estado_cuenta**: Si el documento es un estado de cuenta de tarjeta de crédito, pon true.
  Si es publicidad, promoción, otro tipo de documento, o no puedes identificar movimientos, pon false.

## SI ES UN ESTADO DE CUENTA, EXTRAE:

### METADATOS (metadata)
1. **banco**: Nombre del banco emisor. Ejemplos: Interbank, Scotiabank, BCP, Falabella, BBVA
2. **tipo_tarjeta**: Solo "Visa" o "Mastercard" (identifícalo del logo o texto del documento)
3. **fecha_cierre**: Fecha de cierre/corte del estado de cuenta en formato YYYY-MM-DD

4. **Balances** (busca en el resumen del estado de cuenta):
   - **saldo_apertura_pen**: Saldo anterior/apertura en soles (puede llamarse "Saldo Anterior", "Deuda Anterior", etc.)
   - **saldo_cierre_pen**: Saldo actual/cierre/a pagar en soles (puede llamarse "Total a Pagar", "Pago Total", "Nueva Deuda", etc.)
   - **saldo_apertura_usd**: Saldo anterior/apertura en dólares (si la tarjeta tiene línea en USD)
   - **saldo_cierre_usd**: Saldo actual/cierre/a pagar en dólares (si la tarjeta tiene línea en USD)
   - Si no hay línea en alguna moneda, deja el valor como null

### MOVIMIENTOS (movimientos)
Extrae CADA LÍNEA de movimiento que encuentres:

1. **fecha**: USA SIEMPRE LA FECHA DE CONSUMO/COMPRA, NO la fecha de proceso/registro
   - Si hay dos columnas de fecha (ej: "Fecha Compra" y "Fecha Proceso"), usa la de COMPRA
   - Convierte de DD/MM/YYYY o DD/MM/YY a formato YYYY-MM-DD
   
2. **descripcion**: Tal como aparece en el documento

3. **monto**: 
   - CONSUMOS/CARGOS → valores POSITIVOS
   - PAGOS/ABONOS → valores NEGATIVOS
   
4. **moneda**: PEN (soles) o USD (dólares)

5. **tipo**: consumo, pago, interes, comision, seguro, ajuste, otro

## IMPORTANTE
- NO incluyas saldos ni totales como movimientos
- SOLO movimientos línea por línea
- Los balances van en metadata, NO en movimientos
- Responde ÚNICAMENTE con el JSON estructurado
"""
    
    print("🤖 Procesando con Gemini Flash 2.5...")
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[prompt, uploaded_file],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=ExtractedStatement,
            temperature=0.1,  # Máxima precisión
        ),
    )
    
    print("✅ Respuesta recibida")
    
    # Parsear respuesta
    data = json.loads(response.text)
    statement = ExtractedStatement(**data)
    
    return statement


# ============================================================================
# EXPORTAR CSV POR MONEDA
# ============================================================================

def export_csv_by_currency(movements: List[Movement], output_path: str, moneda: str):
    """Exporta movimientos de una moneda específica a CSV"""
    
    filtered = [m for m in movements if m.moneda == moneda]
    
    if not filtered:
        return False
    
    # Si el archivo es nuevo, escribir BOM UTF-8 para Excel
    file_exists = Path(output_path).exists()
    if not file_exists:
        with open(output_path, 'wb') as f:
            f.write(b'\xef\xbb\xbf')  # UTF-8 BOM
    
    with open(output_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'fecha',
            'descripcion',
            'monto',
            'tipo'
        ])
        
        if not file_exists:
            writer.writeheader()
        
        for mov in filtered:
            writer.writerow({
                'fecha': mov.fecha,
                'descripcion': mov.descripcion,
                'monto': mov.monto,
                'tipo': mov.tipo
            })
    
    print(f"✅ CSV generado: {output_path} ({len(filtered)} movimientos)")
    return True


def generate_base_name(metadata: StatementMetadata) -> str:
    """Genera el nombre base para los archivos: 'Visa Interbank 2025-05'"""
    
    # Extraer año-mes de la fecha de cierre
    try:
        fecha = datetime.strptime(metadata.fecha_cierre, '%Y-%m-%d')
        year_month = fecha.strftime('%Y-%m')
    except ValueError as e:
        print(f"⚠️  Fecha de cierre malformada '{metadata.fecha_cierre}': {e}")
        year_month = metadata.fecha_cierre[:7] if len(metadata.fecha_cierre) >= 7 else "0000-00"
    
    # Limpiar nombres
    tipo = metadata.tipo_tarjeta.strip()
    banco = metadata.banco.strip()
    
    return f"{tipo} {banco} {year_month}"


def print_summary(statement: ExtractedStatement):
    """Imprime resumen rápido"""
    
    meta = statement.metadata
    movs = statement.movimientos
    total_movs = len(movs)
    
    # Separar por moneda
    pen_movs = [m for m in movs if m.moneda == 'PEN']
    usd_movs = [m for m in movs if m.moneda == 'USD']
    
    # Calcular totales (consumos positivos, pagos negativos)
    pen_total = sum(m.monto for m in pen_movs)
    usd_total = sum(m.monto for m in usd_movs)
    
    print("\n" + "="*60)
    print("📊 RESUMEN DE EXTRACCIÓN")
    print("="*60)
    print(f"🏦 Banco: {meta.banco}")
    print(f"💳 Tarjeta: {meta.tipo_tarjeta}")
    print(f"📅 Fecha cierre: {meta.fecha_cierre}")
    print(f"✅ Es estado de cuenta: {meta.es_estado_cuenta}")
    print(f"📝 Total movimientos: {total_movs}")
    
    if pen_movs or meta.saldo_cierre_pen is not None:
        print(f"\n💵 Soles (PEN):")
        if meta.saldo_apertura_pen is not None:
            print(f"   Saldo apertura: S/ {meta.saldo_apertura_pen:.2f}")
        if meta.saldo_cierre_pen is not None:
            print(f"   Saldo cierre:   S/ {meta.saldo_cierre_pen:.2f}")
        if pen_movs:
            print(f"   Movimientos: {len(pen_movs)}")
    
    if usd_movs or meta.saldo_cierre_usd is not None:
        print(f"\n💵 Dólares (USD):")
        if meta.saldo_apertura_usd is not None:
            print(f"   Saldo apertura: $ {meta.saldo_apertura_usd:.2f}")
        if meta.saldo_cierre_usd is not None:
            print(f"   Saldo cierre:   $ {meta.saldo_cierre_usd:.2f}")
        if usd_movs:
            print(f"   Movimientos: {len(usd_movs)}")
    
    print("="*60 + "\n")


# ============================================================================
# MAIN
# ============================================================================

def process_pdf(pdf_path: str, output_dir: Path = None) -> tuple[bool, ExtractedStatement | None]:
    """
    Procesa un PDF de estado de cuenta.
    
    Returns:
        (success, statement) - success es True si se procesó correctamente
    """
    if output_dir is None:
        output_dir = Path(pdf_path).parent
    
    pdf_path = Path(pdf_path)
    
    # Extraer
    statement = extract_statement(str(pdf_path))
    
    # Verificar si es un estado de cuenta real
    if not statement.metadata.es_estado_cuenta:
        print("⚠️ El documento NO es un estado de cuenta de tarjeta de crédito")
        return False, statement
    
    # Resumen
    print_summary(statement)
    
    # Generar nombre base
    base_name = generate_base_name(statement.metadata)
    
    print(f"📁 Nombre base: {base_name}")
    
    # Exportar CSVs separados por moneda
    pen_csv = output_dir / f"{base_name} PEN.csv"
    usd_csv = output_dir / f"{base_name} USD.csv"
    
    pen_exported = export_csv_by_currency(statement.movimientos, str(pen_csv), 'PEN')
    usd_exported = export_csv_by_currency(statement.movimientos, str(usd_csv), 'USD')
    
    if not pen_exported:
        print("ℹ️  Sin movimientos en PEN")
    if not usd_exported:
        print("ℹ️  Sin movimientos en USD")
    
    # Exportar JSON completo
    json_path = output_dir / f"{base_name}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(
            {
                'metadata': statement.metadata.model_dump(),
                'movimientos': [m.model_dump() for m in statement.movimientos]
            },
            f,
            indent=2,
            ensure_ascii=False
        )
    print(f"💾 JSON generado: {json_path}")
    
    # Renombrar PDF original
    new_pdf_name = output_dir / f"{base_name}.pdf"
    if pdf_path != new_pdf_name:
        if new_pdf_name.exists():
            print(f"⚠️  PDF destino ya existe: {new_pdf_name}")
            print(f"    PDF original conservado en: {pdf_path}")
        else:
            shutil.move(str(pdf_path), str(new_pdf_name))
            print(f"📄 PDF renombrado: {new_pdf_name}")
    else:
        print(f"📄 PDF ya tiene el nombre correcto: {pdf_path}")
    
    print("\n✅ ¡Proceso completado!")
    return True, statement


def main():
    if len(sys.argv) != 2:
        print("❌ Uso: python extract_movements.py <archivo.pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"❌ Error: '{pdf_path}' no existe")
        sys.exit(1)
    
    try:
        success, _ = process_pdf(pdf_path)
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

