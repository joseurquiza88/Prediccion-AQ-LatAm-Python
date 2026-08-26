# Librerias
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
import plotly.express as px

# Notas
# dcc.Dropdown → menú desplegable
# dcc.Graph → gráficos interactivos de Plotly
# dcc.Slider → barra deslizante
# dcc.Input → campo para ingresar datos
# dcc.Checklist → casillas de selección
# dcc.RadioItems → botones de opción
# dcc.DatePickerSingle → selector de fecha
# State lee el valor actual de un componente sin disparar el callback cuando ese valor cambia.
# ---------------------------------------------------------
# Directorio principal del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------
# Carpeta donde estan los archivos tiff con los mapas
MAPS_DIR = ROOT_DIR / "data" / "processed" / "maps"

# ---------------------------------------------------------
# Buscar los tifs
tif_files = list(MAPS_DIR.glob("*.tif"))

# ---------------------------------------------------------
# Nombres completos de las ciudades
nombres_ciudades = { "BA": "Buenos Aires", "MD": "Medellín", "MX": "Ciudad de México", "SP": "São Paulo","ST": "Santiago"}
# ---------------------------------------------------------
# Funcion para crear un catalogo con los datos. 
# Cata archivo en el nombre muestra Ciudad, Mes, Año, Tipo de modelo construido (no es de interes para la visualizaion)
def crear_catalogo(tif_files):
    registros = []
    patron = r"^([A-Za-z]+)_PM2\.5_M_(\d{2})-(\d{4})_([A-Za-z]{2})_V1\.1\.tif$"

    for archivo in tif_files:
        match = re.match(patron, archivo.name)
        if not match:
            print(f"No se pudo interpretar: {archivo.name}")
            continue

        modelo = match.group(1) # No es de interes acxa
        mes = int(match.group(2))
        anio = int(match.group(3))
        ciudad = match.group(4)
        nombre_ciudad = nombres_ciudades.get(ciudad, ciudad)
        #Abrir archivo espacial
        with rasterio.open(archivo) as src:
            bbox = src.bounds
            registros.append({
                "modelo": modelo,
                "mes": mes,
                "anio": anio,
                "ciudad": nombre_ciudad, #ciudad,
                "archivo": archivo,
                "left": bbox.left,
                "bottom": bbox.bottom,
                "right": bbox.right,
                "top": bbox.top})
    return pd.DataFrame(registros)


# ---------------------------------------------------------
# Se usa la funcion para crear el catalogo
catalogo = crear_catalogo(tif_files)
#Tomamos la info
ciudades = sorted(catalogo["ciudad"].unique())
anios = sorted(catalogo["anio"].unique())
meses = sorted(catalogo["mes"].unique())

# ---------------------------------------------------------
# Se revisa la info
# print(f"Cantidad de mapas: {len(catalogo)}")
# print("Ciudades:", ciudades)
# print("Años:", anios)
# print("Meses:", meses)


# ---------------------------------------------------------
# Funcion para crear y leer el raster 

def raster_to_image(raster_path):
    with rasterio.open(raster_path) as src:
        data = src.read(1, masked=True)
        bounds = src.bounds
        # Se setean la escala de colores PM2.5 (propia similar a OMS)
        # Como no son mapas anuales, son mensuales no se puede mostrar de la misma forma
        colores = ["#1a9850", "#ffffbf", "#FF8000", "#d73027","#8B00FF"]

        cmap = LinearSegmentedColormap.from_list("pm25", colores)

        # -------------------------------------------------
        # Se esperan tener valor max de 60 ug/m3. 
        # Pero para la paleta de matplitib se esperan valores entre 0-1
        # Porlo que se "normalizar" entre 0 y 60

        data_clip = np.clip(data, 0, 60)
        normalized = data_clip / 60
        rgba = cmap(normalized)

        # Cuando no hay info queda transparente (RGBA=0)
        rgba[data.mask] = [ 0,  0, 0,  0]
        rgba = (rgba * 255).astype(np.uint8)
        image = Image.fromarray(rgba, mode="RGBA")

        # Imagen inicial mostrada en dash con encoded
        buffer = BytesIO() #Converir la imagen tif en un oobjeto que muestre dash
        image.save(buffer,format="PNG") # se guarda temporalmente aca
        encoded = base64.b64encode(buffer.getvalue()).decode() #obtiene los bytes de la imagen original y lo convierte en un texto para despues mostrarlo
        image_url = ("data:image/png;base64,"+ encoded )
        return image_url, bounds

