# Library

from datetime import datetime
import os
from os import listdir
import pandas as pd
import requests
from pathlib import Path
import os
from dotenv import load_dotenv
import os
import sys
from dateutil.relativedelta import relativedelta
import cdsapi
from tqdm import tqdm
import json
import time
import earthaccess
import math
from .config import (SITES, MERRA_DIR, DEM_DIR, AOD_DIR, ERA5_DIR,
    NDVI_DIR, TOKEN_MAIAC, EARTHDATA_USERNAME, EARTHDATA_PASSWORD)

print("librerias ok")


#Probar en python terminal
#  python -c "from src.download import merra_download; print(merra_download('Santiago', '2026-06-20'))"


# ----------------------------------------------------------------------------------
# DESCARGA AOD
def aod_download (site, date):

    # Configuracion
    SITE = site
    OUTPUT_DIR = AOD_DIR
    # Crear carpeta de descarga si no existe
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    url = "https://ladsweb.modaps.eosdis.nasa.gov/api/v2/content/details"
    headers = {"Authorization": f"Bearer {TOKEN_MAIAC}"}

    #Fecha de interes
    date_range = f"{date}..{date}"
    #Coordenadas
    if site not in SITES:
        raise ValueError(
            f"Sitio '{site}' no configurado. "
            f"Sitios disponibles: {list(SITES.keys())}"
        )

    BBOX = SITES[site]
    # Convertir BBOX al formato requerido por LAADS
    bbox_lads = (
        f"[BBOX]"
        f"W{BBOX['west']} "
        f"S{BBOX['south']} "
        f"E{BBOX['east']} "
        f"N{BBOX['north']}"
    )

    # Parametros para la API
    params = {
        "products": "MCD19A2",
        "temporalRanges": date_range,
        "regions": bbox_lads,
        "formats": "json"
    }

    # Crear carpeta de descarga
    #OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Buscar archivos
    response = requests.get(
        url,
        headers = headers,
        params = params
    )

    response.raise_for_status()
    data = response.json()

    # Validar disponibilidad de datos 
    if data["file_count"] == 0:
        raise RuntimeError(
            f"No se encontraron archivos de AOD "
            f"para el sitio '{site}' en la fecha {date}.")
    print(f"Archivos encontrados: {data['file_count']}")


    # Descargar archivos encontrados
    downloaded = 0
    skipped = 0
    for archivo in data["content"]:
        nombre = archivo["name"]
        download_url = archivo["downloadsLink"]
        output_file = OUTPUT_DIR / nombre
        print(f"Descargando: {nombre}")
        # Si ya existe, no lo volvemos a descargar
        if output_file.exists():
            print("El archivo ya existe. Se omite.")
            skipped += 1
            continue
        with requests.get(
            download_url,
            headers = headers,
            stream = True
        ) as r:
            
            r.raise_for_status()
            with open(output_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        downloaded += 1

        print("Descarga completa")

    return {"site": site, "date": date, "files_found": data["file_count"], "files_downloaded": downloaded, "files_skipped": skipped}


# ----------------------------------------------------------------------------------
# DESCARGA NDVI MOD13A3
def ndvi_download(site, end_date):

# Configuracion
    OUTPUT_DIR = NDVI_DIR
    url = "https://ladsweb.modaps.eosdis.nasa.gov/api/v2/content/details"
    headers = {
        "Authorization": f"Bearer {TOKEN_MAIAC}"
    }

    # Validar sitio
    if site not in SITES:
        raise ValueError(
            f"Sitio '{site}' no configurado. "
            f"Sitios disponibles: {list(SITES.keys())}"
        )
    # BBox
    BBOX = SITES[site]
    bbox_lads = (
        f"[BBOX]"
        f"W{BBOX['west']} "
        f"S{BBOX['south']} "
        f"E{BBOX['east']} "
        f"N{BBOX['north']}"
    )

    # Fecha
    end_date = datetime.strptime(
        end_date,
        "%Y-%m-%d"
    )
    search_date = end_date.replace(day=1)

    # Buscar ultimo dato disponible
    while True:
        test_date = search_date.strftime("%Y-%m-%d")
        date_range = f"{test_date}..{test_date}"
        params = {
            "products": "MOD13A3",
            "temporalRanges": date_range,
            "regions": bbox_lads,
            "formats": "json"
        }
        response = requests.get(
            url,
            headers=headers,
            params=params
        )
        response.raise_for_status()
        data = response.json()
        archivos = data.get("content", [])

        print(f"Buscando MOD13A3: {test_date} → {len(archivos)} archivos")

        if archivos:
            print(f"Último MOD13A3 disponible: {test_date}")
            break
        # Retroceder un mes
        search_date -= relativedelta(months=1)

    # Descargar el ultimo dato disponible
    downloaded = 0
    skipped = 0

    for archivo in archivos:
        nombre = archivo["name"]
        download_url = archivo["downloadsLink"]
        output_file = OUTPUT_DIR / nombre
        print(f"Descargando: {nombre}")
        if output_file.exists():
            print("El archivo ya existe. Se omite.")
            skipped += 1
            continue
        with requests.get(
            download_url,
            headers = headers,
            stream = True
        ) as r:
            r.raise_for_status()
            with open(output_file, "wb") as f:
                for chunk in r.iter_content(
                    chunk_size=8192
                ):
                    if chunk:
                        f.write(chunk)
        downloaded += 1
        print("Descarga completa")

    # Se muestra un resumen de la info descargada

    return {"site": site,
        "date": test_date,
        "files_found": len(archivos),
        "files_downloaded": downloaded,
        "files_skipped": skipped
    }



# ----------------------------------------------------------------------------------
# DESCARGA ERA 5
def era_download(site, date):

    dataset = "reanalysis-era5-land"
    #dataset ="reanalysis-era5-single-levels"
    # Fecha
    date_dt = datetime.strptime(date, "%Y-%m-%d")
    year = date_dt.year
    month = date_dt.month
    day = date_dt.day

    # Validar sitio
    if site not in SITES:
        raise ValueError(
            f"Sitio '{site}' no configurado. "
            f"Sitios disponibles: {list(SITES.keys())}"
        )
    BBOX = SITES[site]
    bbox_era = [BBOX['north'],BBOX['west'],BBOX['south'],BBOX['east']]


    #Archivo salida
    output_file = ERA5_DIR / f"ERA5_{date}.nc"

    if output_file.exists():

        print(f"El archivo ya existe: {output_file.name}")

        return {
            "site": site,
            "date": date,
            "file": output_file.name,
            "downloaded": False,
            "skipped": True
        }


    request = {
        "variable": [
            "10m_u_component_of_wind",
            # "10m_v_component_of_wind",
            # "2m_dewpoint_temperature",
            # "2m_temperature",
            # "surface_pressure",
            # "total_precipitation",
            # "boundary_layer_height"
        ],
        "year": year,
        "month": month,
        "day": day,
        "time": [
            "00:00", "01:00"#, "02:00",
            # "03:00", "04:00", "05:00",
            # "06:00", "07:00", "08:00",
            # "09:00", "10:00", "11:00",
            # "12:00", "13:00", "14:00",
            # "15:00", "16:00", "17:00",
            # "18:00", "19:00", "20:00",
            # "21:00", "22:00", "23:00"
        ],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": bbox_era
    }
    archivos = request.get("content", [])
    client = cdsapi.Client()
    
    client.retrieve(dataset, request, target= output_file)#.download()

    print(f"Descarga completa:{output_file.name}")
    # Se muestra un resumen de la info descargada
    return {
        "site": site,
        "date": date,
        "file": output_file.name,
        "downloaded": True,
        "skipped": False }



# ----------------------------------------------------------------------------------
#DESCARGA MERRA 2
def merra_download(site, date):
    auth = earthaccess.login(strategy="environment",persist=False)
    # Configuracion
    variables = ["BCSMASS","DUSMASS", "OCSMASS", "SO2SMASS", "SO4SMASS", "SSSMASS" ]

    OUTPUT_DIR = MERRA_DIR
    CMR_URL = ("https://cmr.earthdata.nasa.gov/search/granules.umm_json")

    SUBSET_URL = ("https://disc.gsfc.nasa.gov/service/subset/jsonwsp" )
    SHORT_NAME = "M2T1NXAER"
    VERSION = "5.12.4"
    PRODUCT = "M2T1NXAER_V5.12.4"
    # Validar sitio
    if site not in SITES:
        raise ValueError(
            f"Sitio '{site}' no configurado. "
            f"Sitios disponibles: {list(SITES.keys())}"
        )
    BBOX = SITES[site]
    # Archivo de salida
    filename = (f"MERRA_{site}_{date}_aerosols.nc4")
    output_file = OUTPUT_DIR / filename
    # Si ya existe ==> no hacer nada

    if output_file.exists():
        print(f"El archivo ya existe:")
        print(output_file)
        return {
            "site": site,
            "date": date,
            "status": "skipped",
            "file": str(output_file)
        }

    # Autenticacion de earthdata
    # print("Autenticando con Earthdata...")
    #auth = earthaccess.login()
    # Fecha
    start = f"{date}T00:00:00Z"
    end = f"{date}T23:59:59Z"
    temporal = f"{start},{end}"


    # BBOXX
    bbox = (
        f"{BBOX['west']},"
        f"{BBOX['south']},"
        f"{BBOX['east']},"
        f"{BBOX['north']}"
    )

    # Buscar granulo de MERRA de CMR
    print("\nBuscando datos MERRA-2...")
    params = {
        "short_name": SHORT_NAME,
        "version": VERSION,
        "temporal": temporal,
        "bounding_box": bbox,
        "page_size": 2000
    }

    response = requests.get(
        CMR_URL,
        params=params,
        headers={
            "Accept": "application/json"
        },
        timeout=120
    )
    response.raise_for_status()
    data = response.json()
    print(f"Granules encontrados: {data['hits']}")
    if data["hits"] == 0:
        raise RuntimeError(
            f"No se encontraron datos MERRA-2 "
            f"para '{site}' en {date}."
        )

    # Creae request del recorte

    subset_request = {
        "methodname": "subset",
        "type": "jsonwsp/request",
        "version": "1.0",
        "args": {
            "role": "subset",
            "start": start,
            "end": end,
            "box": [BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"]],
            "crop": True,
            "data": [{"datasetId": PRODUCT, "variable": variable}
                for variable in variables]
        }
    }


    # print("\nSolicitando subset...")
    # print(f"Sitio: {site}")
    # print(f"Fecha: {date}")
    # print(f"Variables: {variables}")
    # print(f"BBOX: {BBOX}")
    # Enviar request
    subset_response = requests.post(
        SUBSET_URL,
        json=subset_request,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        }, timeout=120 )

    # print("\nStatus Subsetter:", subset_response.status_code)

    if not subset_response.ok:
        print(subset_response.text)
        subset_response.raise_for_status()

    subset_data = subset_response.json()
    job_id = subset_data["result"]["jobId"]
    session_id = subset_data["result"]["sessionId"]

    # print(f"\nJob creado: {job_id}")
    # Esperar que termine el procesamiento

    print("\nProcesando subset...")

    while True:
        status_request = {
            "methodname": "GetStatus",
            "type": "jsonwsp/request",
            "version": "1.0",
            "args": {
                "jobId": job_id,
                "sessionId": session_id
            }
        }

        status_response = requests.post(
            SUBSET_URL,
            json=status_request,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },timeout=120)
        
        status_response.raise_for_status()
        status_data = status_response.json()
        result = status_data["result"]
        status = result["Status"]
        progress = result.get("PercentCompleted",0 )

        print(f"Estado: {status} {progress}%)"
        )

        if status == "Succeeded":
            break

        if status in ["Failed", "Error", "Canceled"]:
            raise RuntimeError(f"El subset falló: {result}")
        time.sleep(5)


    # Obtener resultados
    # print("\nObteniendo resultado...")
    result_request = {
        "methodname": "GetResult",
        "type": "jsonwsp/request",
        "version": "1.0",
        "args": {
            "jobId": job_id,
            "sessionId": session_id
        }
    }

    result_response = requests.post(
        SUBSET_URL,
        json=result_request,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=120
    )

    result_response.raise_for_status()
    result_data = result_response.json()

    # Buscar archivo netcdf

    items = result_data["result"]["items"]
    result_url = None
    for item in items:
        label = item.get("label", "")
        if label.endswith(".dap.nc4"):
            result_url = item["link"]
            break

    if result_url is None:
        raise RuntimeError(
            "No se encontró el archivo "
            "NetCDF en el resultado del subset."
        )


    # print("\nArchivo generado por NASA:")
    # print(result_url)
    #Descargar recorte y no toda la imagen completa
    print("\nDescargando subset...")
    # Sesión autenticada de Earthdata
    session = earthaccess.__auth__.get_session()
    # Nombre del archivo local
    filename = (f"MERRA_{site}_{date}.nc4")
    output_file = OUTPUT_DIR / filename

    print(f"Archivo destino:")
    print(output_file)

    # Si ya existe no descargar!
    if output_file.exists():
        print("\nEl archivo ya existe.")
        print("Se omite la descarga.")
        return {
            "site": site,
            "date": date,
            "status": "skipped",
            "file": str(output_file),
            "variables": variables,
            "job_id": job_id
        }

    # Descargar
    print("\nDescargando desde NASA...")

    with session.get(result_url, stream=True, timeout=300) as r:
        print("Status descarga:",r.status_code)

        if not r.ok:
            print("\nRespuesta NASA:")
            print(r.text[:1000])
            r.raise_for_status()

        # Guardar archivo
        with open(
            output_file,
            "wb"
        ) as f:
            for chunk in r.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk:
                    f.write(chunk)
    print("\nDescarga completa.")
    print(f"Archivo: {output_file}")

    # Return
    return {
        "site": site,
        "date": date,
        "status": "downloaded",
        "file": str(output_file),
        "variables": variables,
        "job_id": job_id}



