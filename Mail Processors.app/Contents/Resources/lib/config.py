#!/usr/bin/env python3
"""
Módulo de configuración para Mail Processors

Busca config en orden:
1. ~/.config/mail_processors/config.toml (instalación de usuario)
2. {APP_PATH}/Contents/Resources/config/config.toml (dentro de la app)
"""

import os
import sys
import tomllib
from pathlib import Path

# =============================================================================
# Detectar ubicación de la app
# =============================================================================

def get_app_path() -> Path:
    """Detecta el path a Contents/Resources de la app"""
    # Si estamos ejecutando desde dentro de la app
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    
    # Buscar hacia arriba hasta encontrar Contents/Resources
    current = Path(__file__).resolve()
    for parent in current.parents:
        if parent.name == 'Resources' and parent.parent.name == 'Contents':
            return parent
    
    # Fallback: directorio del script
    return Path(__file__).parent.parent


APP_PATH = get_app_path()

# =============================================================================
# Buscar archivo de configuración
# =============================================================================

def find_config() -> Path:
    """Busca el archivo de configuración en orden de prioridad"""
    
    # 1. Config de usuario (preferido)
    user_config = Path.home() / '.config' / 'mail_processors' / 'config.toml'
    if user_config.exists():
        return user_config
    
    # 2. Config dentro de la app
    app_config = APP_PATH / 'config' / 'config.toml'
    if app_config.exists():
        return app_config
    
    # 3. Config de desarrollo (carpeta actual)
    dev_config = Path.cwd() / 'config' / 'config.toml'
    if dev_config.exists():
        return dev_config
    
    raise FileNotFoundError(
        "No se encontró config.toml.\n"
        "Ejecuta la app Mail Processors para configurar."
    )


CONFIG_FILE = find_config()

# Cargar configuración
with open(CONFIG_FILE, "rb") as f:
    _config = tomllib.load(f)

# =============================================================================
# Exportar valores de configuración
# =============================================================================

# Gemini
GEMINI_API_KEY = _config.get("gemini", {}).get("api_key", "")

# Validar API key
if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("YOUR_"):
    raise ValueError(
        "❌ API key de Gemini no configurada.\n"
        "   Ejecuta la app Mail Processors para configurar tu API key.\n"
        "   Obtén una gratis en: https://aistudio.google.com/app/apikey"
    )

# Paths
_paths = _config.get("paths", {})
OUTPUT_FOLDER = Path(_paths.get("output_folder", "~/Documents")).expanduser()
PYTHON_PATH = _paths.get("python_path", "/usr/bin/python3")
QPDF_PATH = _paths.get("qpdf_path", "/opt/homebrew/bin/qpdf")
EML_TEMP_FOLDER = Path(_paths.get("eml_temp_folder", "~/Library/MailEML")).expanduser()

# Mail
_mail = _config.get("mail", {})
EECC_FOLDER = _mail.get("eecc_folder", "EECC")
TAXI_FOLDER = _mail.get("taxi_folder", "Taxis")

# PDF
PDF_PASSWORD = _config.get("pdf", {}).get("password", "")

# Logging
_logging = _config.get("logging", {})
EECC_LOG = Path(_logging.get("eecc_log", "~/Library/Logs/MailEECCRule.log")).expanduser()
TAXI_LOG = Path(_logging.get("taxi_log", "~/Library/Logs/MailTaxiRule.log")).expanduser()

# Archivos de salida
TAXI_CSV = OUTPUT_FOLDER / "viajes taxi.csv"
EECC_ERROR_LOG = OUTPUT_FOLDER / "errores.log"
TAXI_ERROR_LOG = OUTPUT_FOLDER / "errores_taxi.log"


def ensure_folders():
    """Crea las carpetas necesarias si no existen"""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    EML_TEMP_FOLDER.mkdir(parents=True, exist_ok=True)


def get_processor_path(processor_id: str) -> Path:
    """Obtiene el path a un processor específico"""
    return APP_PATH / 'processors' / processor_id


if __name__ == '__main__':
    # Test - mostrar configuración cargada
    print(f"Config file: {CONFIG_FILE}")
    print(f"App path: {APP_PATH}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print(f"Gemini API key: {GEMINI_API_KEY[:10]}..." if GEMINI_API_KEY else "No API key")