# ---------------------------------------------------------
# Funcion para calcular promedio de toda la ciudad para cada archivo (mes- año)
def calcular_promedio_raster(raster_path):
    with rasterio.open(raster_path) as src:
        data = src.read(1, masked=True)
        promedio = round(data.mean(),2)
    return float(promedio)

# ---------------------------------------------------------
# Funcion para crear serie temporal por mes 

def crear_serie_temporal(catalogo):
    registros = []
    for _, fila in catalogo.iterrows():
        promedio = calcular_promedio_raster(fila["archivo"])
        registros.append({
            "ciudad": fila["ciudad"],
            "anio": fila["anio"],
            "mes": fila["mes"],
            "pm25_promedio": promedio })

    serie = pd.DataFrame(registros)

    # Como se obtienen los datos del nombre del archivo, se ordenan mal
    # Hay que ordenarlo cronologicamente
    serie = serie.sort_values(["ciudad", "anio", "mes"]).reset_index( drop=True)
    return serie


# Construccion de la serie temporal
TEMPORAL_DIR = ( ROOT_DIR/ "data"  / "processed" / "temporal")
TEMPORAL_DIR.mkdir(parents=True,  exist_ok=True)
# Lo modifique a mano ojo!!!
TEMPORAL_FILE = (TEMPORAL_DIR    / "pm25_temporal.csv")

if TEMPORAL_FILE.exists():
    # print("Leyendo serie temporal existente..." )
    serie_temporal = pd.read_csv(TEMPORAL_FILE, encoding="latin1")
else:
    print("Creando serie temporal a partir de los TIFF...")
    serie_temporal = crear_serie_temporal(catalogo)
    serie_temporal.to_csv(TEMPORAL_FILE, index=False)

print("\n--- Serie temporal ---")
print(serie_temporal.head())

print( "\nCantidad de registros:", len(serie_temporal))

# ---------------------------------------------------------
# Crear app con dash
app = Dash(__name__)

# ---------------------------------------------------------
# Setear estilo general CSS
ESTILO_FONDO = {"backgroundColor": "#f5f6f8", 
    "minHeight": "100vh",
    "fontFamily": "Arial, sans-serif",
    "color": "#263238",
    "padding": "25px 40px"}

ESTILO_TARJETA = {"backgroundColor": "white",
    "borderRadius": "10px",
    "padding":"20px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.08)"}

ESTILO_LABEL = {"fontSize": "14px",
    "fontWeight": "600",
    "marginBottom":"6px",
    "display": "block"}

# ---------------------------------------------------------
# Mapa inicial
primer_mapa = catalogo.iloc[0]

bounds_iniciales = [[ primer_mapa["bottom"], primer_mapa["left"]],
    [primer_mapa["top"],  primer_mapa["right"]]]

centro_inicial = [(primer_mapa["top"]  + primer_mapa["bottom"]) / 2,
    (primer_mapa["left"]  +  primer_mapa["right"]) / 2]