# ----------------------------------------------------------------------------------
# DESCARGA DEM - Elevacion
def dem_download(site):
    # Configuracion
    OUTPUT_DIR = DEM_DIR
    SHORT_NAME = "SRTMGL1"
    VERSION = "003"

    # Validar sitio
    if site not in SITES:
        raise ValueError(
            f"Sitio '{site}' no configurado. "
            f"Sitios disponibles: {list(SITES.keys())}" )

    BBOX = SITES[site]
    # print("=" * 60)
    # print("SRTM - DESCARGA DE ELEVACIÓN")
    # print("=" * 60)
    # print(f"Sitio: {site}")
    # print(f"BBOX: {BBOX}")

    # BBOX
    bounding_box = (BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"])

    # Autenticacion
    # print("\nAutenticando con Earthdata...")
    auth = earthaccess.login()

    # Buscar granulos
    # print("\nBuscando tiles SRTM...")
    results = earthaccess.search_data(
        short_name=SHORT_NAME,
        version=VERSION,
        bounding_box=bounding_box,
        cloud_hosted=True)

    # print(f"Granules encontrados: {len(results)}")
    if len(results) == 0:
        raise RuntimeError(
            f"No se encontraron datos SRTM "
            f"para el sitio '{site}'."
        )

    # Mostrar granulos encontrados
    # print("\nTiles encontrados:")
    # for granule in results:
    #     print(f"  - {granule}")

    # Descargar
    # print("\nDescargando tiles...")
    downloaded_files = earthaccess.download(results, local_path=str(OUTPUT_DIR))

    # Resultados
    # print("\n" + "=" * 60)
    # print("RESUMEN SRTM")
    # print("=" * 60)

    # print(f"Sitio:              {site}")
    # print(f"Granules encontrados: {len(results)}")
    # print(f"Archivos descargados: {len(downloaded_files)}")

    for file in downloaded_files:
        print(f"  ✓ {file}")
    return {
        "site": site,
        "tiles_found": len(results),
        "downloaded": len(downloaded_files),
        "files": [str(f) for f in downloaded_files]
    }