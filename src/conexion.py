
# Objetivo:setear las variables de entorno
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

#Variables de entorno
load_dotenv()
usuario = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
puerto = os.getenv("DB_PORT")
base = os.getenv("DB_NAME")

#Conexion
engine = create_engine(f"postgresql://{usuario}:{password}@{host}:{puerto}/{base}")