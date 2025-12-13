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
        if brew install qpdf 2>/dev/null; then
            QPDF_PATH=$(which qpdf)
            echo "   ✓ Instalado: $QPDF_PATH"
            QPDF_INSTALLED=true
        fi
    fi
    
    # Intentar con MacPorts si Homebrew no funcionó
    if [ "$QPDF_INSTALLED" = false ] && command -v port &> /dev/null; then
        echo "   📥 Instalando qpdf via MacPorts..."
        if sudo port install qpdf 2>/dev/null; then
            QPDF_PATH=$(which qpdf)
            echo "   ✓ Instalado: $QPDF_PATH"
            QPDF_INSTALLED=true
        fi
    fi
    
    # Si no hay gestor de paquetes, ofrecer instalar Homebrew
    if [ "$QPDF_INSTALLED" = false ]; then
        echo ""
        echo "   No se encontró Homebrew ni MacPorts."
        echo "   Homebrew es el gestor de paquetes más popular para macOS."
        echo ""
        read -p "   ¿Deseas instalar Homebrew y qpdf automáticamente? [s/N] " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[SsYy]$ ]]; then
            echo ""
            echo "   📥 Instalando Homebrew..."
            echo "   (Esto puede tardar unos minutos)"
            echo ""
            
            # Instalar Homebrew de forma no interactiva
            NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            
            # Agregar Homebrew al PATH para esta sesión
            if [[ $(uname -m) == "arm64" ]]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            else
                eval "$(/usr/local/bin/brew shellenv)"
            fi
            
            echo ""
            echo "   ✓ Homebrew instalado"
            echo ""
            echo "   📥 Instalando qpdf..."
            brew install qpdf
            
            if command -v qpdf &> /dev/null; then
                QPDF_PATH=$(which qpdf)
                echo "   ✓ qpdf instalado: $QPDF_PATH"
                QPDF_INSTALLED=true
            fi
        fi
    fi
    
    # Si aún no se instaló, dar instrucciones manuales
    if [ "$QPDF_INSTALLED" = false ]; then
        echo ""
        echo "   ❌ qpdf no instalado"
        echo ""
        echo "   Para instalar manualmente:"
        echo "   ┌─────────────────────────────────────────────────────────────┐"
        echo "   │ Opción 1 - Homebrew:                                        │"
        echo "   │   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "   │   brew install qpdf                                         │"
        echo "   ├─────────────────────────────────────────────────────────────┤"
        echo "   │ Opción 2 - MacPorts:                                        │"
        echo "   │   https://www.macports.org/install.php                      │"
        echo "   │   sudo port install qpdf                                    │"
        echo "   └─────────────────────────────────────────────────────────────┘"
        echo ""
        echo "   Después de instalar qpdf, ejecuta ./install.sh de nuevo"
        echo ""
        
        # Usar path por defecto
        QPDF_PATH="/opt/homebrew/bin/qpdf"
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

# Crear copias temporales con paths actualizados
TEMP_DIR=$(mktemp -d)

for script in applescripts/*.applescript; do
    if [ -f "$script" ]; then
        SCRIPT_NAME=$(basename "$script")
        TEMP_SCRIPT="$TEMP_DIR/$SCRIPT_NAME"
        
        # Copiar y actualizar paths
        cp "$script" "$TEMP_SCRIPT"
        
        # Actualizar installPath con el directorio actual
        sed -i '' "s|property installPath : \".*\"|property installPath : \"$SCRIPT_DIR\"|" "$TEMP_SCRIPT"
        
        # Actualizar pythonPath
        sed -i '' "s|set pythonPath to \".*\"|set pythonPath to \"$PYTHON_PATH\"|" "$TEMP_SCRIPT"
        
        # Compilar e instalar
        SCPT_NAME="${SCRIPT_NAME%.applescript}.scpt"
        osacompile -o "$MAIL_SCRIPTS_DIR/$SCPT_NAME" "$TEMP_SCRIPT"
        echo "   ✓ $SCPT_NAME (paths configurados)"
    fi
done

# Limpiar
rm -rf "$TEMP_DIR"

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
