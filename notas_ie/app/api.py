"""
api.py
------
API REST con FastAPI que sirve las notas filtradas al frontend / página IE.

Endpoints:
  GET /notas                  → Todas las notas (filtros opcionales)
  GET /notas/{grado}          → Notas de un grado
  GET /notas/{grado}/{curso}  → Notas de un curso específico
  GET /grados                 → Lista de grados disponibles
  GET /resumen                → Estadísticas generales
  POST /cargar                → Cargar nuevo archivo Excel

Iniciar:
    uvicorn app.api:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Optional
import shutil
import json

from app.extractor import extraer_planilla, RegistroNota
from resumen import generar_resumen

# ── Configuración ──────────────────────────────────────────────────────────────

DATA_DIR    = Path("data")
EXPORTS_DIR = Path("exports")
CACHE_FILE  = EXPORTS_DIR / "notas_cache.json"
PLANILLA    = DATA_DIR / "PLANILLAS_CUARTO__PERIODO_2025.xlsx"
PERIODO     = "P4 - 2025"

DATA_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="GestiónNotas IE — API",
    description="Intermediario de notas para Institución Educativa",
    version="1.0.0",
)

# Permitir peticiones desde el frontend (React/página IE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Cache en memoria ──────────────────────────────────────────────────────────

_cache: list[dict] = []


def cargar_cache():
    """Carga o regenera el cache de notas desde el Excel."""
    global _cache
    if CACHE_FILE.exists():
        with open(CACHE_FILE, encoding="utf-8") as f:
            _cache = json.load(f)["datos"]
        print(f"[cache] {len(_cache)} registros cargados desde cache")
    elif PLANILLA.exists():
        regenerar_cache()
    else:
        print("[cache] Sin archivo Excel disponible. Sube uno con POST /cargar")


def regenerar_cache(ruta: Path = PLANILLA, periodo: str = PERIODO):
    """Extrae las notas del Excel y guarda en cache JSON."""
    global _cache
    registros = extraer_planilla(str(ruta), periodo)
    _cache = [r.to_dict() for r in registros]
    EXPORTS_DIR.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"periodo": periodo, "total": len(_cache), "datos": _cache},
                  f, ensure_ascii=False, indent=2)
    print(f"[cache] {len(_cache)} registros guardados")


def filtrar(
    grado: Optional[str] = None,
    curso: Optional[str] = None,
    indicador: Optional[str] = None,
    nombre: Optional[str] = None,
) -> list[dict]:
    """Aplica filtros opcionales sobre el cache."""
    resultado = _cache
    if grado:
        resultado = [r for r in resultado if r["grado"] == grado]
    if curso:
        resultado = [r for r in resultado if r["curso"] == curso]
    if indicador:
        resultado = [r for r in resultado
                     if (r["indicador_desempeno"] or "").upper() == indicador.upper()]
    if nombre:
        resultado = [r for r in resultado
                     if nombre.lower() in r["estudiante"].lower()]
    return resultado


# ── Eventos ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    cargar_cache()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/", tags=["info"])
def root():
    return {
        "api": "GestiónNotas IE",
        "version": "1.0.0",
        "registros_en_cache": len(_cache),
        "endpoints": ["/notas", "/grados", "/resumen", "/cargar"],
    }


@app.get("/grados", tags=["consulta"])
def listar_grados():
    """Retorna los grados disponibles y cantidad de registros por grado."""
    conteo = {}
    for r in _cache:
        g = r["grado"]
        conteo[g] = conteo.get(g, 0) + 1
    return {"grados": conteo}


@app.get("/notas", tags=["consulta"])
def obtener_notas(
    grado:     Optional[str] = Query(None, description="Ej: 9°"),
    curso:     Optional[str] = Query(None, description="Ej: 9.01"),
    indicador: Optional[str] = Query(None, description="SUPERIOR | ALTO | BASICO | BAJO"),
    nombre:    Optional[str] = Query(None, description="Buscar por nombre parcial"),
):
    """
    Retorna notas filtradas. Todos los parámetros son opcionales y combinables.

    Ejemplos:
      /notas?grado=9°
      /notas?grado=9°&indicador=BAJO
      /notas?nombre=garcia
    """
    if not _cache:
        raise HTTPException(503, "Sin datos. Sube un archivo con POST /cargar")

    datos = filtrar(grado=grado, curso=curso, indicador=indicador, nombre=nombre)
    return {
        "total":   len(datos),
        "filtros": {"grado": grado, "curso": curso, "indicador": indicador, "nombre": nombre},
        "datos":   datos,
    }


@app.get("/notas/{grado}", tags=["consulta"])
def notas_por_grado(grado: str):
    """Retorna todas las notas de un grado. Ej: /notas/9°"""
    datos = filtrar(grado=grado)
    if not datos:
        raise HTTPException(404, f"No se encontraron registros para el grado '{grado}'")
    return {"grado": grado, "total": len(datos), "datos": datos}


@app.get("/notas/{grado}/{curso}", tags=["consulta"])
def notas_por_curso(grado: str, curso: str):
    """Retorna notas de un curso específico. Ej: /notas/9°/9.01"""
    datos = filtrar(grado=grado, curso=curso)
    if not datos:
        raise HTTPException(404, f"No se encontraron registros para {grado} / {curso}")
    return {"grado": grado, "curso": curso, "total": len(datos), "datos": datos}


@app.get("/resumen", tags=["estadísticas"])
def resumen():
    """Estadísticas generales: conteo por indicador, promedios por grado."""
    if not _cache:
        raise HTTPException(503, "Sin datos disponibles")

    # Por indicador
    por_indicador = {}
    for r in _cache:
        ind = r["indicador_desempeno"] or "Sin indicador"
        por_indicador[ind] = por_indicador.get(ind, 0) + 1

    # Promedio por grado
    promedios = {}
    for r in _cache:
        g = r["grado"]
        if g not in promedios:
            promedios[g] = []
        if r["nota_definitiva"] is not None:
            promedios[g].append(r["nota_definitiva"])

    promedios_calc = {
        g: round(sum(v) / len(v), 2)
        for g, v in promedios.items() if v
    }

    return {
        "total_registros":  len(_cache),
        "por_indicador":    por_indicador,
        "promedio_por_grado": promedios_calc,
    }


@app.post("/cargar", tags=["administración"])
async def cargar_planilla(
    archivo: UploadFile = File(...),
    periodo: str = Query(default="P4 - 2025", description="Etiqueta del período"),
):
    """
    Sube un nuevo archivo Excel (.xlsx) y regenera el cache de notas.
    Reemplaza los datos anteriores.
    """
    if not archivo.filename.endswith(".xlsx"):
        raise HTTPException(400, "Solo se aceptan archivos .xlsx")

    ruta_destino = DATA_DIR / archivo.filename
    with open(ruta_destino, "wb") as f:
        shutil.copyfileobj(archivo.file, f)

    try:
        regenerar_cache(ruta=ruta_destino, periodo=periodo)
        generar_resumen(str(ruta_destino), str(EXPORTS_DIR / "resumen_academico.txt"), periodo)
    except Exception as e:
        raise HTTPException(500, f"Error procesando el archivo: {e}")

    return {
        "mensaje":  "Archivo procesado correctamente",
        "archivo":  archivo.filename,
        "periodo":  periodo,
        "registros_cargados": len(_cache),
    }


@app.delete("/cache", tags=["administración"])
def limpiar_cache():
    """Elimina el cache. Los datos se regeneran al reiniciar o al subir un nuevo archivo."""
    global _cache
    _cache = []
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
    return {"mensaje": "Cache eliminado"}
