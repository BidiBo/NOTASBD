import os
import argparse
import uvicorn
import cv2
import easyocr
import json
import logging
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

# --- 1. Configuración de Carpetas y Entorno ---
CARPETA_LOGS = "[LOGS OCR]"
CARPETA_JPG = "JPG"
ARCHIVO_MEMORIA = "plantillas.json"

os.makedirs(CARPETA_LOGS, exist_ok=True)
os.makedirs(CARPETA_JPG, exist_ok=True)

# --- 2. Configuración del Logger ---
ARCHIVO_LOG = os.path.join(CARPETA_LOGS, "actividad_ocr.log")
logging.basicConfig(
    filename=ARCHIVO_LOG,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8"
)
logger = logging.getLogger("OCR_Logger")

app = FastAPI(title="Motor OCR - Middleware Automático")
logger.info("=== Servidor OCR Iniciado ===")
print("Cargando modelo de EasyOCR...")
reader = easyocr.Reader(['es'], gpu=False)

# --- 3. Modelos de Datos ---
class Region(BaseModel):
    nombre_columna: str
    x: int
    y: int
    w: int
    h: int
    allowlist: str = ""

class PlantillaEntrenamiento(BaseModel):
    cliente_id: str
    regiones: List[Region]

# --- 4. Funciones Core (Memoria y OCR) ---
def cargar_memoria():
    if not os.path.exists(ARCHIVO_MEMORIA):
        return {}
    with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_en_memoria(plantilla: PlantillaEntrenamiento):
    memoria = cargar_memoria()
    memoria[plantilla.cliente_id] = [region.dict() for region in plantilla.regiones]
    with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(memoria, f, indent=4)

def procesar_imagen_local(nombre_archivo, cliente_id):
    """Busca la imagen en la carpeta JPG y la procesa usando la memoria."""
    ruta_imagen = os.path.join(CARPETA_JPG, nombre_archivo)
    
    if not os.path.exists(ruta_imagen):
        return {"error": f"La imagen {nombre_archivo} no existe en la carpeta {CARPETA_JPG}."}

    memoria = cargar_memoria()
    if cliente_id not in memoria:
        return {"error": f"No hay memoria entrenada para el cliente: {cliente_id}"}

    plantilla = memoria[cliente_id]
    img = cv2.imread(ruta_imagen)
    if img is None:
        return {"error": "No se pudo decodificar la imagen. Verifica el formato."}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resultados_finales = {}

    for region in plantilla:
        x, y, w, h = region["x"], region["y"], region["w"], region["h"]
        allowlist = region["allowlist"]
        nombre_columna = region["nombre_columna"]

        roi = gray[y:y+h, x:x+w]
        
        if allowlist:
            lectura = reader.readtext(roi, allowlist=allowlist, detail=0)
        else:
            lectura = reader.readtext(roi, detail=0)
            
        resultados_finales[nombre_columna] = " ".join(lectura).strip()

    return {"status": "success", "archivo": nombre_archivo, "cliente": cliente_id, "data": resultados_finales}

# --- 5. Endpoints REST API ---
@app.post("/api/v1/entrenar-ocr")
def endpoint_entrenar_ocr(plantilla: PlantillaEntrenamiento):
    try:
        guardar_en_memoria(plantilla)
        logger.info(f"Éxito: Memoria actualizada para {plantilla.cliente_id}.")
        return {"status": "success", "mensaje": f"Memoria actualizada para {plantilla.cliente_id}"}
    except Exception as e:
        logger.error(f"Error al entrenar memoria: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/extraer-imagen")
def endpoint_extraer_imagen(nombre_archivo: str = Form(...), cliente_id: str = Form(...)):
    """Toma un nombre de archivo, lo busca en la carpeta JPG y lo procesa."""
    try:
        logger.info(f"Procesando {nombre_archivo} para el cliente {cliente_id}")
        resultado = procesar_imagen_local(nombre_archivo, cliente_id)
        
        if "error" in resultado:
            logger.warning(f"Error procesando {nombre_archivo}: {resultado['error']}")
            raise HTTPException(status_code=404, detail=resultado["error"])
        
        logger.info(f"Extracción exitosa para {nombre_archivo}.")
        return JSONResponse(content=resultado)
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/logs")
def obtener_logs(lineas: int = 50):
    if not os.path.exists(ARCHIVO_LOG):
        return {"status": "error", "mensaje": "Sin logs."}
    with open(ARCHIVO_LOG, "r", encoding="utf-8") as f:
        logs_limpios = [linea.strip() for linea in f.readlines()[-lineas:] if linea.strip()]
    return {"status": "success", "logs": logs_limpios}

# --- 6. Modo Consola (Procesamiento por Lotes) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Motor OCR Middleware.")
    parser.add_argument('--modo', choices=['api', 'cmd'], default='api')
    parser.add_argument('--cliente', type=str, help="ID del cliente para procesar la carpeta JPG entera en modo cmd.")
    args = parser.parse_args()

    if args.modo == 'api':
        print(f"Iniciando API en http://localhost:8000. Asegúrate de poner tus fotos en la carpeta '{CARPETA_JPG}'.")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    elif args.modo == 'cmd':
        if not args.cliente:
            print("Error: Debes indicar un --cliente para procesar la carpeta JPG.")
        else:
            imagenes = [f for f in os.listdir(CARPETA_JPG) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            print(f"Se encontraron {len(imagenes)} imágenes en la carpeta '{CARPETA_JPG}'. Iniciando lote...")
            logger.info(f"Inicio de procesamiento por lotes para cliente {args.cliente}. Total: {len(imagenes)}")
            
            for img_name in imagenes:
                res = procesar_imagen_local(img_name, args.cliente)
                if "error" in res:
                    print(f"[X] Error en {img_name}: {res['error']}")
                else:
                    print(f"[OK] {img_name} procesada. Datos: {res['data']}")