# ---------------------------------------------------------
# Layout general (html)
app.layout = html.Div([

    # Encabezado
    html.Div([
        html.H1("Visualizador de concentraciones de PM2.5", style={"fontSize": "30px","fontWeight": "600","marginBottom": "5px", "color": "#263238"}),
        html.P("Exploración de concentraciones mensuales de PM2.5en cinco centros urbanos de América Latina.",
            style={"fontSize": "15px","color": "#607d8b", "marginTop": "0px" })],
    style={"marginBottom": "20px"}),

# ---------------------------------------------------------
# Fltros a la izquierda
    html.Div([html.Div([html.H3("Selección",style={"fontSize": "18px","marginTop": "0px","marginBottom": "20px"}),
    # Ciudad
        html.Label("Ciudad", style=ESTILO_LABEL), 
        dcc.Dropdown(id="ciudad-dropdown",
                     options=[{"label": ciudad,"value": ciudad}
                              for ciudad in ciudades], value=ciudades[0],clearable=False, style={"fontSize": "14px", "marginBottom": "20px"}),

    #Año
        html.Label("Año", style=ESTILO_LABEL), dcc.Dropdown(id="anio-dropdown", options=[
                    {"label": anio, "value": anio}
                    for anio in anios ],
                    value=anios[-1], clearable=False, style={"fontSize": "14px","marginBottom": "20px"}),
    #Mes
            html.Label("Mes",style=ESTILO_LABEL), dcc.Dropdown(id="mes-dropdown",
                options=[{ "label": mes, "value": mes}
                    for mes in meses],
                value=meses[0], clearable=False, style={
                    "fontSize": "14px", "marginBottom": "20px"}),
            html.Hr(style={"border": "none","borderTop":"1px solid #e0e0e0","margin":"25px 0"}),

    #Texto comentario
            html.P("Hacé click sobre el mapa para "
                "seleccionar un píxel y consultar "
                "su evolución temporal.",style={"fontSize": "13px","lineHeight": "1.5","color": "#78909c"})],
        style={**ESTILO_TARJETA, "width": "220px", "minWidth": "220px", "height": "fit-content"}),

# ---------------------------------------------------------
# Mapa en el sector derecho
        html.Div([html.H3("Mapa de concentraciones mensuales de PM2.5 (ug/m3)",
                style={"fontSize": "18px", "marginTop": "0px","marginBottom": "12px"} ),
            html.Div([dl.Map(id="mapa", children=[
                        dl.TileLayer(),
                        dl.ImageOverlay(id="raster-overlay", url="", bounds=bounds_iniciales, opacity=0.7,interactive=True),
                        # Marcador del pixel
                        dl.CircleMarker(id="pixel-marker",center=centro_inicial, radius=9,color="#000000",fillColor="#ffffff",fillOpacity=0.5, weight=2)],
                    center=centro_inicial, zoom=11, style={ "width": "100%", "height": "500px","borderRadius": "8px"}),

# ---------------------------------------------------------
# Informacion del pixel
                html.Div(id="pixel-info", children=[ 
                    html.P("Hacé click sobre el mapa",style={"margin": "0","fontWeight":"600"}),
                    html.P("para consultar el valor.", style={"margin":"4px 0 0 0", "fontSize":"12px"})],
                    style={"position":"absolute", "top":"15px", 
                           "right":"15px", "backgroundColor":"rgba(255,255,255,0.95)",
                           "padding":"12px 15px", "borderRadius":"8px",
                           "boxShadow":"0 2px 8px rgba(0,0,0,0.2)", "zIndex":"1000",
                        "fontSize":"13px","minWidth":"180px"}),
# ---------------------------------------------------------
# Leyenda 
        html.Div([html.Div("PM2.5 (µg/m³)", style={"fontWeight":"600","fontSize":"12px","marginBottom":"5px"}),
                        html.Div( style={ "width":"190px","height":"12px","background":"linear-gradient("
                                    "to right,"
                                    "#1a9850," "#ffffbf,"
                                    "#FF8000,"
                                    "#d73027,"
                                    "#8B00FF"
                                    ")", "borderRadius":"3px"}),
                        html.Div([html.Span("0"), html.Span("15"),html.Span("30"),html.Span("45"),html.Span("60+")],
                            style={"width":"190px","display":"flex","justifyContent":"space-between", "fontSize":"10px",
                                "marginTop":"3px"})],
                    style={"position": "absolute", "bottom":"15px", "right":"15px","backgroundColor":
                            "rgba(255,255,255,0.95)", "padding":"10px","borderRadius": "7px",
                        "boxShadow": "0 2px 8px rgba(0,0,0,0.2)", "zIndex": "1000"})
            ], style={"position": "relative"})],

        style={ **ESTILO_TARJETA, "flex": "1", "minWidth": "0"})
        ],

    style={"display": "flex", "gap": "20px", "alignItems":"flex-start","marginBottom":"20px"}),

# ---------------------------------------------------------
# Series temporales

    html.Div([html.H3("Evolución mensual", style={ "fontSize": "18px","marginTop": "0px","marginBottom": "15px"}),
        html.Div([
# ---------------------------------------------------------
#   Promedio por ciudad
            html.Div([dcc.Graph(id= "serie-temporal-ciudad",
                    config={"displayModeBar": False}, style={"height":"330px"})],
            style={**ESTILO_TARJETA, "flex": "1", "padding": "10px"}),

# ---------------------------------------------------------
#   Promedio pixel
            html.Div([dcc.Graph(id="serie-temporal-pixel",
                    config={"displayModeBar":False},
                    style={"height":"330px"})],
            style={**ESTILO_TARJETA,
                "flex": "1",
                "padding": "10px"})],
        style={"display":"flex", "gap":"20px"})
    ],
    style={"marginBottom":"20px"})], style=ESTILO_FONDO)


