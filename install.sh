#!/bin/bash
# =============================================================================
# Mail Processors - Script de Instalación
# =============================================================================

set -e

echo "📦 Mail Processors - Instalación"
echo "================================="

# Obtener directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. Crear config.toml si no existe
echo ""
echo "1️⃣  Verificando configuración..."
if [ ! -f config/config.toml ]; then
    mkdir -p config
    cp config.example.toml config/config.toml
    echo "   📝 Creado config/config.toml"
    echo "   ⚠️  ¡IMPORTANTE! Edita config/config.toml con tus valores reales:"
    echo "      - API key de Gemini"
    echo "      - Password del PDF"
    echo "      - Rutas de carpetas"
else
    echo "   ✓ config/config.toml ya existe"
fi

# 2. Crear carpetas necesarias
echo ""
echo "2️⃣  Creando carpetas..."
mkdir -p ~/Library/MailEML
echo "   ✓ ~/Library/MailEML"

# 3. Instalar dependencias Python
echo ""
echo "3️⃣  Instalando dependencias Python..."
pip3 install -r requirements.txt

# 4. Verificar qpdf
echo ""
echo "4️⃣  Verificando qpdf..."
if command -v qpdf &> /dev/null; then
    echo "   ✓ qpdf encontrado: $(which qpdf)"
else
    echo "   ⚠️  qpdf no encontrado. Instalar con:"
    echo "      brew install qpdf"
fi

# 5. Compilar AppleScripts e instalar en Mail
echo ""
echo "5️⃣  Compilando AppleScripts..."

MAIL_SCRIPTS_DIR="$HOME/Library/Application Scripts/com.apple.mail"
mkdir -p "$MAIL_SCRIPTS_DIR"

cd applescripts

if [ -f procesar_eecc.applescript ]; then
    osacompile -o "$MAIL_SCRIPTS_DIR/procesar_eecc.scpt" procesar_eecc.applescript
    echo "   ✓ procesar_eecc.scpt → $MAIL_SCRIPTS_DIR/"
fi

if [ -f procesar_taxi.applescript ]; then
    osacompile -o "$MAIL_SCRIPTS_DIR/procesar_taxi.scpt" procesar_taxi.applescript
    echo "   ✓ procesar_taxi.scpt → $MAIL_SCRIPTS_DIR/"
fi

cd ..

# 6. Instrucciones finales
echo ""
echo "================================="
echo "✅ Instalación completada!"
echo ""
echo "📋 Pasos siguientes:"
echo ""
echo "1. Edita config/config.toml con tus valores reales"
echo ""
echo "2. Configura las reglas en Mail.app:"
echo "   - Mail → Preferencias → Reglas → Agregar regla"
echo "   - Condiciones según remitente del banco/taxi"
echo "   - Acción: 'Run AppleScript' → procesar_eecc.scpt (o procesar_taxi.scpt)"
echo "   - NO marques 'Move Message' ni 'Mark as Read' (lo hace el script)"
echo ""
echo "3. Crea las carpetas EECC y Taxis en Mail.app"
echo ""
echo "📁 Ubicación de archivos:"
echo "   - Scripts Mail: ~/Library/Application Scripts/com.apple.mail/"
echo "   - CSVs/JSONs: $(grep output_folder config/config.toml | cut -d'"' -f2)"
echo "   - Logs: ~/Library/Logs/Mail*.log"
echo ""

