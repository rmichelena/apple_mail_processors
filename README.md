# Apple Mail Processors

Sistema automatizado para procesar correos en Apple Mail:
- **Estados de cuenta** de tarjetas de crédito → extrae movimientos a CSV
- **Viajes de taxi** (Uber, Cabify, Beat, etc.) → consolida en CSV

Usa **Google Gemini Flash 2.5** para extracción inteligente de datos.

## ✨ Características

- 🤖 Extracción inteligente con IA (Gemini)
- 🔐 Descifrado automático de PDFs protegidos
- 📊 Genera CSVs separados por moneda (PEN/USD)
- 📬 Mueve y marca correos automáticamente
- ⚠️ Validación: solo procesa documentos válidos (ignora publicidad)
- 💰 Costo mínimo (~$0.001 por documento)

## 🏗️ Arquitectura

```
Mail.app
    │
    ├─ Regla: Estado de Cuenta → AppleScript → Python
    │                                             │
    │                                             ├─ Extrae PDF del .eml
    │                                             ├─ Quita password (qpdf)
    │                                             ├─ Valida con Gemini (¿es EECC real?)
    │                                             ├─ Si válido: genera CSVs/JSON
    │                                             └─ Si válido: mueve a EECC/
    │
    └─ Regla: Taxi → AppleScript → Python
                                      │
                                      ├─ Convierte HTML a Markdown
                                      ├─ Valida con Gemini (¿es recibo real?)
                                      ├─ Si válido: agrega a CSV
                                      └─ Si válido: mueve a Taxis/
```

> **Nota:** Si el documento no es válido (publicidad, otro tipo de correo), el mensaje 
> queda sin procesar para revisión manual. Solo se mueven los correos procesados exitosamente.

## 📁 Estructura del Proyecto

```
mail-processors/
├── config/
│   └── config.toml              # 🔒 Configuración real (NO en git)
├── scripts/
│   ├── config.py                # Carga configuración
│   ├── mail_actions.py          # Read+move mensajes vía osascript
│   ├── extract_movements.py     # Extractor de estados de cuenta
│   ├── extract_from_email.py    # Procesa .eml de EECC
│   └── extract_taxi_trip.py     # Procesa .eml de taxis
├── applescripts/
│   ├── procesar_eecc.applescript   # Código fuente (texto, versionable)
│   └── procesar_taxi.applescript   # Código fuente (texto, versionable)
├── config.example.toml          # ✅ Template (SÍ en git)
├── requirements.txt
├── install.sh
├── .gitignore
└── README.md
```

### Nota sobre AppleScripts

Los archivos `.applescript` son **código fuente en texto** (versionables en git).

El script `install.sh` los compila a `.scpt` (binarios) y los instala en:
```
~/Library/Application Scripts/com.apple.mail/
```

Esta es la carpeta requerida por Mail.app para ejecutar scripts desde reglas.

## 📋 Requisitos