# ---------------------------------------------------------
# CALLBACK para actualizar el mapa
# callback: funcion que se ejecuta automáicamente cuando cambia algo en el dashboard.
@app.callback(
    Output("raster-overlay","url"), # cambia el mapa/imagen
    Output("raster-overlay","bounds"), #cambia los limites porque es otra ciuda
    Output("mapa","center"), # el centro de la imagen
    # Cambia  por tres razones: por cambiar la ciudad en el selector, el año o el mes
    Input("ciudad-dropdown","value"),
    Input("anio-dropdown","value"),
    Input("mes-dropdown", "value"))
# ---------------------------------------------------------
#Funcion cambiar mapa
def actualizar_mapa(ciudad, anio,mes):
    # Me quedo con el registro segun lo que se selecciono en los seleccionadores
    registro = catalogo[(catalogo["ciudad"] == ciudad)   &  (catalogo["anio"] == anio) & (catalogo["mes"] == mes)]
    if registro.empty:
        return (None, None, [0, 0] )
    registro = registro.iloc[0]
    raster_path = registro["archivo"]
    # Se busca la url y lo limites segun lo ingreso
    image_url, bounds = (raster_to_image(raster_path))
    center = [( bounds.top + bounds.bottom ) / 2,(bounds.left+bounds.right ) / 2]
    return ( image_url, [[bounds.bottom, bounds.left],[bounds.top,bounds.right]],center)

# # ---------------------------------------------------------
# Callback para calcular los datos por pixel

@app.callback(
    Output("pixel-info","children"),
    Output("pixel-marker", "center"),
    Input("mapa","clickData"),
    State("ciudad-dropdown","value"), # Dame el valor que tiene actualmente el selector de ciudad, pero no hagas que este callback se ejecute cuando cambie la ciudad.”
    State( "anio-dropdown", "value"),
    State("mes-dropdown", "value"))
# Funcion para mostrar la info del pixel 
def mostrar_pixel(click, ciudad, anio,mes):
    # Si no se  hizo click por defecto queda el mensaje
    if click is None:
        return (html.Div([html.P("Hacé click sobre el mapa",
                    style={"margin": "0","fontWeight":"600" }),
                html.P("para consultar el valor.",
                       style={"margin":"4px 0 0 0", "fontSize": "12px"})]),
            centro_inicial # el centro del marcador del pixel esta en el medio
        )

    # Coordenadas

    lat = click["latlng"]["lat"]
    lon = click["latlng"]["lng"]

    # Buscar raster
    registro = catalogo[ (catalogo["ciudad"] == ciudad) & (catalogo["anio"] == anio) & (catalogo["mes"] == mes)]
    if registro.empty:
        return ("No se encontró el mapa seleccionado.", [lat, lon])
    registro = registro.iloc[0]
    raster_path = registro["archivo"]

    # -----------------------------------------------------
    # Abrir el raster y btener valor del pixel
    with rasterio.open(raster_path) as src:
        # Busca el valor para un punto dato con lat/long
        valor = list(src.sample([(lon, lat)] ))[0][0]

        # Si no hay datos en ese punto
        if (src.nodata is not None and valor == src.nodata):
            return (html.Div([html.P(f"Ciudad: {ciudad}"),
                    html.P(f"{anio} / {mes:02d}"),
                    html.P("Sin datos en este punto.")]),
                [lat, lon])

    # Si hay info, mostrar en un div ==> <p> es decir en un parrafo
    return (html.Div([html.P(f"Ciudad: {ciudad}", style={ "margin": "0 0 3px 0", "fontWeight": "600"}),
            html.P(f"{anio} / {mes:02d}", style={"margin": "0 0 5px 0", "color": "#607d8b" }),
            html.P( f"PM2.5: {valor:.2f} µg/m³", style={ "margin": "0 0 3px 0", "fontSize":"15px", "fontWeight":"600" }),
            html.P(f"Lat: {lat:.4f}", style={ "margin": "0", "fontSize": "11px"}),
            html.P(f"Lon: {lon:.4f}",style={"margin": "0", "fontSize": "11px"})]),
        [lat, lon])

# -----------------------------------------------------
# Callback de la serie de tiempo por ciudad
@app.callback(Output("serie-temporal-ciudad", "figure"),
    Input("ciudad-dropdown", "value"))

