"""
resumen.py
----------
Genera un archivo TXT con el resumen del proceso académico
de todos los estudiantes extraídos de la planilla Excel.

Uso:
    python resumen.py
    python resumen.py --input data/planilla.xlsx --output exports/resumen.txt
"""

import argparse
from pathlib import Path
from datetime import datetime
from app.extractor import extraer_planilla


# ── Mensajes por indicador ─────────────────────────────────────────────────────

MENSAJES = {
    'SUPERIOR': 'APROBÓ con desempeño SUPERIOR',
    'ALTO':     'APROBÓ con desempeño ALTO',
    'BASICO':   'APROBÓ con desempeño BÁSICO',
    'BAJO':     'NO APROBÓ, desempeño BAJO',
    None:       'aprobó',
}


def generar_resumen(ruta_excel: str, ruta_salida: str, periodo: str = "P4 - 2025"):
    print(f"\n📄 Extrayendo datos de: {ruta_excel}")
    registros = extraer_planilla(ruta_excel, periodo)

    if not registros:
        print("⚠️  Sin registros para generar resumen.")
        return

    # ── Agrupar por grado y curso ──────────────────────────────────────────────
    grupos = {}
    for r in registros:
        clave = (r.grado, r.curso)
        if clave not in grupos:
            grupos[clave] = []
        grupos[clave].append(r)

    # ── Estadísticas globales ──────────────────────────────────────────────────
    total       = len(registros)
    aprobados   = sum(1 for r in registros if (r.indicador_desempeno or '') != 'BAJO')
    reprobados  = total - aprobados
    promedio    = round(sum(r.nota_definitiva for r in registros) / total)

    conteo_ind = {'SUPERIOR': 0, 'ALTO': 0, 'BASICO': 0, 'BAJO': 0}
    for r in registros:
        ind = (r.indicador_desempeno or '').upper()
        if ind in conteo_ind:
            conteo_ind[ind] += 1

    # ── Construir texto ────────────────────────────────────────────────────────
    lineas = []
    sep    = "=" * 70
    sep2   = "-" * 70

    # Encabezado
    lineas += [
        sep,
        "  RESUMEN ACADÉMICO — PROCESO DE ESTUDIANTES",
        f"  Período: {periodo}",
        f"  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sep,
        "",
        "ESTADÍSTICAS GENERALES",
        sep2,
        f"  Total estudiantes evaluados : {total}",
        f"  Aprobados                   : {aprobados}",
        f"  No aprobados (BAJO)         : {reprobados}",
        f"  Nota promedio general       : {promedio}",
        "",
        f"  Superior : {conteo_ind['SUPERIOR']} estudiantes",
        f"  Alto     : {conteo_ind['ALTO']} estudiantes",
        f"  Básico   : {conteo_ind['BASICO']} estudiantes",
        f"  Bajo     : {conteo_ind['BAJO']} estudiantes",
        "",
    ]

    # Detalle por grado y curso
    for (grado, curso), estudiantes in sorted(grupos.items()):
        prom_grupo = round(sum(e.nota_definitiva for e in estudiantes) / len(estudiantes))

        lineas += [
            sep,
            f"  GRADO {grado}  |  CURSO {curso}  |  {len(estudiantes)} estudiantes  |  Promedio: {prom_grupo}",
            sep,
            "",
        ]

        for e in estudiantes:
            ind = (e.indicador_desempeno or '').upper()
            mensaje = MENSAJES.get(ind, MENSAJES[None])
            estado  = "✓" if ind != 'BAJO' else "✗"

            lineas.append(
                f"  {estado}  {e.estudiante:<40}  Nota: {round(e.nota_definitiva):>3}  →  {mensaje}"
            )

        # Mini resumen del grupo
        apro_g = sum(1 for e in estudiantes if (e.indicador_desempeno or '') != 'BAJO')
        lineas += [
            "",
            f"     Aprobados: {apro_g}/{len(estudiantes)}  |  No aprobados: {len(estudiantes)-apro_g}/{len(estudiantes)}",
            "",
        ]

    # Pie
    lineas += [
        sep,
        "  FIN DEL INFORME",
        sep,
    ]

    # ── Guardar archivo ────────────────────────────────────────────────────────
    Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
    contenido = "\n".join(lineas)

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"\n✓ Resumen guardado en: {ruta_salida}")
    print(f"  {total} estudiantes  |  {aprobados} aprobados  |  {reprobados} no aprobados")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generador de resumen académico TXT")
    parser.add_argument("--input",   default="data/PLANILLAS_CUARTO__PERIODO_2025.xlsx")
    parser.add_argument("--output",  default="exports/resumen_academico.txt")
    parser.add_argument("--periodo", default="P4 - 2025")
    args = parser.parse_args()

    generar_resumen(args.input, args.output, args.periodo)
