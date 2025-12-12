#!/bin/bash
# =============================================================================
# Apple Mail Processors - Script de Instalación
# =============================================================================

set -e

echo "📦 Apple Mail Processors - Instalación"
echo "======================================="

# Obtener directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# =============================================================================
# 1. Detectar Python
# =============================================================================
echo ""
echo "1️⃣  Detectando Python..."

# Buscar python3 en orden de preferencia
if command -v python3 &> /dev/null; then
    PYTHON_PATH=$(which python3)
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo "   ✓ Encontrado: $PYTHON_PATH ($PYTHON_VERSION)"
else
    echo "   ❌ Python 3 no encontrado"
    echo "   Instala Python desde https://www.python.org/downloads/"
    exit 1
fi

# =============================================================================
# 2. Verificar/Instalar qpdf
# =============================================================================
echo ""
echo "2️⃣  Verificando qpdf..."

if command -v qpdf &> /dev/null; then
    QPDF_PATH=$(which qpdf)
    echo "   ✓ Encontrado: $QPDF_PATH"
else
    echo "   ⚠️  qpdf no encontrado"
    QPDF_INSTALLED=false
    
    # Intentar instalar con Homebrew si está disponible
    if command -v brew &> /dev/null; then
        echo "   📥 Instalando qpdf via Homebrew..."
        if brew install qpdf; then
            QPDF_PATH=$(which qpdf)
            echo "   ✓ Instalado: $QPDF_PATH"
            QPDF_INSTALLED=true
        fi
    fi
    
    # Intentar con MacPorts si Homebrew no funcionó
    if [ "$QPDF_INSTALLED" = false ] && command -v port &> /dev/null; then
        echo "   📥 Instalando qpdf via MacPorts..."
        if sudo port install qpdf; then
            QPDF_PATH=$(which qpdf)
            echo "   ✓ Instalado: $QPDF_PATH"
            QPDF_INSTALLED=true
        fi
    fi
    
    # Si no se pudo instalar automáticamente
    if [ "$QPDF_INSTALLED" = false ]; then
        echo ""
        echo "   ❌ No se pudo instalar qpdf automáticamente"
        echo ""
        echo "   Opciones para instalar manualmente:"
        echo "   ┌─────────────────────────────────────────────────────────────┐"
        echo "   │ Opción 1 - Homebrew (recomendado):                          │"
        echo "   │   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\" │"
        echo "   │   brew install qpdf                                         │"
        echo "   ├─────────────────────────────────────────────────────────────┤"
        echo "   │ Opción 2 - MacPorts:                                        │"
        echo "   │   sudo port install qpdf                                    │"
        echo "   ├─────────────────────────────────────────────────────────────┤"
        echo "   │ Opción 3 - Descarga directa:                                │"
        echo "   │   https://github.com/qpdf/qpdf/releases                     │"
        echo "   │   Descarga el .pkg para macOS e instala                     │"
        echo "   └─────────────────────────────────────────────────────────────┘"
        echo ""
        echo "   Después de instalar, ejecuta ./install.sh de nuevo"
        echo "   o edita config/config.toml con el path correcto de qpdf"
        echo ""
        
        # Usar path por defecto (el usuario deberá ajustarlo)
        QPDF_PATH="/usr/local/bin/qpdf"
    fi
fi

# =============================================================================
# 3. Crear/Actualizar config.toml
# =============================================================================
echo ""
echo "3️⃣  Configurando..."

mkdir -p config

if [ ! -f config/config.toml ]; then
    # Crear desde template
    cp config.example.toml config/config.toml
    echo "   📝 Creado config/config.toml desde template"
    CONFIG_CREATED=true
else
    echo "   ✓ config/config.toml ya existe"
    CONFIG_CREATED=false
fi

# Actualizar paths detectados en config.toml
if [ -n "$PYTHON_PATH" ]; then
    # Usar sed para reemplazar el python_path
    sed -i '' "s|python_path = \".*\"|python_path = \"$PYTHON_PATH\"|" config/config.toml
    echo "   ✓ python_path actualizado: $PYTHON_PATH"
fi

if [ -n "$QPDF_PATH" ]; then
    sed -i '' "s|qpdf_path = \".*\"|qpdf_path = \"$QPDF_PATH\"|" config/config.toml
    echo "   ✓ qpdf_path actualizado: $QPDF_PATH"
fi

if [ "$CONFIG_CREATED" = true ]; then
    echo ""
    echo "   ⚠️  ¡IMPORTANTE! Edita config/config.toml con tus valores:"
    echo "      - gemini.api_key (obtener en https://aistudio.google.com/app/apikey)"
    echo "      - pdf.password (password de tus PDFs bancarios)"
    echo "      - paths.output_folder (dónde guardar los archivos)"
fi

# =============================================================================
# 4. Crear carpetas necesarias
# =============================================================================
echo ""
echo "4️⃣  Creando carpetas..."
mkdir -p ~/Library/MailEML
echo "   ✓ ~/Library/MailEML"

# =============================================================================
# 5. Instalar dependencias Python
# =============================================================================
echo ""
echo "5️⃣  Instalando dependencias Python..."
echo "   - google-genai (Gemini AI SDK)"
echo "   - pydantic (validación de datos)"
echo "   - beautifulsoup4 (procesamiento HTML)"
echo "   - markdownify (conversión HTML→Markdown)"
"$PYTHON_PATH" -m pip install -r requirements.txt --quiet --disable-pip-version-check
echo "   ✓ Todas las dependencias instaladas"

# =============================================================================
# 6. Compilar AppleScripts e instalar en Mail
# =============================================================================
echo ""
echo "6️⃣  Compilando AppleScripts..."

MAIL_SCRIPTS_DIR="$HOME/Library/Application Scripts/com.apple.mail"
mkdir -p "$MAIL_SCRIPTS_DIR"

cd applescripts

if [ -f procesar_eecc.applescript ]; then
    osacompile -o "$MAIL_SCRIPTS_DIR/procesar_eecc.scpt" procesar_eecc.applescript
    echo "   ✓ procesar_eecc.scpt"
fi

if [ -f procesar_taxi.applescript ]; then
    osacompile -o "$MAIL_SCRIPTS_DIR/procesar_taxi.scpt" procesar_taxi.applescript
    echo "   ✓ procesar_taxi.scpt"
fi

cd ..

echo "   📁 Instalados en: $MAIL_SCRIPTS_DIR/"

# =============================================================================
# 7. Resumen final
# =============================================================================
echo ""
echo "======================================="
echo "✅ Instalación completada!"
echo ""
echo "📋 Configuración detectada:"
echo "   Python: $PYTHON_PATH"
echo "   qpdf:   $QPDF_PATH"
echo ""

if [ "$CONFIG_CREATED" = true ]; then
    echo "⚠️  ACCIÓN REQUERIDA:"
    echo "   Edita config/config.toml y configura:"
    echo "   - API key de Gemini"
    echo "   - Password del PDF"
    echo "   - Carpeta de salida"
    echo ""
fi

echo "📋 Pasos para configurar Mail.app:"
echo ""
echo "1. Crea carpetas 'EECC' y 'Taxis' en tu buzón"
echo ""
echo "2. Mail → Preferencias → Reglas → Agregar regla:"
echo "   - Condición: From contains [remitentes de bancos/taxis]"
echo "   - Acción: Run AppleScript → procesar_eecc.scpt (o procesar_taxi.scpt)"
echo "   - NO marques 'Move Message' ni 'Mark as Read'"
echo ""
