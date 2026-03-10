"""
extractor.py
------------
Lee planillas Excel de la IE y extrae únicamente:
  - Grado, Curso, Período, Estudiante, Asignatura, Nota Definitiva, Indicador de Desempeño

Uso directo:
    python extractor.py --input data/planilla.xlsx --periodo "P4 - 2025"
"""

import re
import argparse
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


# ── Modelo de datos ────────────────────────────────────────────────────────────

@dataclass
class RegistroNota:
    grado: str
    curso: str
    periodo: str
    estudiante: str
    asignatura: str
    nota_definitiva: int
    indicador_desempeno: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


# ── Columnas clave del Excel ───────────────────────────────────────────────────

COL_NUMERO      = 0   # Número de lista del estudiante
COL_NOMBRE      = 1   # Apellidos y nombres
COL_ASIGNATURA  = 0   # Celda de encabezado: "ASIGNATURA: <nombre>"
COL_CURSO       = 17  # Celda de encabezado: "CURSO: X.XX"
COL_DOCENTE     = 9   # Celda de encabezado: "DOCENTE: <nombre>"
COL_NOTA_DEF    = 21  # Nota definitiva del período (DEF PER I)
COL_INDICADOR   = 17  # Indicador de desempeño en fila de estudiante


# ── Funciones de limpieza ──────────────────────────────────────────────────────

def limpiar_asignatura(texto: str) -> str:
    """Extrae el nombre de la asignatura del texto 'ASIGNATURA: <nombre>'."""
    match = re.search(r'ASIGNATURA:\s*([^\n\r]*)', str(texto))
    if not match:
        return "No especificada"
    nombre = match.group(1).strip()
    nombre = re.sub(r'PERÍODO:.*', '', nombre).strip()
    return nombre if nombre else "No especificada"


def limpiar_curso(texto: str) -> str:
    """Extrae el código de curso del texto 'CURSO: X.XX'."""
    return re.sub(r'CURSO:\s*', '', str(texto)).strip().replace(' ', '')


def es_fila_estudiante(row: pd.Series) -> bool:
    """Devuelve True si la fila corresponde a un estudiante (col 0 es número, col 1 es nombre)."""
    num = row[COL_NUMERO]
    nombre = row[COL_NOMBRE]
    if pd.isna(num) or pd.isna(nombre):
        return False
    if not isinstance(num, (int, float)):
        return False
    return str(nombre).strip() != ''


def es_fila_bloque(row: pd.Series) -> bool:
    """Devuelve True si la fila es encabezado de un nuevo bloque (contiene 'ASIGNATURA')."""
    return 'ASIGNATURA' in str(row[COL_ASIGNATURA])


# ── Extractor principal ────────────────────────────────────────────────────────

def extraer_hoja(df: pd.DataFrame, grado: str, periodo: str) -> list[RegistroNota]:
    """Procesa una hoja del Excel y retorna lista de RegistroNota."""
    registros = []

    # Detectar inicio de cada bloque
    filas_bloque = [i for i, row in df.iterrows() if es_fila_bloque(row)]
    filas_bloque.append(len(df))  # sentinel de fin

    for idx, inicio in enumerate(filas_bloque[:-1]):
        fin = filas_bloque[idx + 1]
        bloque = df.iloc[inicio:fin]
        cabecera = bloque.iloc[0]

        # Metadatos del bloque
        asignatura = limpiar_asignatura(cabecera[COL_ASIGNATURA])
        curso      = limpiar_curso(cabecera[COL_CURSO]) if not pd.isna(cabecera[COL_CURSO]) else "—"

        # Iterar estudiantes del bloque
        for _, row in bloque.iterrows():
            if not es_fila_estudiante(row):
                continue

            nota_raw = row[COL_NOTA_DEF]
            if pd.isna(nota_raw):
                continue  # sin nota → omitir

            ind_raw = str(row[COL_INDICADOR]).strip()
            indicador = ind_raw if ind_raw not in ('nan', 'None', '') else None

            registros.append(RegistroNota(
                grado               = grado,
                curso               = curso,
                periodo             = periodo,
                estudiante          = str(row[COL_NOMBRE]).strip(),
                asignatura          = asignatura,
                nota_definitiva     = round(float(nota_raw)),
                indicador_desempeno = indicador,
            ))

    return registros


def extraer_planilla(ruta: str, periodo: str = "P4 - 2025") -> list[RegistroNota]:
    """
    Lee todas las hojas del Excel y retorna lista completa de RegistroNota.

    Args:
        ruta:    Ruta al archivo .xlsx
        periodo: Etiqueta del período académico

    Returns:
        Lista de RegistroNota con solo los datos necesarios
    """
    path = Path(ruta)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    xl = pd.ExcelFile(ruta)
    todos = []

    for hoja in xl.sheet_names:
        df = pd.read_excel(ruta, sheet_name=hoja, header=None)
        registros = extraer_hoja(df, grado=hoja.strip(), periodo=periodo)
        todos.extend(registros)
        print(f"  [{hoja}] → {len(registros)} registros")

    print(f"\n✓ Total extraído: {len(todos)} registros con nota")
    return todos


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extractor de notas IE")
    parser.add_argument("--input",   default="data/PLANILLAS_CUARTO__PERIODO_2025.xlsx")
    parser.add_argument("--periodo", default="P4 - 2025")
    parser.add_argument("--output",  default="exports/notas.json")
    args = parser.parse_args()

    import json
    registros = extraer_planilla(args.input, args.periodo)
    datos = [r.to_dict() for r in registros]

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"periodo": args.periodo, "total": len(datos), "datos": datos},
                  f, ensure_ascii=False, indent=2)
    print(f"✓ Exportado → {args.output}")
