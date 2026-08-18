

# Se aplica el modelo a la fecha de interes, pero hay un lag minimo de 10 dias
# Librerias
from pathlib import Path
import joblib

# Setear informacion de entrada
ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT_DIR / "models"

#Funciones
def load_model(estacion):
    """
    Carga el modelo entrenado correspondiente a una estación.
    """
    model_path = MODEL_DIR / f"best_model_{estacion}.pkl"
    modelo = joblib.load(model_path)
    return modelo

def predict(modelo, X):
    """
    Genera predicciones utilizando el modelo cargado.
    """
    y_pred = modelo.predict(X)
    return y_pred


# ---------------------------------------------------------
# 1. Se abre AOD


# ---------------------------------------------------------
# 2. Se abre NDVI


# ---------------------------------------------------------
# 3. Se abre Variables metereologicas




# ---------------------------------------------------------
# 4. Se abre Composicion de aerosoles




# ---------------------------------------------------------
# 5. Se abre Elevacion



# ---------------------------------------------------------
# 6. Se abre Dia


# ---------------------------------------------------------
# Se genera un stack de datos


# ---------------------------------------------------------
# Se abre el modelo previamente entrenado y validado



# ---------------------------------------------------------
# Se aplica el modelo al stack de datos con todas las variables



# ---------------------------------------------------------
# Se guarda la imagen a nivel local