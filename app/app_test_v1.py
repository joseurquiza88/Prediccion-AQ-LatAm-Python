# Librerías
from pathlib import Path
import re

import pandas as pd
import rasterio


# Directorio principal del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent

# Carpeta donde están los TIFF
MAPS_DIR = ROOT_DIR / "data" / "processed" / "maps"

# Buscar archivos TIFF
tif_files = list(MAPS_DIR.glob("*.tif"))


def crear_catalogo(tif_files):

    registros = []

    patron = r"^([A-Za-z]+)_PM2\.5_M_(\d{2})-(\d{4})_([A-Za-z]{2})_V1\.1\.tif$"

    for archivo in tif_files:

        match = re.match(patron, archivo.name)

        if not match:
            print(f"No se pudo interpretar: {archivo.name}")
            continue

        modelo = match.group(1)
        mes = int(match.group(2))
        anio = int(match.group(3))
        ciudad = match.group(4)

        with rasterio.open(archivo) as src:

            bbox = src.bounds

            registros.append({
                "modelo": modelo,
                "mes": mes,
                "anio": anio,
                "ciudad": ciudad,
                "archivo": archivo,
                "left": bbox.left,
                "bottom": bbox.bottom,
                "right": bbox.right,
                "top": bbox.top
            })

    return pd.DataFrame(registros)


catalogo = crear_catalogo(tif_files)

print("\n--- Catálogo ---")
print(catalogo.head())

print("\nCantidad de registros:", len(catalogo))



print("\n--- Modelos ---")
print(catalogo["modelo"].unique())

print("\n--- Ciudades ---")
print(catalogo["ciudad"].unique())

print("\n--- Años ---")
print(catalogo["anio"].unique())

print("\n--- Cantidad de mapas por modelo ---")
print(catalogo["modelo"].value_counts())

print("\n--- Cantidad de mapas por ciudad ---")
print(catalogo["ciudad"].value_counts())


duplicados = catalogo[
    catalogo.duplicated(
        subset=["ciudad", "anio", "mes"],
        keep=False
    )
]

print("\n--- Combinaciones duplicadas ---")
print(duplicados[["modelo", "mes", "anio", "ciudad", "archivo"]])