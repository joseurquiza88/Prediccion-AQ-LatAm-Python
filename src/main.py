#Librerias
from src.download import (aod_download, ndvi_download, era_download, merra_download, dem_download)

#Setear info de entrada
SITE = "Santiago"
DATE = "2026-06-20"

#01. Descarga de variables
aod_download(SITE, DATE)
ndvi_download(SITE, DATE)
era_download(SITE, DATE)
merra_download(SITE, DATE)
dem_download(SITE)

#02. Procesamiento de variables
#03. Aplicacion de modelo
#04. Generacion de mapa
#05. Mapa dinamico