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
- 🧩 Arquitectura modular para agregar nuevos processors

## 🚀 Instalación Rápida

### Opción 1: App con Wizard (Recomendada)

1. **Descarga** `Mail Processors.app` de [Releases](https://github.com/rmichelena/apple_mail_processors/releases)
2. **Mueve** la app a `/Applications` o donde prefieras
3. **Abre** la app y sigue el wizard

El wizard automáticamente:
- ✅ Verifica/instala Python y qpdf
- ✅ Te permite seleccionar qué processors activar
- ✅ Configura carpetas de Mail, API key, y directorio de salida
- ✅ Crea las carpetas necesarias en Mail.app
- ✅ Instala las dependencias Python
- ✅ Compila e instala los AppleScripts

### Opción 2: Instalación Manual (Desarrolladores)

```bash
git clone https://github.com/rmichelena/apple_mail_processors.git
cd apple_mail_processors
./install.sh
nano config/config.toml  # Configurar API key, passwords, etc.
```

## 📋 Requisitos

- **macOS 11 Big Sur o superior**
- **Python 3.11+**
- **API Key de Google Gemini** - [Obtener gratis](https://aistudio.google.com/app/apikey)
- **qpdf** - Para descifrar PDFs (se instala automáticamente)

| macOS | Soporte |
|-------|---------|
| 14 Sonoma | ✅ |
| 13 Ventura | ✅ |
| 12 Monterey | ✅ |
| 11 Big Sur | ✅ |
| 10.15 o anterior | ❌ |

## 🏗️ Arquitectura

```
Mail.app
    │
    ├─ Regla: Estado de Cuenta → AppleScript → Python
    │                                             │
    │                                             ├─ Extrae PDF del .eml
    │                                             ├─ Quita password (qpdf)
    │                                             ├─ Valida con Gemini
    │                                             ├─ Si válido: genera CSVs/JSON
    │                                             └─ Si válido: mueve a EECC/
    │
    └─ Regla: Taxi → AppleScript → Python
                                      │
                                      ├─ Convierte HTML a Markdown
                                      ├─ Valida con Gemini
                                      ├─ Si válido: agrega a CSV
                                      └─ Si válido: mueve a Taxis/
```

> **Nota:** Si el documento no es válido (publicidad, etc.), el mensaje 
> queda sin procesar para revisión manual.

## 📁 Estructura

```
apple_mail_processors/
├── Mail Processors.app/          # 🆕 App con wizard de instalación
│   └── Contents/
│       └── Resources/
│           ├── processors/       # Processors modulares
│           │   ├── eecc/
│           │   ├── taxi/
│           │   └── amazon/       # (próximamente)
│           └── lib/              # Módulos Python compartidos
├── scripts/                      # Scripts para instalación manual
├── applescripts/                 # Fuentes AppleScript (texto)
├── config.example.toml           # Template de configuración
├── install.sh                    # Instalador alternativo (CLI)
└── README.md
```

## ⚙️ Configuración Post-Instalación

Después de ejecutar el wizard, solo necesitas crear las **reglas en Mail.app**:

1. Mail → Preferencias → Reglas → Agregar regla
2. **Para Estados de Cuenta:**
   - Condición: "From contains" + remitentes de tus bancos
   - Acción: "Run AppleScript" → `Mail_Processors_EECC.scpt`
3. **Para Taxis:**
   - Condición: "From contains" + uber, cabify, etc.
   - Acción: "Run AppleScript" → `Mail_Processors_Taxi.scpt`

⚠️ **Importante:** NO agregues "Move Message" ni "Mark as Read" en las reglas.

## 📤 Salida

### Estados de Cuenta

Por cada PDF genera:
- `Visa Interbank 2025-05 PEN.csv` - Movimientos en soles
- `Visa Interbank 2025-05 USD.csv` - Movimientos en dólares
- `Visa Interbank 2025-05.json` - Metadata completa
- `Visa Interbank 2025-05.pdf` - PDF renombrado

```csv
fecha,descripcion,monto,tipo
2025-05-01,WONG SURCO,125.50,consumo
2025-05-02,NETFLIX.COM,44.90,consumo
```

### Viajes de Taxi

CSV consolidado: `viajes taxi.csv`

```csv
fecha,hora,empresa,origen,destino,moneda,precio
2025-05-01,08:30,Uber,Av. Prado 123,Aeropuerto,PEN,45.00
```

## 📋 Logs

```bash
# Ver logs en tiempo real
tail -f ~/Library/Logs/MailProcessors_EECC.log
tail -f ~/Library/Logs/MailProcessors_Taxi.log
```

## 🛠️ Uso Manual

```bash
# Procesar PDF directamente
python3 scripts/extract_movements.py "/ruta/al/estado-cuenta.pdf"

# Procesar .eml de estado de cuenta
python3 scripts/extract_from_email.py "/ruta/al/correo.eml"

# Procesar .eml de taxi
python3 scripts/extract_taxi_trip.py "/ruta/al/correo.eml"
```

## 🐛 Troubleshooting

### El script no se ejecuta
- Verifica permisos: Preferencias → Privacidad → Automatización
- Revisa logs: `tail -50 ~/Library/Logs/MailProcessors_EECC.log`

### Error de qpdf
```bash
brew reinstall qpdf
```

### Error de API Gemini
- Verifica la API key en `~/.config/mail_processors/config.toml`
- Revisa tu uso en https://aistudio.google.com/

## 💰 Costos

- ~$0.001 por estado de cuenta
- ~$0.0002 por correo de taxi
- Con uso normal: prácticamente $0/mes

## 🔐 Seguridad

- La configuración se guarda en `~/.config/mail_processors/config.toml`
- **NUNCA** subas archivos de configuración a git
- El `.gitignore` ya excluye archivos sensibles

## 📜 Licencia

MIT License
