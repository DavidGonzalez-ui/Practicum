# Practicum 1.2 — Extracción estructurada de PDF a JSON

Flujo completo para extraer el contenido de **cualquier PDF** y convertirlo
en JSON estructurado y luego aplanado, usando la librería
[`opendataloader_pdf`](https://pypi.org/project/opendataloader-pdf/) y
[`pdfplumber`](https://github.com/jsvine/pdfplumber).

## Descripción

A partir de los PDF facilitados por el docente tutor, el proyecto:

1. Extrae **todo** el contenido detectado (headings, paragraphs, lists,
   tables, images) con `opendataloader_pdf`.
2. Filtra y conserva solo el texto (heading / paragraph / list).
3. Re-extrae las tablas con `pdfplumber` y **las intercala con el texto
   respetando el orden de lectura real** del documento (por posición
   visual en la página, no por orden de extracción).
4. Aplana el árbol JSON resultante en una tabla plana con
   `id / parent_id / order / type / source_id`.

Los 4 scripts **no tienen el nombre del PDF hardcodeado**: detectan
automáticamente el `.pdf` de la carpeta (`_detectar_pdf.py`).

## Estructura del repositorio

```
Entrega_Final/
├── scripts/                  Código del flujo (5 archivos .py)
├── pdfs_entrada/             PDFs de origen facilitados por el tutor
├── JSONObtenidos/            Salidas JSON generadas (ver nota abajo)
├── documentacion/            Documentación ampliada del flujo
├── requirements.txt          Dependencias del proyecto
└── README.md
```

## Sobre los dos PDF procesados y el sufijo `Pdf2`

Este proyecto se ejecutó sobre **dos PDF distintos**, y por eso en
`JSONObtenidos/` conviven dos juegos de resultados.

Los scripts **siempre escriben las salidas con el mismo nombre**
(`contenido_sin_tablas.json`, `documento_final_ordenado.json`,
`documento_aplanado.json`), sin incluir el nombre del PDF. Por tanto, al
procesar el segundo PDF las salidas pisarían a las del primero. Para
**conservar ambos juegos**, las salidas del segundo PDF se guardaron con
el sufijo `Pdf2` añadido manualmente.

| PDF de origen | Salidas (sin sufijo) | Salidas (sufijo `Pdf2`) |
|---|---|---|
| `PLAN_3952-DSOF_1067.pdf` | `contenido_sin_tablas.json` · `documento_final_ordenado.json` · `documento_aplanado.json` | — |
| `DSOF_1067-O20F21.pdf` | — | `contenido_sin_tablasPdf2.json` · `documento_final_ordenadoPdf2.json` · `documento_aplanadoPdf2.json` |

Además, `DSOF_1067-O20F21.json` y `PLAN_3952-DSOF_1067.json` son los JSON
**crudos** que genera el paso 1 (`opendataloader_pdf`) para cada PDF.

> **Nota técnica:** en `3_construir_documento_final_ordenado.py` (línea 100)
> la lectura usa `contenido_sin_tablasPDF2.json` (en mayúsculas), mientras
> que `2_filtrar_contenido_sin_tablas.py` (línea 89) escribe
> `contenido_sin_tablasPdf2.json` (en minúsculas). Si se quiere reejecutar
> el flujo completo del segundo PDF de un tirón habría que unificar esa
> diferencia de mayúsculas. Los resultados ya generados (presentes en
> `JSONObtenidos/`) no se ven afectados.

## Requisitos

- **Python 3.12+**
- **Java** instalado y en el `PATH` (lo necesita `opendataloader_pdf`).
- Dependencias de Python:

```bash
pip install -r requirements.txt
```

## Cómo ejecutar

Ejecuta los scripts en orden desde la carpeta `scripts/`:

```bash
# Paso 1 (requiere Java + opendataloader_pdf).
# Solo necesario si NO tienes ya el JSON crudo en JSONObtenidos/
python 1_extraer_pdf_opendataloader.py

# Paso 2 — filtra y deja solo el texto
python 2_filtrar_contenido_sin_tablas.py

# Paso 3 — re-extrae tablas e intercala todo por posición real
python 3_construir_documento_final_ordenado.py

# Paso 4 — aplana el documento final
python 4_aplanar_documento.py
```

Para usar otro PDF distinto al detectado, pásalo como argumento:

```bash
python 1_extraer_pdf_opendataloader.py mi_archivo.pdf
python 3_construir_documento_final_ordenado.py mi_archivo.pdf
```

## Flujo de datos

```
PDF (cualquiera)
 │
 ▼
1_extraer_pdf_opendataloader.py   ──► JSONObtenidos/<nombre_pdf>.json
 │   (opendataloader_pdf: heading, paragraph, list, table, image...)
 ▼
2_filtrar_contenido_sin_tablas.py ──► JSONObtenidos/contenido_sin_tablas.json
 │   (se queda solo con heading / paragraph / list)
 ▼
3_construir_documento_final_ordenado.py ──► JSONObtenidos/documento_final_ordenado.json
 │   - Re-extrae TODAS las tablas con pdfplumber (con bounding box)
 │   - Elimina párrafos/headings duplicados (texto ya presente en tablas)
 │   - Ordena texto + tablas por posición visual real (Y, X) por página
 ▼
4_aplanar_documento.py ──► JSONObtenidos/documento_aplanado.json
     (aplanador 100% genérico y recursivo)
```

## Resultado de ejemplo (`PLAN_3952-DSOF_1067.pdf`)

`documento_final_ordenado.json`
- 114 elementos (12 headings, 15 listas, 7 párrafos, 80 tablas)
- 280 duplicados de texto eliminados
- Texto y tablas intercalados según el orden de lectura real

`documento_aplanado.json`
- 1139 filas planas con `id / parent_id / order / type / source_id`
- Tipos: `document, heading, paragraph, list, list_item, table,
  table_row, table_cell`

Documentación ampliada en [`documentacion/`](./documentacion/).

## Código

A continuación se incluye el código completo de cada script del flujo.

### `scripts/_detectar_pdf.py`

Función auxiliar usada por los scripts 1, 2 y 3 para que el flujo funcione
con cualquier PDF, sin nombres hardcodeados.

```python
"""
_detectar_pdf.py
─────────────────
Función auxiliar usada por los scripts 1, 2 y 3 para que el flujo
funcione con CUALQUIER PDF, sin nombres hardcodeados.

Reglas de detección:
  1. Si se pasa un argumento por línea de comandos
     (python 1_extraer_pdf_opendataloader.py archivo.pdf), se usa ese.
  2. Si no, busca todos los .pdf en la carpeta actual:
       - si hay exactamente uno -> lo usa
       - si hay varios -> muestra un menú para elegir
       - si no hay ninguno -> lanza un error
"""

import sys
import glob
import os


def detectar_pdf():
    # Caso 1: PDF pasado como argumento
    if len(sys.argv) > 1:
        ruta = sys.argv[1]

        if not os.path.isfile(ruta):
            raise FileNotFoundError(
                f"No existe el archivo: {ruta}"
            )

        return ruta

    # Caso 2: Buscar PDFs en la carpeta actual
    pdfs = glob.glob("*.pdf")

    if len(pdfs) == 0:
        raise FileNotFoundError(
            "No se encontró ningún archivo .pdf en la carpeta actual.\n"
            "Ejecuta el script indicando el archivo:\n"
            "    python nombre_script.py mi_archivo.pdf"
        )

    if len(pdfs) == 1:
        print(f"PDF detectado automáticamente: {pdfs[0]}")
        return pdfs[0]

    # Caso 3: Hay varios PDFs
    print("\nSe encontraron varios archivos PDF:\n")

    for i, pdf in enumerate(pdfs, start=1):
        print(f"{i}. {pdf}")

    while True:
        try:
            opcion = int(
                input("\nSeleccione el número del PDF que desea procesar: ")
            )

            if 1 <= opcion <= len(pdfs):
                pdf_seleccionado = pdfs[opcion - 1]
                print(f"\nPDF seleccionado: {pdf_seleccionado}")
                return pdf_seleccionado

            print(
                f"Debe ingresar un número entre 1 y {len(pdfs)}."
            )

        except ValueError:
            print("Ingrese un número válido.")


def nombre_base(ruta_pdf):
    """
    'DSOF_1067-O20F21.pdf' -> 'DSOF_1067-O20F21'
    """
    return os.path.splitext(
        os.path.basename(ruta_pdf)
    )[0]
```

### `scripts/1_extraer_pdf_opendataloader.py` — Paso 1

Usa `opendataloader_pdf` (requiere Java) para generar el JSON crudo con todo
el contenido detectado del PDF.

```python
"""
1_extraer_pdf_opendataloader.py
─────────────────────────────────
PASO 1 del flujo.

Usa la librería `opendataloader_pdf` (requiere Java instalado) para leer
el PDF y generar un JSON con TODO el contenido detectado por la
herramienta: headings, paragraphs, lists, tables, images, etc.

FUNCIONA CON CUALQUIER PDF:
    - Si hay un solo .pdf en esta carpeta, se detecta automáticamente.
    - Si quieres especificar otro, pásalo como argumento:
          python 1_extraer_pdf_opendataloader.py mi_archivo.pdf

ENTRADA:
    <cualquier>.pdf  (detectado automáticamente)

SALIDA:
    JSONObtenidos/<nombre_del_pdf>.json
    JSONObtenidos/<nombre_del_pdf>.md   (versión markdown, opcional)

NOTA:
    Este paso solo necesita ejecutarse UNA VEZ. Si ya tienes el JSON
    crudo en JSONObtenidos/, puedes saltar este paso y continuar
    directamente con el script 2.
"""

import opendataloader_pdf
from _detectar_pdf import detectar_pdf

pdf_path = detectar_pdf()

print(f"PDF detectado: {pdf_path}")

opendataloader_pdf.convert(
    input_path=[pdf_path],
    output_dir="JSONObtenidos",
    format="markdown,json"
)

print("Extracción con opendataloader_pdf completada -> JSONObtenidos/")
```

### `scripts/2_filtrar_contenido_sin_tablas.py` — Paso 2

Conserva únicamente los elementos de texto (`heading`, `paragraph`, `list`)
del JSON crudo.

```python
"""
2_filtrar_contenido_sin_tablas.py
─────────────────────────────────
PASO 2 del flujo.

Toma el JSON crudo de opendataloader_pdf y se queda únicamente con los
elementos de tipo "heading", "paragraph" y "list" (descarta "image",
"table" y cualquier otro tipo detectado por la propia herramienta).

Este es el "texto" del documento, antes de mezclarlo con las tablas
que extraeremos por separado con pdfplumber (paso 3).

FUNCIONA CON CUALQUIER PDF:
    - Detecta automáticamente el .pdf de esta carpeta y busca su JSON
      crudo correspondiente en JSONObtenidos/<nombre_del_pdf>.json
    - Si no lo encuentra con ese nombre exacto, busca cualquier JSON
      en JSONObtenidos/ que tenga la forma "cruda" (claves "file name"
      y "kids" a nivel raíz) y no sea uno de los archivos generados
      por este mismo flujo.

ENTRADA:
    JSONObtenidos/<nombre_del_pdf>.json

SALIDA:
    JSONObtenidos/contenido_sin_tablas.json
"""

import json
import os
import glob

from _detectar_pdf import detectar_pdf, nombre_base


GENERADOS_POR_EL_FLUJO = {
    "contenido_sin_tablas.json",
    "documento_final_ordenado.json",
    "documento_aplanado.json",
}


def localizar_json_crudo():
    pdf_path = detectar_pdf()
    esperado = os.path.join("JSONObtenidos", f"{nombre_base(pdf_path)}.json")

    if os.path.isfile(esperado):
        return esperado

    # Fallback: buscar cualquier json "crudo" (file name + kids)
    for ruta in glob.glob(os.path.join("JSONObtenidos", "*.json")):
        if os.path.basename(ruta) in GENERADOS_POR_EL_FLUJO:
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and "file name" in data and "kids" in data:
            return ruta

    raise FileNotFoundError(
        f"No se encontró el JSON crudo esperado ({esperado}) ni ningún "
        f"JSON con formato 'file name' + 'kids' en JSONObtenidos/. "
        f"Ejecuta primero 1_extraer_pdf_opendataloader.py"
    )


ruta_json = localizar_json_crudo()
print(f"JSON crudo: {ruta_json}")

with open(ruta_json, "r", encoding="utf-8") as archivo:
    documento = json.load(archivo)

elementos_filtrados = []

for elemento in documento["kids"]:

    tipo = elemento.get("type")

    if tipo in ("heading", "paragraph", "list"):
        elementos_filtrados.append(elemento)

nuevo_json = {
    "file_name": documento["file name"],
    "kids": elementos_filtrados
}

with open(
    "JSONObtenidos/contenido_sin_tablasPdf2.json",
    "w",
    encoding="utf-8"
) as archivo:
    json.dump(nuevo_json, archivo, ensure_ascii=False, indent=4)

print(f"Contenido filtrado: {len(elementos_filtrados)} elementos "
      f"(heading/paragraph/list) -> JSONObtenidos/contenido_sin_tablas.json")
```

### `scripts/3_construir_documento_final_ordenado.py` — Paso 3

Re-extrae las tablas con `pdfplumber` y las intercala con el texto según la
posición visual real en la página.

```python
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
```

### `scripts/4_aplanar_documento.py` — Paso 4 (final)

Aplanador genérico y recursivo: convierte el árbol JSON en una tabla plana
con `id / parent_id / order / type / source_id`.

```python
"""
4_aplanar_documento.py
────────────────────────
PASO 4 del flujo (final).

Aplanador 100% GENÉRICO Y RECURSIVO: convierte CUALQUIER árbol JSON
(dict / list anidados) en una lista plana de filas con:

    id          → identificador único secuencial (entero, determinista)
    parent_id   → id de la fila padre (None para la raíz)
    order       → posición entre hermanos (0, 1, 2, ...)
    type        → tipo de la fila (ver "Cómo se calcula type" abajo)
    source_id   → el "id" ORIGINAL del elemento si lo tenía
                   (ej: 221 para un heading, "T16_2" para una tabla;
                   None si el elemento no tenía "id" propio)
    + el resto de campos simples (content, page_number, etc.)

No asume nada sobre la estructura: NO sabe que una "table" tiene
"rows"->"cells" ni que una "list" tiene "items". Recorre cualquier
clave que sea lista o diccionario, sin importar su nombre. Por eso
sirve para CUALQUIER PDF que pase por el script 3, e incluso para
el JSON crudo de opendataloader_pdf si se quisiera aplanar directo.

Cómo se calcula "type"
───────────────────────
1. Si el elemento tiene su propia clave "type" (heading, paragraph,
   list, table, image, ...) -> se usa ese valor tal cual, y se vuelve
   el "contexto" para sus descendientes.
2. Si NO tiene "type" propio, se construye como
   "{contexto}_{singular(nombre_de_la_clave_que_lo_contenía)}"
   Ejemplos:  table + "rows"  -> "table_row"
              table_row + "cells" (contexto sigue siendo "table")
                                  -> "table_cell"
              list  + "items" -> "list_item"
3. Si tampoco hay contexto (es la raíz del documento), type = "document".

ENTRADA:
    JSONObtenidos/documento_final_ordenado.json

SALIDA:
    JSONObtenidos/documento_aplanado.json
"""

import json
from collections import Counter


filas = []
contador_id = 0


def nuevo_id():
    global contador_id
    contador_id += 1
    return contador_id


def singular(palabra):
    """'rows'->'row', 'cells'->'cell', 'items'->'item', 'kids'->'kid'..."""
    especiales = {"kids": "kid", "children": "child"}
    if palabra in especiales:
        return especiales[palabra]
    if palabra.endswith("s") and len(palabra) > 1:
        return palabra[:-1]
    return palabra


def agregar_fila(tipo, parent_id, order, source_id=None, **campos):
    fila = {
        "id": nuevo_id(),
        "parent_id": parent_id,
        "order": order,
        "type": tipo,
        "source_id": source_id,
    }
    fila.update(campos)
    filas.append(fila)
    return fila["id"]


def aplanar(nodo, parent_id, order, clave_contenedora=None, contexto=None):
    """
    Recorre `nodo` (dict o list) de forma recursiva y agrega filas a `filas`.
    - clave_contenedora: nombre de la clave del padre que contiene a `nodo`
                          (ej: "rows", "items", "elements")
    - contexto: el último "type" explícito visto en algún ancestro
                (ej: "table", "list"); se usa para nombrar a los hijos
                que no tienen "type" propio.
    """

    # ── Caso LISTA: cada item se aplana con el mismo contexto ──
    if isinstance(nodo, list):
        for i, item in enumerate(nodo):
            aplanar(item, parent_id, i,
                    clave_contenedora=clave_contenedora,
                    contexto=contexto)
        return

    # ── Caso DICCIONARIO ──
    if isinstance(nodo, dict):

        tipo_explicito = nodo.get("type")

        if tipo_explicito:
            tipo = tipo_explicito
        elif contexto and clave_contenedora:
            tipo = f"{contexto}_{singular(clave_contenedora)}"
        else:
            tipo = clave_contenedora or "document"

        # el contexto para los hijos: si este nodo definió un "type"
        # propio, ese se vuelve el nuevo contexto; si no, se conserva
        nuevo_contexto = tipo_explicito or contexto

        # campos simples (no dict/list, sin "type"/"id" -> van aparte)
        campos = {
            clave: valor
            for clave, valor in nodo.items()
            if clave not in ("type", "id")
            and not isinstance(valor, (dict, list))
        }

        nodo_id = agregar_fila(
            tipo,
            parent_id,
            order,
            source_id=nodo.get("id"),
            **campos
        )

        # recorrer hijos (cualquier clave que sea dict o list)
        for clave, valor in nodo.items():
            if isinstance(valor, (list, dict)):
                aplanar(valor, nodo_id, 0,
                        clave_contenedora=clave,
                        contexto=nuevo_contexto)

        return


# ══════════════════════════════════════════════════════════
#  LEER documento_final_ordenado.json
# ══════════════════════════════════════════════════════════

with open(
    "JSONObtenidos/documento_final_ordenadoPdf2.json",
    "r",
    encoding="utf-8"
) as f:
    documento = json.load(f)


# ══════════════════════════════════════════════════════════
#  APLANAR (recursivo, sin asumir nada de la estructura)
# ══════════════════════════════════════════════════════════

aplanar(documento, parent_id=None, order=0)


# ══════════════════════════════════════════════════════════
#  GUARDAR
# ══════════════════════════════════════════════════════════

with open(
    "JSONObtenidos/documento_aplanadoPdf2.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(filas, f, ensure_ascii=False, indent=4)


# ══════════════════════════════════════════════════════════
#  REPORTE
# ══════════════════════════════════════════════════════════

conteo = Counter(f["type"] for f in filas)

print("=" * 50)
print("  documento_aplanado.json generado")
print("=" * 50)
print(f"  Total de filas: {len(filas)}")
for tipo, cnt in sorted(conteo.items()):
    print(f"    {tipo:<15} : {cnt}")
print("=" * 50)
```
