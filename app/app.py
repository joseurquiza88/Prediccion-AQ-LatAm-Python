# Librerías
from pathlib import Path
import re
import pandas as pd
import rasterio
from dash import Dash, html, dcc, Input, Output, State
import base64
from io import BytesIO
import numpy as np
from PIL import Image
import dash_leaflet as dl
from matplotlib.colors import LinearSegmentedColormap
# ---------------------------------------------------------
# Directorio principal del proyecto

ROOT_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------
# Carpeta donde están los TIFF

MAPS_DIR = ROOT_DIR / "data" / "processed" / "maps"


# ---------------------------------------------------------
# Buscar archivos TIFF

tif_files = list(MAPS_DIR.glob("*.tif"))


# ---------------------------------------------------------
# Crear catálogo

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


# ---------------------------------------------------------
# Crear catálogo

catalogo = crear_catalogo(tif_files)
ciudades = sorted(catalogo["ciudad"].unique())
anios = sorted(catalogo["anio"].unique())
meses = sorted(catalogo["mes"].unique())

# Revision de la info
print(f"Cantidad de mapas: {len(catalogo)}")
print("Ciudades:", ciudades)
print("Años:", anios)
print("Meses:", meses)

# ---------------------------------------------------------
# Funcion para crear raster
def raster_to_image(raster_path):

    with rasterio.open(raster_path) as src:

        data = src.read(1, masked=True)
        bounds = src.bounds

        # -----------------------------------------------------
        # Escala de colores PM2.5
        # Basada en la paleta utilizada en la app original
        # Dominio fijo: 0 - 60 µg/m³

        colores = [
            "#1a9850",  # verde
            "#ffffbf",  # amarillo
            "#FF8000",  # naranja
            "#d73027",  # rojo
            "#8B00FF"   # violeta
        ]

        cmap = LinearSegmentedColormap.from_list(
            "pm25",
            colores
        )

        # -----------------------------------------------------
        # Normalizar entre 0 y 60

        data_clip = np.clip(data, 0, 60)

        normalized = data_clip / 60

        # Aplicar colores
        rgba = cmap(normalized)

        # -----------------------------------------------------
        # Hacer transparentes los NoData

        rgba[data.mask] = [0, 0, 0, 0]

        # Convertir de 0-1 a 0-255
        rgba = (rgba * 255).astype(np.uint8)

        # Crear imagen RGBA
        image = Image.fromarray(rgba, mode="RGBA")

        # -----------------------------------------------------
        # Guardar imagen temporalmente en memoria

        buffer = BytesIO()

        image.save(
            buffer,
            format="PNG"
        )

        encoded = base64.b64encode(
            buffer.getvalue()
        ).decode()

        image_url = f"data:image/png;base64,{encoded}"

        return image_url, bounds
# ---------------------------------------------------------
#  Probamos una sola imagen
# raster_path = MAPS_DIR / "ET_PM2.5_M_02-2024_BA_V1.1.tif"

# image_url, bounds = raster_to_image(raster_path)
# # ---------------------------------------------------------
# Crear aplicación Dash

app = Dash(__name__)


# ---------------------------------------------------------
# Layout
primer_mapa = catalogo.iloc[0]

bounds_iniciales = [
    [primer_mapa["bottom"], primer_mapa["left"]],
    [primer_mapa["top"], primer_mapa["right"]]
]

centro_inicial = [
    (primer_mapa["top"] + primer_mapa["bottom"]) / 2,
    (primer_mapa["left"] + primer_mapa["right"]) / 2
]