def actualizar_serie_temporal(ciudad):
    datos = serie_temporal[serie_temporal["ciudad"] == ciudad ].copy()

    # Crear fecha
    datos["fecha"] = pd.to_datetime(dict( year=datos["anio"], month=datos["mes"],day=1) )

    # Crear gráfico
    figura = px.line(datos, x="fecha", y="pm25_promedio", markers=True, labels={"fecha": "Mes",
            "pm25_promedio": "PM2.5 (µg/m³)"})

    # Estilo
    figura.update_layout(template="plotly_white", margin=dict( l=45, r=20, t=45, b=40),
        font=dict(family="Arial", size=11),
        title=dict( text="Promedio ciudad", font=dict(size=16 ),x=0.02 ),
        xaxis=dict( showgrid=True, gridcolor="#eeeeee"), yaxis=dict(showgrid=True, gridcolor="#eeeeee"))
    return figura

# -----------------------------------------------------
# Callback - Serie temporal por pixel, que es distinta a la de la ciudad
@app.callback( Output( "serie-temporal-pixel", "figure"),
    Input("mapa", "clickData"),
    Input( "ciudad-dropdown", "value"),
    Input( "anio-dropdown", "value"),
    Input( "mes-dropdown", "value"))
# -----------------------------------------------------
def actualizar_serie_pixel(click, ciudad, anio, mes):
    # Si todavía no hay click
    if click is None:
        figura = px.line( title="Promedio píxel")
        figura.update_layout(template="plotly_white", margin=dict(l=45, r=20, t=45, b=40),
            annotations=[dict(text="Hacé click sobre el mapa para seleccionar un píxel", xref="paper", yref="paper", x=0.5,
            y=0.5, showarrow=False)])
        return figura

    # Tomar las coordenadas al hacer click

    lat = click["latlng"]["lat"]
    lon = click[ "latlng"]["lng"]

    print( "Click para serie temporal:", lat, lon)
    # Buscar mapas de la ciudad


    registros = catalogo[catalogo["ciudad"]== ciudad].copy()
    datos_pixel = []

    # Obtener valor del mismo píxel en todos los meses para poder hacer esta serie temporal

    for _, registro in registros.iterrows():
        raster_path = registro["archivo"]
        with rasterio.open( raster_path ) as src:
            valor = list(src.sample([(lon, lat)]))[0][0]

            # Ignorar NoData
            if (src.nodata is not None and valor == src.nodata):
                continue
            # Ignorar NaN. No deberia haber nans igual
            if np.isnan(valor):
                continue
            datos_pixel.append({
                "anio": registro["anio"],
                "mes": registro["mes"], 
                "pm25_pixel": float(valor) })
# Dataframe con la info para visualizarla
    datos_pixel = pd.DataFrame(datos_pixel)
    # Si no hay datos
    if datos_pixel.empty: 
        figura = px.line(title="Promedio píxel - Sin datos")
        figura.update_layout( template="plotly_white")
        return figura

    # Crear fecha
    datos_pixel["fecha"] = pd.to_datetime(dict(year=datos_pixel["anio"], month=datos_pixel["mes"], day=1))
    # Por las dudas los ordeno a parte en orden cronológico
    datos_pixel = datos_pixel.sort_values("fecha")

    # Crear gráfico
    figura = px.line(datos_pixel, "fecha",  y="pm25_pixel", markers=True,
                     labels={ "fecha": "Mes", "pm25_pixel": "PM2.5 Mensual (µg/m³)"})

    # Estilo
    figura.update_layout(template="plotly_white", 
                         margin=dict( l=45,r=20, t=45, b=40),font=dict(family="Arial", size=11),

        title=dict(text="Promedio píxel", font=dict( size=16), x=0.02),
        xaxis=dict( showgrid=True, gridcolor="#eeeeee"), yaxis=dict(showgrid=True,gridcolor="#eeeeee"))


    # Setear la misma escala para ambos graficos
    datos_ciudad = serie_temporal[serie_temporal["ciudad"] == ciudad ]["pm25_promedio"]
    valores = pd.concat([datos_ciudad, datos_pixel["pm25_pixel"]])
    ymin = valores.min()
    ymax = valores.max()
    margen = ( ymax - ymin) * 0.10
    if margen == 0:
        margen = 1
    figura.update_yaxes(range=[ ymin - margen, ymax + margen])
    return figura

# -----------------------------------------------------
# Ejecutar la app completa
if __name__ == "__main__":
    app.run(debug=True )