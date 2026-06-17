"""
3_construir_documento_final_ordenado.py
────────────────────────────────────────
PASO 3 del flujo.

Genera UN SOLO JSON unificado con:
  • Texto (heading/paragraph/list) limpio, sin duplicados de tablas
  • Tablas con id canónico T{pagina}_{numero}
  • TODO ordenado por POSICIÓN VISUAL REAL en la página (bounding box),
    no por orden de extracción.

Por qué este enfoque resuelve el problema:
─────────────────────────────────────────
- opendataloader_pdf da a cada heading/paragraph/list una "bounding box"
  en coordenadas PDF (origen abajo-izquierda, Y crece hacia ARRIBA).
- pdfplumber (find_tables) da a cada tabla un bbox en SU propio sistema
  (origen arriba-izquierda, "top" crece hacia ABAJO).
- Convirtiendo el bbox de la tabla a coordenadas PDF:
        y1_tabla = page_height - bbox.top   (borde superior de la tabla)
  podemos comparar directamente la posición vertical de tablas y texto.
- Ordenando cada página por Y descendente (de arriba hacia abajo)
  obtenemos el ORDEN DE LECTURA REAL del PDF, sin importar si el
  elemento es texto o tabla.

Esto es exactamente lo que muestra el ejemplo de la página 16/28:
la tabla de "Horas de trabajo: (Totales del bimestre)" tiene su borde
superior justo DEBAJO del heading y ENCIMA del párrafo "Fechas
importantes:", así que ahora queda intercalada correctamente.
"""

import json
import pdfplumber

from _detectar_pdf import detectar_pdf


PDF_PATH = detectar_pdf()
print(f"PDF detectado: {PDF_PATH}")


# ══════════════════════════════════════════════════════════
#  PASO 1 — Re-extraer tablas CON bounding box + limpieza
#           (misma limpieza que 3limpiarColumnasVacias.py:
#            quita celdas vacías y renumera columnas)
# ══════════════════════════════════════════════════════════

tablas_con_bbox = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_idx, page in enumerate(pdf.pages, start=1):

        encontradas = page.find_tables()

        for table_idx, tabla in enumerate(encontradas, start=1):

            x0, top, x1, bottom = tabla.bbox
            y1_pdf = page.height - top      # borde superior en coords PDF
            y0_pdf = page.height - bottom   # borde inferior en coords PDF

            filas_raw = tabla.extract()
            filas_limpias = []

            for fila_num, fila in enumerate(filas_raw, start=1):
                celdas = []
                for valor in fila:
                    contenido = str(valor).strip() if valor else ""
                    if contenido:
                        celdas.append(contenido)

                # renumerar columnas tras quitar vacías
                celdas_obj = [
                    {"column_number": i, "content": c}
                    for i, c in enumerate(celdas, start=1)
                ]

                if celdas_obj:
                    filas_limpias.append({
                        "row_number": fila_num,
                        "cells": celdas_obj
                    })

            tablas_con_bbox.append({
                "type":         "table",
                "id":           f"T{page_idx}_{table_idx}",
                "page_number":  page_idx,
                "table_number": table_idx,
                "y_top":        y1_pdf,
                "y_bottom":     y0_pdf,
                "x0":           x0,
                "rows":         filas_limpias
            })

print(f"Tablas re-extraídas con bbox: {len(tablas_con_bbox)}")


# ══════════════════════════════════════════════════════════
#  PASO 2 — Cargar texto (heading/paragraph/list)
# ══════════════════════════════════════════════════════════

with open("JSONObtenidos/contenido_sin_tablasPDF2.json", "r", encoding="utf-8") as f:
    contenido = json.load(f)

elementos_texto = contenido["kids"]
print(f"Elementos de texto cargados: {len(elementos_texto)}")


# ══════════════════════════════════════════════════════════
#  PASO 3 — Detección de duplicados (texto que en realidad
#           es contenido de una tabla en la misma página)
#           Igual criterio de 3 niveles validado antes.
# ══════════════════════════════════════════════════════════

def norm(t):
    return " ".join(str(t).lower().replace("\n", " ").split())


celdas_exactas       = {}
texto_concat_pagina  = {}
celdas_individuales  = {}

for t in tablas_con_bbox:
    p = t["page_number"]
    celdas_exactas.setdefault(p, set())
    texto_concat_pagina.setdefault(p, [])
    celdas_individuales.setdefault(p, [])

    concat = ""
    for row in t["rows"]:
        for cell in row["cells"]:
            cn = norm(cell["content"])
            if cn:
                celdas_exactas[p].add(cn)
                celdas_individuales[p].append(cn)
                concat += " " + cn

    texto_concat_pagina[p].append(concat.strip())


