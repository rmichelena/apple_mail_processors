#!/usr/bin/env python3
"""
Módulo de configuración - Carga config.toml
"""

import tomllib
from pathlib import Path

# Ruta al archivo de configuración
CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "config.toml"

# Cargar configuración
if not CONFIG_FILE.exists():
    raise FileNotFoundError(
        f"No se encontró {CONFIG_FILE}\n"
        f"Copia config.example.toml a config/config.toml y edita con tus valores."
    )

with open(CONFIG_FILE, "rb") as f:
    _config = tomllib.load(f)

# =============================================================================
# Exportar valores de configuración
# =============================================================================

# Gemini
GEMINI_API_KEY = _config["gemini"]["api_key"]

# Paths
OUTPUT_FOLDER = Path(_config["paths"]["output_folder"]).expanduser()
PYTHON_PATH = _config["paths"]["python_path"]
QPDF_PATH = _config["paths"]["qpdf_path"]
EML_TEMP_FOLDER = Path(_config["paths"]["eml_temp_folder"]).expanduser()

# Mail
EECC_FOLDER = _config["mail"]["eecc_folder"]
TAXI_FOLDER = _config["mail"]["taxi_folder"]

# PDF
PDF_PASSWORD = _config["pdf"]["password"]

# Logging
EECC_LOG = Path(_config["logging"]["eecc_log"]).expanduser()
TAXI_LOG = Path(_config["logging"]["taxi_log"]).expanduser()

# Archivos de salida
TAXI_CSV = OUTPUT_FOLDER / "viajes taxi.csv"
EECC_ERROR_LOG = OUTPUT_FOLDER / "errores.log"
TAXI_ERROR_LOG = OUTPUT_FOLDER / "errores_taxi.log"

# Directorio de scripts (para llamar a otros scripts)
SCRIPTS_DIR = Path(__file__).parent


def ensure_folders():
    """Crea las carpetas necesarias si no existen"""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    EML_TEMP_FOLDER.mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    # Test - mostrar configuración cargada
    print("Configuración cargada:")
    print(f"  OUTPUT_FOLDER: {OUTPUT_FOLDER}")
    print(f"  PYTHON_PATH: {PYTHON_PATH}")
    print(f"  QPDF_PATH: {QPDF_PATH}")
    print(f"  EML_TEMP_FOLDER: {EML_TEMP_FOLDER}")
    print(f"  EECC_FOLDER: {EECC_FOLDER}")
    print(f"  TAXI_FOLDER: {TAXI_FOLDER}")
    print(f"  GEMINI_API_KEY: {GEMINI_API_KEY[:10]}...")

