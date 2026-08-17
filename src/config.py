#Librerias
from pathlib import Path
import os
from dotenv import load_dotenv

# Rutas

# Directorio donde está el notebook
NOTEBOOK_DIR = Path.cwd()
# Subir un nivel → raíz del proyecto
ROOT_DIR = NOTEBOOK_DIR#.parent.parent
# Carpetas del proyecto
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
AOD_DIR = DATA_RAW_DIR / "AOD"
NDVI_DIR = DATA_RAW_DIR / "NDVI"
ERA5_DIR = DATA_RAW_DIR / "ERA5"
MERRA_DIR = DATA_RAW_DIR / "MERRA"
DEM_DIR = DATA_RAW_DIR / "DEM"

#Sitios
SITES = {
    "San Pablo": {
        "west": -47.18761699953164,
        "south": -23.769825082026546,
        "east": -46.2989251168905,
        "north": -23.15380334079614
    },

    "Santiago": {
        "west": -71.0653675613302, #supizq
        "south": -33.74283779348805, #AbajDer
        "east": -70.3061109228608, #abajder
        "north": -33.07880767505593 #SupIzq
    },

"Medellin": {
        "west": -75.73349373413268,
        "south": 6.064656084590012,
        "east": -75.3546571948446,
        "north": 6.45881903338495
    },

"Mexico": {
        "west": -99.62981206846747,
        "south": 18.79096843909478,
        "east": -98.41583428026645,
        "north": 19.9977998136125
    },

}

# Variables de entorno

ENV_FILE = ROOT_DIR / ".env"

load_dotenv(ENV_FILE)

TOKEN_MAIAC = os.getenv("TOKEN_MAIAC")
EARTHDATA_USERNAME = os.getenv("EARTHDATA_USERNAME")
EARTHDATA_PASSWORD = os.getenv("EARTHDATA_PASSWORD")


# Validar credenciales
if not TOKEN_MAIAC:
    raise ValueError("No se encontró TOKEN_MAIAC en .env")

if not EARTHDATA_USERNAME:
    raise ValueError("No se encontró EARTHDATA_USERNAME en .env")

if not EARTHDATA_PASSWORD:
    raise ValueError("No se encontró EARTHDATA_PASSWORD en .env")