def es_duplicado(elem):
    tipo    = elem.get("type")
    content = elem.get("content", "").strip()
    page    = elem.get("page number") or 0

    if tipo not in ("paragraph", "heading") or not content:
        return False

    cn = norm(content)

    if cn in celdas_exactas.get(page, set()):
        return True

    if len(cn) >= 5:
        for tc in texto_concat_pagina.get(page, []):
            if cn in tc:
                return True

    for c in celdas_individuales.get(page, []):
        if cn in c:
            return True

    return False


# ══════════════════════════════════════════════════════════
#  PASO 4 — Serializar elementos de texto sobrevivientes
#           conservando su bounding box para el ordenamiento
# ══════════════════════════════════════════════════════════

nodos_texto = []
eliminados  = 0

for elem in elementos_texto:
    tipo = elem.get("type")

    if tipo in ("paragraph", "heading"):
        if es_duplicado(elem):
            eliminados += 1
            continue

        bb = elem.get("bounding box", [0, 0, 0, 0])
        nodos_texto.append({
            "type":        tipo,
            "id":          elem.get("id"),
            "page_number": elem.get("page number"),
            "content":     elem.get("content", "").strip(),
            "y_top":       bb[3],   # y1: borde superior
            "y_bottom":    bb[1],   # y0: borde inferior
            "x0":          bb[0]
        })

    elif tipo == "list":
        items = []
        for item in elem.get("list items", []):
            c = item.get("content", "").strip()
            if c:
                items.append({"content": c})

        if not items:
            continue

        bb = elem.get("bounding box", [0, 0, 0, 0])
        nodos_texto.append({
            "type":        "list",
            "id":          elem.get("id"),
            "page_number": elem.get("page number"),
            "items":       items,
            "y_top":       bb[3],
            "y_bottom":    bb[1],
            "x0":          bb[0]
        })

print(f"Duplicados eliminados      : {eliminados}")
print(f"Elementos de texto válidos : {len(nodos_texto)}")


# ══════════════════════════════════════════════════════════
#  PASO 5 — Unir texto + tablas y ordenar por posición visual
#
#  Orden: página ascendente, luego Y descendente (de arriba
#  hacia abajo), y como criterio de desempate x0 ascendente
#  (izquierda a derecha, por si hay elementos lado a lado).
# ══════════════════════════════════════════════════════════

todos = nodos_texto + tablas_con_bbox

todos_ordenados = sorted(
    todos,
    key=lambda e: (e["page_number"], -e["y_top"], e["x0"])
)

# Quitar campos auxiliares de ordenamiento antes de exportar
elementos_finales = []
for e in todos_ordenados:
    limpio = {k: v for k, v in e.items() if k not in ("y_top", "y_bottom", "x0")}
    elementos_finales.append(limpio)


resultado = {
    "file_name": contenido["file_name"],
    "total_elements": len(elementos_finales),
    "elements": elementos_finales
}

with open("JSONObtenidos/documento_final_ordenadoPdf2.json", "w", encoding="utf-8") as f:
    json.dump(resultado, f, ensure_ascii=False, indent=4)


# ══════════════════════════════════════════════════════════
#  REPORTE
# ══════════════════════════════════════════════════════════

from collections import Counter
tipos = Counter(e["type"] for e in elementos_finales)

print()
print("=" * 55)
print("  documento_final_ordenado.json generado")
print("=" * 55)
print(f"  Total elementos : {len(elementos_finales)}")
for tipo, cnt in sorted(tipos.items()):
    print(f"    {tipo:<12} : {cnt}")
print("=" * 55)


# ══════════════════════════════════════════════════════════
#  VERIFICACIÓN del caso reportado (páginas 16 y 28)
# ══════════════════════════════════════════════════════════

for pagina in (16, 28):
    print(f"\n--- Página {pagina} (orden final) ---")
    for e in elementos_finales:
        if e["page_number"] == pagina:
            if e["type"] == "table":
                print(f"  [TABLE]     {e['id']}  ({len(e['rows'])} filas)")
            elif e["type"] == "list":
                print(f"  [LIST]      {len(e['items'])} items")
            else:
                print(f"  [{e['type'].upper():<9}] \"{e.get('content','')[:60]}\"")