- **macOS 11 Big Sur o superior** (probado en Sonoma/Ventura/Monterey)
- **Python 3.11+** (probado con 3.14)
- **qpdf** - para descifrar PDFs (se instala automáticamente si tienes Homebrew)
- **API Key de Google Gemini** - obtener gratis en [AI Studio](https://aistudio.google.com/app/apikey)

### Compatibilidad macOS

| Versión | Soporte |
|---------|---------|
| macOS 14 Sonoma | ✅ Completo |
| macOS 13 Ventura | ✅ Completo |
| macOS 12 Monterey | ✅ Completo |
| macOS 11 Big Sur | ✅ Debería funcionar |
| macOS 10.15 Catalina | ⚠️ Sin soporte oficial de Homebrew |
| macOS 10.14 o anterior | ❌ No soportado |

### Dependencias Python (se instalan automáticamente)
- `google-genai` - SDK de Google Gemini AI
- `pydantic` - Validación de datos
- `beautifulsoup4` - Procesamiento HTML
- `markdownify` - Conversión HTML→Markdown

## 🚀 Instalación

### 1. Clonar/Descargar

```bash
git clone https://github.com/rmichelena/apple_mail_processors.git
cd apple_mail_processors
```

### 2. Ejecutar instalador

```bash
./install.sh
```

El instalador automáticamente:
- ✅ Detecta Python y actualiza la configuración
- ✅ Instala qpdf via Homebrew (si está disponible)
- ✅ Detecta paths y los configura
- ✅ Crea `config/config.toml` desde el template
- ✅ Instala dependencias Python
- ✅ Compila e instala los AppleScripts

### 3. Editar configuración

```bash
nano config/config.toml
```

Solo necesitas configurar manualmente:
- `gemini.api_key` - Obtener en https://aistudio.google.com/app/apikey
- `pdf.password` - Password de tus PDFs bancarios
- `paths.output_folder` - Dónde guardar CSVs/PDFs

> **Nota:** `python_path` y `qpdf_path` se detectan automáticamente durante la instalación.

### 5. Crear carpetas en Mail.app

Crea dos carpetas en tu buzón:
- `EECC` - Para estados de cuenta procesados
- `Taxis` - Para correos de taxi procesados

### 6. Configurar reglas en Mail.app

**Regla para Estados de Cuenta:**
- Menú: Mail → Preferencias → Reglas → Agregar regla
- Nombre: "Procesar EECC"
- Condición: "From contains" + remitentes de tus bancos
- Acción: "Run AppleScript" → selecciona `procesar_eecc.scpt`
  (aparecerá automáticamente si está en `~/Library/Application Scripts/com.apple.mail/`)
- ⚠️ NO agregues "Move Message" ni "Mark as Read"

**Regla para Taxis:**
- Similar, pero con remitentes de Uber, Cabify, etc.
- AppleScript: `procesar_taxi.scpt`

## ⚙️ Configuración

### config.toml

```toml
[gemini]
api_key = "AIzaSy..."  # API key de Google Gemini

[paths]
output_folder = "~/Dropbox/estados-cuenta"  # Dónde guardar archivos
python_path = "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
qpdf_path = "/opt/homebrew/bin/qpdf"
eml_temp_folder = "~/Library/MailEML"

[mail]
eecc_folder = "EECC"    # Carpeta destino en Mail
taxi_folder = "Taxis"   # Carpeta destino en Mail

[pdf]
password = "12345678"   # Password de PDFs bancarios

[logging]
eecc_log = "~/Library/Logs/MailEECCRule.log"
taxi_log = "~/Library/Logs/MailTaxiRule.log"
```

## 📤 Salida

### Estados de Cuenta

Por cada PDF procesado genera:
- `Visa Interbank 2025-05 PEN.csv` - Movimientos en soles
- `Visa Interbank 2025-05 USD.csv` - Movimientos en dólares (si aplica)
- `Visa Interbank 2025-05.json` - Datos completos con metadata
- `Visa Interbank 2025-05.pdf` - PDF renombrado

**Formato CSV:**
```csv
fecha,descripcion,monto,tipo
2025-05-01,WONG SURCO,125.50,consumo
2025-05-02,NETFLIX.COM,44.90,consumo
2025-05-15,PAGO RECIBIDO,-500.00,pago
```

### Viajes de Taxi

Un CSV consolidado: `viajes taxi.csv`

```csv
fecha,hora,empresa,origen,destino,moneda,precio
2025-05-01,08:30,Uber,Av. Javier Prado 123,Aeropuerto Jorge Chávez,PEN,45.00
2025-05-02,19:15,Cabify,Centro Comercial Jockey,Miraflores,PEN,22.50
```

## 📋 Logs

- Estados de cuenta: `~/Library/Logs/MailEECCRule.log`
- Taxis: `~/Library/Logs/MailTaxiRule.log`
- Errores Python: `{output_folder}/errores.log`

Ver logs en tiempo real:
```bash
tail -f ~/Library/Logs/MailEECCRule.log
```

## 🛠️ Uso Manual

### Procesar un PDF directamente

```bash
cd scripts
python3 extract_movements.py "/ruta/al/estado-cuenta.pdf"
```

### Procesar un .eml

```bash
python3 extract_from_email.py "/ruta/al/correo.eml"
```

### Procesar correo de taxi

```bash
python3 extract_taxi_trip.py "/ruta/al/correo.eml"
```

## 🐛 Troubleshooting

### El script no se ejecuta

1. Verifica permisos de automatización:
   - Preferencias del Sistema → Privacidad → Automatización
   - Mail debe poder controlar "System Events"

2. Verifica que Python está en el path correcto:
   ```bash
   which python3
   ```
   
3. Revisa los logs:
   ```bash
   tail -50 ~/Library/Logs/MailEECCRule.log
   ```

### Error de qpdf

```bash
# Verificar instalación
qpdf --version

# Reinstalar si es necesario
brew reinstall qpdf
```

### Error de API Gemini

- Verifica que la API key sea correcta
- Verifica que no hayas excedido el límite gratuito
- Revisa https://aistudio.google.com/ para ver tu uso

### PDFs no se descifran

- Verifica el password en `config/config.toml`
- Algunos bancos usan formatos de password diferentes

## 💰 Costos

Google Gemini Flash 2.5 es muy económico:
- ~$0.001 por estado de cuenta procesado
- ~$0.0002 por correo de taxi

Con uso normal (5-10 correos/mes), el costo es prácticamente $0.

## 🔐 Seguridad

- **NUNCA** subas `config/config.toml` a git (contiene API keys y passwords)
- El archivo `.gitignore` ya lo excluye automáticamente
- Usa `config.example.toml` como template en el repositorio

## 📜 Licencia

MIT License - Usa como quieras.