app.layout = html.Div([

    html.H1("Visualizador de concentraciones de PM2.5"),

    html.P(
        "Exploración de concentraciones mensuales de PM2.5 "
        "en cinco centros urbanos de América Latina."
    ),

    html.H3("Seleccionar mapa"),


    html.Label("Ciudad"),

    dcc.Dropdown(
        id="ciudad-dropdown",
        options=[
            {"label": ciudad, "value": ciudad}
            for ciudad in ciudades
        ],
        value=ciudades[0],
        style={"width": "300px"}
    ),

    html.Label("Año"),

    dcc.Dropdown(
        id="anio-dropdown",
        options=[
            {"label": anio, "value": anio}
            for anio in anios
        ],
        value=anios[-1],
        style={"width": "300px"}
    ),

    html.Label("Mes"),

    dcc.Dropdown(
        id="mes-dropdown",
        options=[
            {"label": mes, "value": mes}
            for mes in meses
        ],
        value=meses[0],
        style={"width": "300px"}
    ),

    html.Br(),

    html.H3("Mapa de PM2.5"),

   html.Div(

    [

        dl.Map(
            id="mapa",

            children=[

                dl.TileLayer(),

                dl.ImageOverlay(
                    id="raster-overlay",
                    url="",
                    bounds=bounds_iniciales,
                    opacity=0.7,
                    interactive=True
                )

            ],

            center=centro_inicial,
            zoom=10,

            style={
                "width": "100%",
                "height": "700px"
            }
        ),

        # -------------------------------------------------
        # Leyenda

        html.Div(

            [

                html.Div(
                    "PM2.5 (µg/m³)",
                    style={
                        "fontWeight": "bold",
                        "marginBottom": "6px"
                    }
                ),

                html.Div(
                    style={
                        "width": "220px",
                        "height": "15px",
                        "background": (
                            "linear-gradient("
                            "to right, "
                            "#1a9850, "
                            "#ffffbf, "
                            "#FF8000, "
                            "#d73027, "
                            "#8B00FF"
                            ")"
                        )
                    }
                ),

                html.Div(

                    [
                        html.Span("0"),
                        html.Span("15"),
                        html.Span("30"),
                        html.Span("45"),
                        html.Span("60+")
                    ],

                    style={
                        "width": "220px",
                        "display": "flex",
                        "justifyContent": "space-between",
                        "fontSize": "12px"
                    }
                )

            ],

            style={
                "position": "absolute",
                "bottom": "20px",
                "right": "20px",
                "backgroundColor": "white",
                "padding": "10px",
                "borderRadius": "5px",
                "boxShadow": "0 1px 5px rgba(0,0,0,0.3)",
                "zIndex": "1000"
            }
        )

    ],

    style={
        "position": "relative"
    }
),
    html.H3("Información del píxel seleccionado"),

    html.Div(
    "Hacé click sobre el mapa para consultar el valor.",
    id="pixel-info"
)

])

@app.callback(
    Output("raster-overlay", "url"),
    Output("raster-overlay", "bounds"),
    Output("mapa", "center"),
    Input("ciudad-dropdown", "value"),
    Input("anio-dropdown", "value"),
    Input("mes-dropdown", "value")
)
def actualizar_mapa(ciudad, anio, mes):

    registro = catalogo[
        (catalogo["ciudad"] == ciudad) &
        (catalogo["anio"] == anio) &
        (catalogo["mes"] == mes)
    ]

    if registro.empty:
        return None, None, [0, 0]

    registro = registro.iloc[0]

    raster_path = registro["archivo"]

    image_url, bounds = raster_to_image(raster_path)

    center = [
        (bounds.top + bounds.bottom) / 2,
        (bounds.left + bounds.right) / 2
    ]

    return (
        image_url,
        [
            [bounds.bottom, bounds.left],
            [bounds.top, bounds.right]
        ],
        center
    )



# ---------------------------------------------------------
# Callback para consultar el píxel

# @app.callback(
#     Output("pixel-info", "children"),
#     Input("mapa", "clickData"),
#     State("ciudad-dropdown", "value"),
#     State("anio-dropdown", "value"),
#     State("mes-dropdown", "value")
# )

@app.callback(
    Output("pixel-info", "children"),
    Input("mapa", "clickData"),
    State("ciudad-dropdown", "value"),
    State("anio-dropdown", "value"),
    State("mes-dropdown", "value")
)
def mostrar_pixel(click, ciudad, anio, mes):

    if click is None:
        return "Hacé click sobre el mapa para consultar el valor."

    # Obtener coordenadas del click
    lat = click["latlng"]["lat"]
    lon = click["latlng"]["lng"]

    # Buscar el raster correspondiente
    registro = catalogo[
        (catalogo["ciudad"] == ciudad) &
        (catalogo["anio"] == anio) &
        (catalogo["mes"] == mes)
    ]

    if registro.empty:
        return "No se encontró el mapa seleccionado."

    registro = registro.iloc[0]
    raster_path = registro["archivo"]

    # Consultar el valor del píxel
    with rasterio.open(raster_path) as src:

        valor = list(
            src.sample([(lon, lat)])
        )[0][0]

        # Comprobar NoData
        if src.nodata is not None and valor == src.nodata:
            return html.Div([
                html.P(f"Ciudad: {ciudad}"),
                html.P(f"Año: {anio}"),
                html.P(f"Mes: {mes}"),
                html.P("Sin datos en este punto.")
            ])

    # Mostrar información
    return html.Div([
        html.P(f"Ciudad: {ciudad}"),
        html.P(f"Año: {anio}"),
        html.P(f"Mes: {mes}"),
        html.P(f"PM2.5: {valor:.2f} µg/m³"),
        html.P(f"Latitud: {lat:.4f}"),
        html.P(f"Longitud: {lon:.4f}")
    ])


# ---------------------------------------------------------
# Ejecutar aplicación

if __name__ == "__main__":
    app.run(debug=True)