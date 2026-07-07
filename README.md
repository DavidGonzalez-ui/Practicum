# Practicum 1.2 — Extracción estructurada de PDF a JSON para MongoDB

A continucacion se muestra el flujo completo y replicable que toma un archivo PDF, extrae todo su contenido, lo limpia, lo ordena según
el orden de lectura del documento y lo transforma en un único
diccionario jerárquico de tipo `clave: valor` listo para subir a MongoDB.

Las herramientas usadas fueron: 

* [`opendataloader_pdf`](https://pypi.org/project/opendataloader-pdf/)
(se usa para la extracción inicial y requiere Java).

* [`pdfplumber`](https://github.com/jsvine/pdfplumber) (para la re-extracción de tablas
con posición real).

## Resultados obtenidos

El flujo se ejecutó sobre los dos PDF que se nos facilitaron
(se encuentran en [`pdfs_entrada/`](./pdfs_entrada/)). Todos los archivos
generados se pueden encontrar en [`JSONObtenidos/`](./JSONObtenidos/):

| | `DSOF_1067-O20F21.pdf` | `PLAN_3952-DSOF_1067.pdf` |
|---|---|---|
| JSON crudo | `DSOF_1067-O20F21.json` | `PLAN_3952-DSOF_1067.json` |
| Solo texto | `contenido_sin_tablas.json` | `contenido_sin_tablas2.json` |
| Documento ordenado | `documento_final_ordenado.json` | `documento_final_ordenado2.json` |
| Aplanado para MongoDB | `documento_final_ordenado1_para_mongo.json` | `documento_para_mongo_generico.json` |

Ejemplo real del resultado final:

```json
{
  "a_datos_de_identificacion_de_la_asignatura": {
    "asignatura": "Introducción a la programación",
    "modalidad_de_estudio": "Presencial",
    "area_academica": "Técnica",
    "nombre_de_la_carrera": "Computación"
  }
}
```

Las **claves** quedan normalizadas (snake_case, sin tildes ni símbolos, para
que la notación de puntos de MongoDB funcione sin errores) y los **valores**
conservan el texto original intacto.

## Estructura del repositorio

```
Practicum1.2/
├── scripts/                       Código del flujo (6 archivos .py)
│   ├── _detectar_pdf.py               Auxiliar: detección/selección del PDF
│   ├── 1_extraer_pdf_opendataloader.py    Paso 1: extracción cruda
│   ├── 2_filtrar_contenido_sin_tablas.py  Paso 2: filtrar solo texto
│   ├── 3_construir_documento_final_ordenado.py  Paso 3: tablas + orden real
│   ├── aplanar_para_mongo_generico.py     Paso 4: aplanado clave:valor p/ Mongo
│   └── 4_aplanar_documento.py             Conversor alternativo clave:valor
├── pdfs_entrada/                  PDFs de origen facilitados por el tutor
├── JSONObtenidos/                 Todas las salidas generadas (JSON, MD, imágenes)
├── documentacion/                 Explicación ampliada del flujo y los scripts
├── requirements.txt
└── README.md
```

## Requisitos e instalación

1. **Python 3.10+** — verificar con `python --version`.
2. **Java (JRE 8+)** instalado y en el `PATH` — lo necesita
   `opendataloader_pdf` internamente. Verificar con `java -version`.
3. Instalar las dependencias de Python:

```bash
pip install -r requirements.txt
```

(Instala `opendataloader_pdf` y `pdfplumber`; el resto es librería estándar.)

## Proceso replicable paso a paso

> **Preparación:** copiar el PDF a procesar y los scripts a una misma carpeta
> de trabajo (los scripts detectan el `.pdf` de la **carpeta actual**). La
> carpeta `JSONObtenidos/` se crea sola en el paso 1. Todos los comandos se
> ejecutan desde esa carpeta de trabajo.

### Paso 1 — Extracción cruda con `opendataloader_pdf`

```bash
python 1_extraer_pdf_opendataloader.py
```

Si hay un solo PDF en la carpeta lo detecta automáticamente; si hay varios,
muestra un menú numerado para elegir (también se puede pasar como argumento:
`python 1_extraer_pdf_opendataloader.py PLAN_3952-DSOF_1067.pdf`).

**Salida esperada:** `JSONObtenidos/<nombre_pdf>.json` (todo el contenido
detectado: headings, paragraphs, lists, tables, images), más una versión
Markdown `<nombre_pdf>.md` y una carpeta `<nombre_pdf>_images/` con las
imágenes extraídas del PDF.

### Paso 2 — Filtrar solo el texto

```bash
python 2_filtrar_contenido_sin_tablas.py
```

Lee el JSON crudo del PDF detectado y conserva únicamente los elementos
`heading`, `paragraph` y `list` (descarta `table`, `image`, etc.).

**Salida esperada:** `JSONObtenidos/contenido_sin_tablas2.json`.
Con `PLAN_3952-DSOF_1067.pdf` la consola reporta `Filtrado: 314 elementos`;
con `DSOF_1067-O20F21.pdf`, 23 elementos.

### Paso 3 — Re-extraer tablas e intercalar por posición real

```bash
python 3_construir_documento_final_ordenado.py
```

Re-extrae **todas** las tablas con `pdfplumber` (con su *bounding box*),
elimina los párrafos/headings que en realidad son texto de una tabla, y
ordena texto + tablas por **posición visual real** en cada página.

**Salida esperada:** `JSONObtenidos/documento_final_ordenado2.json`.
Reporte real con `PLAN_3952-DSOF_1067.pdf`:

```
Tablas extraídas: 80
Elementos de texto: 314
Duplicados eliminados: 280
==================================================
  Total: 114
    heading      : 12
    list         : 15
    paragraph    : 7
    table        : 80
==================================================
```

### Paso 4 — Aplanar a clave:valor para MongoDB

```bash
python aplanar_para_mongo_generico.py JSONObtenidos/documento_final_ordenado2.json JSONObtenidos/documento_para_mongo_generico.json
```

Recibe la **entrada** y la **salida** como argumentos. Convierte el documento
ordenado en un único diccionario jerárquico `clave: valor`, sin metadata
(sin `type`, `id`, `page_number`…), con claves seguras para MongoDB.

Así se generaron los dos resultados incluidos en este repositorio:

```bash
# PDF 1 (DSOF)
python aplanar_para_mongo_generico.py JSONObtenidos/documento_final_ordenado.json JSONObtenidos/documento_final_ordenado1_para_mongo.json

# PDF 2 (PLAN)
python aplanar_para_mongo_generico.py JSONObtenidos/documento_final_ordenado2.json JSONObtenidos/documento_para_mongo_generico.json
```

### Paso 5 (opcional) — Subir a MongoDB

El JSON final es un único documento, listo para importarse tal cual:

```bash
mongoimport --db practicum --collection asignaturas --file JSONObtenidos/documento_para_mongo_generico.json
```

### Procesar un segundo PDF

Los pasos 2 y 3 escriben **siempre los mismos nombres de archivo**
(`contenido_sin_tablas2.json`, `documento_final_ordenado2.json`), por lo que
una segunda ejecución sobreescribiría la primera. Para conservar ambos
resultados, **renombrar las salidas antes de procesar el siguiente PDF** —
así se hizo en esta entrega: las salidas de `DSOF_1067-O20F21.pdf` se
conservaron sin el sufijo `2` y las de `PLAN_3952-DSOF_1067.pdf` con él.

## Cómo funciona (resumen)

La explicación completa está en
[`documentacion/flujo.md`](./documentacion/flujo.md); estas son las ideas
clave:

**Orden de lectura real (paso 3).** `opendataloader_pdf` da la posición del
texto en coordenadas PDF (origen abajo-izquierda, Y crece hacia arriba) y
`pdfplumber` da la de las tablas en su propio sistema (origen
arriba-izquierda, `top` crece hacia abajo). Convirtiendo el bbox de la tabla
con `y_top = page.height - top`, ambos quedan en el mismo sistema y basta
ordenar cada página por Y descendente (con desempate por X) para reconstruir
el orden en que se lee el documento, intercalando texto y tablas
correctamente.

**Duplicados (paso 3).** El texto que ya vive dentro de una tabla se detecta
con 3 niveles de comparación por página: coincidencia exacta con una celda,
contención en el texto concatenado de la tabla, y contención dentro de una
celda individual. En `PLAN_3952-DSOF_1067.pdf` esto eliminó 280 duplicados.

**Tablas cortadas por página (paso 4).** Antes de interpretar las tablas, el
aplanador las reconstruye: descarta títulos repetidos por el salto de página,
pega el contenido que quedó separado de su título (caso típico: el título
"Semana 6" queda solo al final de una tabla y sus datos caen en la
siguiente), y fusiona las tablas-matriz partidas usando `column_number`.

**Interpretación de tablas (paso 4).** Dos estrategias: *tabla-matriz*
(encabezados de columna reales, p. ej. horarios) se convierte en una lista de
registros, heredando de la fila anterior las celdas combinadas (*rowspan*,
p. ej. la columna "Componente"); *tabla-formulario* usa la regla padre-hijo:
una fila de 1 celda (p. ej. "A. Datos básicos de la asignatura") es el padre
de las filas siguientes, y cada fila de 2 celdas es un par `clave: valor`.

**Texto (paso 4).** Un heading o párrafo con el patrón `Etiqueta: valor`
(p. ej. "ÁREA ACADÉMICA: Técnica") se convierte en un campo de la sección
actual; un párrafo que termina en `:` o que es corto y precede a una
tabla/lista se trata como título de sección (p. ej. "Fechas importantes:");
el resto es contenido.

**Claves seguras (paso 4).** `clean_key()` pasa las claves a snake_case sin
tildes ni símbolos (los puntos rompen la notación de puntos de Mongo) y
`add_unique()` evita perder datos: si una clave se repite, agrupa los valores
en una lista en vez de sobrescribir.

## Notas de replicabilidad

- Ejecutar los scripts **desde la carpeta donde está el PDF**; las rutas de
  salida (`JSONObtenidos/...`) son relativas a la carpeta actual.
- Los mensajes en consola de los pasos 2 y 3 muestran los nombres sin el
  sufijo `2` (`contenido_sin_tablas.json`, `documento_final_ordenado.json`),
  pero los archivos **realmente escritos** son `contenido_sin_tablas2.json` y
  `documento_final_ordenado2.json`. El flujo entre pasos es consistente
  (el paso 3 lee exactamente lo que escribe el paso 2).
- `4_aplanar_documento.py` (conversor alternativo) tiene su ruta de entrada
  escrita con backslash de Windows (`JSONObtenidos\documento_final_ordenado2.json`);
  en Linux/Mac hay que cambiarla a `/`. Los resultados de MongoDB de esta
  entrega se generaron con `aplanar_para_mongo_generico.py`, que recibe las
  rutas por argumento y funciona en cualquier sistema.
- El paso 1 falla si Java no está instalado o no está en el `PATH`.

## Código

Código completo de cada script, tal como se usó para generar los resultados
de `JSONObtenidos/`. La explicación va antes de cada bloque.

### `scripts/_detectar_pdf.py`

Auxiliar de los pasos 1–3. Si se pasa un PDF por argumento lo usa; si no,
busca los `.pdf` de la carpeta actual (uno → lo usa; varios → menú numerado;
ninguno → error). `nombre_base()` devuelve el nombre del archivo sin
extensión, usado para nombrar las salidas del paso 1.

```python
import sys
import glob
import os


def detectar_pdf():
    # Si se pasa un PDF por argumento
    if len(sys.argv) > 1:
        ruta = sys.argv[1]

        if not os.path.isfile(ruta):
            raise FileNotFoundError(
                f"No existe el archivo: {ruta}"
            )

        return ruta

    # Buscar PDFs en la carpeta actual
    pdfs = glob.glob("*.pdf")

    if len(pdfs) == 0:
        raise FileNotFoundError(
            "No se encontró ningún archivo PDF."
        )

    if len(pdfs) == 1:
        print(f"PDF detectado: {pdfs[0]}")
        return pdfs[0]

    # Hay varios PDFs
    print("\nPDFs encontrados:\n")

    for i, pdf in enumerate(pdfs, start=1):
        print(f"{i}. {pdf}")

    while True:
        try:
            opcion = int(
                input("\nSeleccione el PDF a procesar: ")
            )

            if 1 <= opcion <= len(pdfs):
                return pdfs[opcion - 1]

            print(
                f"Ingrese un número entre 1 y {len(pdfs)}"
            )

        except ValueError:
            print("Ingrese un número válido")


def nombre_base(ruta_pdf):
    return os.path.splitext(
        os.path.basename(ruta_pdf)
    )[0]
```

### `scripts/1_extraer_pdf_opendataloader.py` — Paso 1

Crea `JSONObtenidos/` si no existe y llama a `opendataloader_pdf.convert()`
para generar el JSON crudo con todo el contenido detectado, más la versión
Markdown y las imágenes del PDF.

```python
import os
import opendataloader_pdf
from _detectar_pdf import detectar_pdf, nombre_base

pdf_path = detectar_pdf()
base     = nombre_base(pdf_path)

os.makedirs("JSONObtenidos", exist_ok=True)

print(f"Procesando: {pdf_path}")

opendataloader_pdf.convert(
    input_path=[pdf_path],
    output_dir="JSONObtenidos",
    format="markdown,json"
)

print(f"Extracción completada → JSONObtenidos/{base}.json")
```

### `scripts/2_filtrar_contenido_sin_tablas.py` — Paso 2

Localiza el JSON crudo del PDF detectado (`JSONObtenidos/<nombre_pdf>.json`)
y conserva solo los elementos de texto (`heading`, `paragraph`, `list`).

```python
import json
import os
import glob
from _detectar_pdf import detectar_pdf, nombre_base

# Localizar el JSON crudo que corresponde al PDF seleccionado
pdf_path  = detectar_pdf()
base      = nombre_base(pdf_path)
json_crudo = os.path.join("JSONObtenidos", f"{base}.json")

if not os.path.isfile(json_crudo):
    raise FileNotFoundError(
        f"No se encontró {json_crudo}.\n"
        f"Ejecuta primero: python 1_extraer_pdf_opendataloader.py"
    )

print(f"Leyendo: {json_crudo}")

with open(json_crudo, "r", encoding="utf-8") as f:
    documento = json.load(f)

elementos_filtrados = [
    elem for elem in documento["kids"]
    if elem.get("type") in ("heading", "paragraph", "list")
]

nuevo_json = {
    "file_name": documento["file name"],
    "kids":      elementos_filtrados
}

with open("JSONObtenidos/contenido_sin_tablas2.json", "w", encoding="utf-8") as f:
    json.dump(nuevo_json, f, ensure_ascii=False, indent=4)

print(f"Filtrado: {len(elementos_filtrados)} elementos → JSONObtenidos/contenido_sin_tablas.json")
```

### `scripts/3_construir_documento_final_ordenado.py` — Paso 3

Re-extrae las tablas con `pdfplumber` conservando su bounding box, limpia las
celdas vacías, elimina el texto duplicado (3 niveles de comparación) y ordena
todos los elementos por `(página, −Y, X)` — el orden de lectura real.

```python
import json
import pdfplumber
from _detectar_pdf import detectar_pdf

PDF_PATH = detectar_pdf()
print(f"PDF: {PDF_PATH}")

# ── Re-extraer tablas con bbox ────────────────────────────────────────────────

tablas_con_bbox = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_idx, page in enumerate(pdf.pages, start=1):
        for table_idx, tabla in enumerate(page.find_tables(), start=1):

            x0, top, x1, bottom = tabla.bbox
            y1_pdf = page.height - top
            y0_pdf = page.height - bottom

            filas_limpias = []
            for fila_num, fila in enumerate(tabla.extract(), start=1):
                celdas = [
                    {"column_number": i, "content": str(v).strip()}
                    for i, v in enumerate(fila, start=1)
                    if v and str(v).strip()
                ]
                if celdas:
                    filas_limpias.append({"row_number": fila_num, "cells": celdas})

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

print(f"Tablas extraídas: {len(tablas_con_bbox)}")

# ── Cargar texto ──────────────────────────────────────────────────────────────

with open("JSONObtenidos/contenido_sin_tablas2.json", "r", encoding="utf-8") as f:
    contenido = json.load(f)

elementos_texto = contenido["kids"]
print(f"Elementos de texto: {len(elementos_texto)}")

# ── Índices para detección de duplicados (3 niveles) ─────────────────────────

def norm(t):
    return " ".join(str(t).lower().replace("\n", " ").split())

celdas_exactas      = {}
texto_concat_pagina = {}
celdas_individuales = {}

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

# ── Serializar texto sobreviviente ────────────────────────────────────────────

nodos_texto = []
eliminados  = 0

for elem in elementos_texto:
    tipo = elem.get("type")
    bb   = elem.get("bounding box", [0, 0, 0, 0])

    if tipo in ("paragraph", "heading"):
        if es_duplicado(elem):
            eliminados += 1
            continue
        nodos_texto.append({
            "type":        tipo,
            "id":          elem.get("id"),
            "page_number": elem.get("page number"),
            "content":     elem.get("content", "").strip(),
            "y_top":       bb[3],
            "y_bottom":    bb[1],
            "x0":          bb[0]
        })

    elif tipo == "list":
        items = [
            {"content": item.get("content", "").strip()}
            for item in elem.get("list items", [])
            if item.get("content", "").strip()
        ]
        if items:
            nodos_texto.append({
                "type":        "list",
                "id":          elem.get("id"),
                "page_number": elem.get("page number"),
                "items":       items,
                "y_top":       bb[3],
                "y_bottom":    bb[1],
                "x0":          bb[0]
            })

print(f"Duplicados eliminados: {eliminados}")

# ── Unir + ordenar por posición visual ───────────────────────────────────────

todos_ordenados = sorted(
    nodos_texto + tablas_con_bbox,
    key=lambda e: (e["page_number"], -e["y_top"], e["x0"])
)

elementos_finales = [
    {k: v for k, v in e.items() if k not in ("y_top", "y_bottom", "x0")}
    for e in todos_ordenados
]

resultado = {
    "file_name":      contenido["file_name"],
    "total_elements": len(elementos_finales),
    "elements":       elementos_finales
}

with open("JSONObtenidos/documento_final_ordenado2.json", "w", encoding="utf-8") as f:
    json.dump(resultado, f, ensure_ascii=False, indent=4)

from collections import Counter
tipos = Counter(e["type"] for e in elementos_finales)
print()
print("=" * 50)
print("  documento_final_ordenado.json generado")
print("=" * 50)
print(f"  Total: {len(elementos_finales)}")
for t, c in sorted(tipos.items()):
    print(f"    {t:<12} : {c}")
print("=" * 50)
```

### `scripts/aplanar_para_mongo_generico.py` — Paso 4

El paso final. Reconstruye las tablas cortadas por los saltos de página,
interpreta cada tabla como matriz o como formulario padre-hijo, clasifica los
párrafos en título/contenido, y arma un único diccionario jerárquico
`clave: valor` con claves normalizadas para MongoDB. Uso:
`python aplanar_para_mongo_generico.py entrada.json salida.json`.

```python
import json
import re
import sys
import unicodedata


def clean_key(text) -> str:
    """Convierte texto crudo (celda/encabezado) en una clave de Mongo
    100% segura: sin tildes/diéresis/ñ especiales, sin puntos ni otros
    símbolos (rompen la notación de puntos de Mongo), sin espacios
    (todo en snake_case). Esto NUNCA se aplica a los valores, solo a
    las claves."""
    if text is None:
        return "campo"
    key = str(text).strip()
    key = unicodedata.normalize("NFKD", key)
    key = "".join(c for c in key if not unicodedata.combining(c))  # quita tildes
    key = re.sub(r"[^A-Za-z0-9]+", " ", key)  # cualquier símbolo (incluye '.') -> espacio
    key = re.sub(r"\s+", "_", key.strip())
    return key.lower() if key else "campo"


def add_unique(target: dict, key: str, value):
    """Agrega key:value; si la clave ya existe, la convierte en lista
    en vez de sobrescribirla. Si tanto el valor existente como el nuevo
    son listas, se concatenan (no se anida una lista dentro de otra)."""
    if key in target:
        if isinstance(target[key], list) and isinstance(value, list):
            target[key].extend(value)
        elif isinstance(target[key], list):
            target[key].append(value)
        else:
            target[key] = [target[key], value]
    else:
        target[key] = value


_EMBEDDED_KV = re.compile(r"^([^:：]{1,60}):\s*(.+)$", re.DOTALL)


def split_embedded_kv(text: str):
    """Separa el patrón 'Etiqueta: valor' cuando viene junto en un mismo
    texto (ej. 'Crédito: 3' o 'ÁREA ACADÉMICA: Técnica'). None si el
    texto termina en ':' sin nada después."""
    if not text:
        return None
    m = _EMBEDDED_KV.match(text.strip())
    if not m:
        return None
    etiqueta, valor = m.group(1).strip(), m.group(2).strip()
    if not etiqueta or not valor:
        return None
    return clean_key(etiqueta), valor


# ---------------------------------------------------------------------
# Preparación de tablas: el PDF corta muchas tablas al cambiar de página.
# El título de una sección (ej. "Semana 6") suele quedar solo en una
# tabla, y su contenido real cae en la(s) tabla(s) siguientes SIN su
# propio título. Estas reglas reconstruyen la tabla completa antes de
# interpretarla.
# ---------------------------------------------------------------------

def _es_titulo_duplicado(actual, anterior):
    """La tabla 'actual' es una fila suelta cuyo texto repite EXACTO el
    título con el que terminó la tabla anterior (artefacto típico de
    salto de página): se descarta, no aporta nada nuevo."""
    filas_a = actual.get("rows") or []
    filas_p = anterior.get("rows") or []
    if len(filas_a) != 1 or not filas_p:
        return False
    celdas_a = filas_a[0].get("cells", [])
    celdas_p = filas_p[-1].get("cells", [])
    if len(celdas_a) != 1 or len(celdas_p) != 1:
        return False
    return clean_key(celdas_a[0].get("content")) == clean_key(celdas_p[0].get("content"))


def _tiene_titulo_colgante_confiable(table):
    """True solo si hay evidencia fuerte de que la tabla quedó cortada a
    mitad de un bloque título+contenido (y no es simplemente una lista de
    casilleros que termina en un ítem suelto, ni una tabla-matriz cuya
    última fila es un dato disperso y no un título).

    Evidencia fuerte = la tabla termina en una fila de 1 celda, Y ADEMÁS:
    - es la ÚNICA fila de la tabla (un título suelto, sin nada más), o
    - la fila justo antes tiene 2+ celdas (datos reales), señal de que
      el bloque título+contenido se interrumpió a mitad de camino.
    """
    rows = table.get("rows") or []
    if not rows or is_matrix_table(rows):
        return False
    if len(rows[-1].get("cells", [])) != 1:
        return False
    if len(rows) == 1:
        return True
    return len(rows[-2].get("cells", [])) >= 2


def _empieza_sin_titulo(table):
    """True si la primera fila de la tabla NO es un título (no tiene
    exactamente 1 celda): esta tabla no abre su propia sección."""
    rows = table.get("rows") or []
    return bool(rows) and len(rows[0].get("cells", [])) != 1


def _es_continuacion_de_matriz(table):
    """Tabla-matriz (ej. horarios) cortada por página: ninguna de sus
    celdas usa la columna 1 porque esa columna quedó vacía en el corte."""
    rows = table.get("rows") or []
    if not rows:
        return False
    return all(c.get("column_number") != 1 for r in rows for c in r.get("cells", []))


def preparar_tablas(elementos: list) -> list:
    resultado = []
    for e in elementos:
        es_tabla = isinstance(e, dict) and e.get("type") == "table"
        anterior = resultado[-1] if resultado and isinstance(resultado[-1], dict) else None
        anterior_es_tabla = anterior is not None and anterior.get("type") == "table"

        if es_tabla and anterior_es_tabla:
            if _es_titulo_duplicado(e, anterior):
                continue  # título repetido por el corte de página: se descarta

            if _tiene_titulo_colgante_confiable(anterior) and _empieza_sin_titulo(e):
                # Contenido sin título propio, y la tabla anterior quedó
                # con un título sin resolver: se pega como continuación.
                anterior["rows"] = (anterior.get("rows") or []) + (e.get("rows") or [])
                continue

            if _es_continuacion_de_matriz(e):
                nuevas_filas = e.get("rows") or []
                prev_rows = anterior.get("rows") or []
                fusionado = False
                if len(nuevas_filas) == 1 and prev_rows:
                    cols_previas = {c["column_number"]: c for c in prev_rows[-1].get("cells", [])}
                    for c in nuevas_filas[0].get("cells", []):
                        if c["column_number"] in cols_previas:
                            celda = cols_previas[c["column_number"]]
                            celda["content"] = f"{str(celda.get('content', '')).rstrip()}\n{c.get('content', '')}"
                            fusionado = True
                if not fusionado:
                    anterior["rows"] = prev_rows + nuevas_filas
                continue

        resultado.append(e)
    return resultado


def is_matrix_table(rows) -> bool:
    """Tabla-matriz (columnas reales, ej. horarios): la primera fila
    tiene 3+ celdas que no terminan en ':' (son encabezados de columna)."""
    if not rows:
        return False
    first_cells = rows[0].get("cells", [])
    if len(first_cells) < 3:
        return False
    if any(str(c.get("content", "")).rstrip().endswith(":") for c in first_cells):
        return False
    max_col = max((c.get("column_number", 1) for r in rows for c in r.get("cells", [])), default=1)
    return max_col > 2


def parse_matrix_table(rows):
    """Lista de registros usando column_number para emparejar cada celda
    con el encabezado real de su columna. Cuando a una fila le falta la
    PRIMERA columna (ej. 'Componente'), es porque en el PDF original esa
    celda estaba combinada (rowspan) con la fila de arriba: se hereda el
    valor de la fila anterior para esa y cualquier otra columna faltante,
    igual que se ve visualmente en la tabla del PDF."""
    headers = {c.get("column_number"): clean_key(c.get("content")) for c in rows[0].get("cells", [])}
    columnas = sorted(headers.keys())
    primera_columna = columnas[0] if columnas else None

    registros = []
    anterior = {}
    for row in rows[1:]:
        celdas = {c.get("column_number"): c.get("content") for c in row.get("cells", [])}
        es_continuacion = primera_columna is not None and primera_columna not in celdas
        registro = {}
        for col in columnas:
            nombre_col = headers[col]
            if col in celdas:
                add_unique(registro, nombre_col, celdas[col])
            elif es_continuacion and nombre_col in anterior:
                add_unique(registro, nombre_col, anterior[nombre_col])
        for col, valor in celdas.items():
            if col not in headers:
                add_unique(registro, f"columna_{col}", valor)
        registros.append(registro)
        anterior = registro
    return registros


def parse_row_into(row, target: dict):
    """Regla padre-hijo por fila: 2 celdas = clave:valor directo; 3+ =
    primera celda como mini-título y el resto en pares clave:valor (o
    separando 'Etiqueta: valor' si viene junto en una celda)."""
    cells = row.get("cells", [])
    n = len(cells)
    if n == 0:
        return
    if n == 1:
        target.setdefault("otros_elementos", []).append(cells[0].get("content"))
    elif n == 2:
        add_unique(target, clean_key(cells[0].get("content")), cells[1].get("content"))
    else:
        label = clean_key(cells[0].get("content"))
        resto = cells[1:]
        sub = {}
        i = 0
        while i < len(resto):
            embebido = split_embedded_kv(resto[i].get("content"))
            if embebido:
                add_unique(sub, embebido[0], embebido[1])
                i += 1
            elif i + 1 < len(resto):
                add_unique(sub, clean_key(resto[i].get("content")), resto[i + 1].get("content"))
                i += 2
            else:
                add_unique(sub, "valor_adicional", resto[i].get("content"))
                i += 1
        add_unique(target, label, sub)


def _tiene_hijos_antes_del_siguiente_titulo(rows, start_idx):
    j = start_idx
    found = False
    while j < len(rows) and len(rows[j].get("cells", [])) != 1:
        if len(rows[j].get("cells", [])) >= 2:
            found = True
        j += 1
    return found, j


def parse_form_table(rows):
    """Tabla tipo formulario: una fila de 1 celda es el PADRE de las
    filas que siguen (hasta la próxima fila de 1 celda), igual que en el
    ejemplo original ('A. Datos básicos...' como padre de 'Nombre de la
    asignatura' -> 'INTRODUCCION A LA PROGRAMACION')."""
    contenido = {}
    idx, n = 0, len(rows)
    while idx < n:
        row = rows[idx]
        cells = row.get("cells", [])
        if len(cells) == 1:
            label = clean_key(cells[0].get("content"))
            tiene_hijos, next_idx = _tiene_hijos_antes_del_siguiente_titulo(rows, idx + 1)
            if tiene_hijos:
                sub = {}
                for j in range(idx + 1, next_idx):
                    parse_row_into(rows[j], sub)
                add_unique(contenido, label, sub)
                idx = next_idx
            else:
                contenido.setdefault("otros_elementos", []).append(cells[0].get("content"))
                idx += 1
        else:
            parse_row_into(row, contenido)
            idx += 1
    return contenido


def merge_section_content(root: dict, section_key: str, data):
    """Une 'data' (dict o list) dentro de root[section_key] sin agregar
    metadata. Si los tipos no calzan (dict existente + list nueva, o
    viceversa) se envuelven bajo 'registros' en vez de perder datos."""
    existente = root.get(section_key)
    if existente is None or existente == {}:
        root[section_key] = data
        return
    if isinstance(existente, dict):
        if isinstance(data, dict):
            for k, v in data.items():
                add_unique(existente, k, v)
        else:
            add_unique(existente, "registros", data)
    elif isinstance(existente, list):
        if isinstance(data, list):
            existente.extend(data)
        else:
            nuevo = {"registros": existente}
            for k, v in data.items():
                add_unique(nuevo, k, v)
            root[section_key] = nuevo
    else:
        root[section_key] = {"valor_previo": existente}
        merge_section_content(root, section_key, data)


def encontrar_lista_de_elementos(data):
    """Ubica la lista de elementos aunque no esté bajo la clave 'elements'."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("elements"), list):
            return data["elements"]
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and "type" in v[0]:
                return v
    raise ValueError(
        "No pude encontrar la lista de elementos del documento. Esperaba "
        "una clave 'elements' (lista de objetos con 'type'), o directamente "
        "una lista de esos objetos en la raíz."
    )


_FIN_ORACION = (".", ",", ";")


def _clasificar_parrafo(texto: str, siguiente_tipo):
    """Distingue párrafo-TÍTULO (ej. 'Fechas importantes:') de
    párrafo-CONTENIDO (ej. una descripción larga). Termina en ':' ->
    título. Termina en '.', ',' o ';' -> contenido. Corto y justo antes
    de tabla/lista -> título que las agrupa. Otro caso -> contenido."""
    t = (texto or "").strip()
    if not t:
        return "vacio"
    if t.endswith(":"):
        return "titulo"
    if t.endswith(_FIN_ORACION):
        return "contenido"
    return "titulo" if len(t.split()) <= 10 and siguiente_tipo in ("table", "list") else "contenido"


def transformar(data) -> dict:
    elementos = preparar_tablas(encontrar_lista_de_elementos(data))

    root: dict = {}
    seccion_actual = None
    contador_listas = 0

    for idx, e in enumerate(elementos):
        if not isinstance(e, dict):
            continue

        tipo = e.get("type")
        siguiente = elementos[idx + 1] if idx + 1 < len(elementos) else None
        siguiente_tipo = siguiente.get("type") if isinstance(siguiente, dict) else None

        try:
            if tipo == "heading":
                contenido_txt = e.get("content")
                if contenido_txt is None:
                    continue
                # Un heading tipo "ÁREA ACADÉMICA: Técnica" es en realidad
                # un campo clave:valor de la sección actual, no un título
                # nuevo (a diferencia de "A. Datos básicos...", que no
                # trae un valor embebido y sí abre sección).
                embebido = split_embedded_kv(contenido_txt)
                if embebido and seccion_actual is not None:
                    merge_section_content(root, seccion_actual, {embebido[0]: embebido[1]})
                else:
                    clave = clean_key(contenido_txt)
                    root.setdefault(clave, {})
                    seccion_actual = clave

            elif tipo == "paragraph":
                contenido_txt = e.get("content")
                if contenido_txt is None:
                    continue
                embebido = split_embedded_kv(contenido_txt)
                if embebido:
                    seccion_actual = seccion_actual or "contenido"
                    root.setdefault(seccion_actual, {})
                    merge_section_content(root, seccion_actual, {embebido[0]: embebido[1]})
                elif _clasificar_parrafo(contenido_txt, siguiente_tipo) == "titulo":
                    clave = clean_key(contenido_txt)
                    root.setdefault(clave, {})
                    seccion_actual = clave
                else:
                    seccion_actual = seccion_actual or "contenido"
                    root.setdefault(seccion_actual, {})
                    merge_section_content(root, seccion_actual, {"texto": contenido_txt})

            elif tipo == "table":
                rows = e.get("rows", [])
                contenido = parse_matrix_table(rows) if is_matrix_table(rows) else parse_form_table(rows)
                seccion_actual = seccion_actual or "contenido"
                root.setdefault(seccion_actual, {})
                merge_section_content(root, seccion_actual, contenido)

            elif tipo == "list":
                contador_listas += 1
                items = [item.get("content") for item in e.get("items", [])]
                seccion_actual = seccion_actual or "contenido"
                root.setdefault(seccion_actual, {})
                merge_section_content(root, seccion_actual, {f"lista_{contador_listas}": items})

            else:
                seccion_actual = seccion_actual or "contenido"
                root.setdefault(seccion_actual, {})
                if isinstance(e.get("rows"), list):
                    rows = e["rows"]
                    contenido = parse_matrix_table(rows) if is_matrix_table(rows) else parse_form_table(rows)
                    merge_section_content(root, seccion_actual, contenido)
                elif isinstance(e.get("items"), list):
                    contador_listas += 1
                    items = [i.get("content", i) if isinstance(i, dict) else i for i in e["items"]]
                    merge_section_content(root, seccion_actual, {f"lista_{contador_listas}": items})
                elif e.get("content") is not None:
                    clave = clean_key(e["content"])
                    root.setdefault(clave, {})
                    seccion_actual = clave
        except Exception:
            continue

    return root


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "documento_final_ordenado.json"
    salida_path = sys.argv[2] if len(sys.argv) > 2 else "documento_para_mongo_generico.json"

    with open(entrada, encoding="utf-8") as f:
        data = json.load(f)

    with open(salida_path, "w", encoding="utf-8") as f:
        json.dump(transformar(data), f, ensure_ascii=False, indent=2)

    print(salida_path)
```

### `scripts/4_aplanar_documento.py` — Conversor alternativo

Versión previa del aplanado clave:valor (`SmartJSONConverter`): interpreta
las tablas fila por fila según su número de celdas y agrupa párrafos,
encabezados y listas del documento ordenado. Se conserva en el repositorio
como alternativa; los resultados de MongoDB incluidos se generaron con
`aplanar_para_mongo_generico.py`.

```python
import json
import re
import unicodedata
from pathlib import Path
from datetime import datetime


class SmartJSONConverter:
    
    def __init__(self, archivo_json: str):
        self.archivo_json = archivo_json
        self.datos_originales = None
        self.datos_planos = {}
        self.claves_usadas = set()
    
    def cargar_json(self) -> bool:
        try:
            with open(self.archivo_json, 'r', encoding='utf-8') as f:
                self.datos_originales = json.load(f)
            return True
        except Exception:
            return False
    
    def normalizar_clave(self, texto: str) -> str:
        if not isinstance(texto, str):
            return str(texto).lower()
        
        texto = re.sub(r'\s+', ' ', texto).strip().lower()
        nfd = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
        texto = re.sub(r'[^a-z0-9ñ]+', '_', texto)
        texto = texto.strip('_')
        texto = re.sub(r'_+', '_', texto)
        
        clave_final = texto
        contador = 1
        original = texto
        
        while clave_final in self.claves_usadas:
            clave_final = f"{original}_{contador}"
            contador += 1
        
        self.claves_usadas.add(clave_final)
        return clave_final
    
    def limpiar(self, valor: str) -> str:
        if not isinstance(valor, str):
            return str(valor)
        return re.sub(r'\s+', ' ', valor).replace('\n', ' ').strip()
    
    def detectar_marcador(self, texto: str) -> bool:
        return texto.lower().strip() in ['x', '✓']
    
    def procesar_tabla(self, tabla: dict) -> dict:
        resultado = {}
        filas = tabla.get('rows', [])
        
        if not filas:
            return resultado
        
        for idx, fila in enumerate(filas):
            cells = fila.get('cells', [])
            contenidos = [self.limpiar(c.get('content', '')) for c in cells if c.get('content')]
            
            if not contenidos:
                continue
            
            if len(contenidos) == 1:
                contenido = contenidos[0]
                if len(contenido) >= 3 and not self.detectar_marcador(contenido):
                    clave = self.normalizar_clave(contenido)
                    resultado[clave] = contenido
            
            elif len(contenidos) == 2:
                clave_texto, valor_texto = contenidos[0], contenidos[1]
                
                if self.detectar_marcador(valor_texto) and len(clave_texto) >= 3:
                    clave = self.normalizar_clave(clave_texto)
                    resultado[clave] = clave_texto
                
                elif (len(clave_texto) >= 3 and len(valor_texto) >= 2 and 
                      not self.detectar_marcador(clave_texto) and 
                      not self.detectar_marcador(valor_texto)):
                    clave = self.normalizar_clave(clave_texto)
                    resultado[clave] = valor_texto
            
            elif len(contenidos) > 2:
                primer = contenidos[0]
                if len(primer) >= 3 and not self.detectar_marcador(primer):
                    if len(contenidos) == 3 and self.detectar_marcador(contenidos[-1]):
                        clave = self.normalizar_clave(primer)
                        resultado[clave] = primer
                    elif not all(self.detectar_marcador(c) for c in contenidos[1:]):
                        clave = self.normalizar_clave(primer)
                        valor = ' '.join(contenidos[1:])
                        resultado[clave] = valor
        
        return resultado
    
    def procesar(self) -> dict:
        if not self.cargar_json():
            return {}
        
        self.datos_planos['_metadata'] = {
            'archivo_original': self.datos_originales.get('file_name', ''),
            'fecha_procesamiento': datetime.now().isoformat(),
            'total_elementos': self.datos_originales.get('total_elements', 0)
        }
        
        elementos = self.datos_originales.get('elements', [])
        parrafos = []
        encabezados = []
        listas = {}
        
        for elemento in elementos:
            tipo = elemento.get('type', '')
            
            if tipo == 'table':
                tabla_datos = self.procesar_tabla(elemento)
                self.datos_planos.update(tabla_datos)
            
            elif tipo == 'paragraph':
                contenido = self.limpiar(elemento.get('content', ''))
                if len(contenido) >= 5:
                    parrafos.append(contenido)
            
            elif tipo == 'heading':
                contenido = self.limpiar(elemento.get('content', ''))
                if len(contenido) >= 3:
                    encabezados.append(contenido)
            
            elif tipo == 'list':
                items = [self.limpiar(i.get('content', '')) 
                        for i in elemento.get('items', []) if i.get('content')]
                if items:
                    elemento_id = elemento.get('id', len(listas))
                    listas[f"lista_{elemento_id}"] = items
        
        if parrafos:
            self.datos_planos['parrafos'] = parrafos
        if encabezados:
            self.datos_planos['encabezados'] = encabezados
        
        self.datos_planos.update(listas)
        
        return self.datos_planos
    
    def guardar(self, archivo_salida: str = None) -> str:
        if not archivo_salida:
            ruta = Path(self.archivo_json)
            ## Aca esta para cambiar el nombre 
            archivo_salida = str(ruta.parent / f"{ruta.stem}_PLANO2.json")
        
        try:
            with open(archivo_salida, 'w', encoding='utf-8') as f:
                json.dump(self.datos_planos, f, ensure_ascii=False, indent=2)
            return archivo_salida
        except Exception:
            return None
    
    def transformar(self) -> str:
        self.procesar()
        return self.guardar()


if __name__ == "__main__":
    archivo_entrada = "JSONObtenidos\documento_final_ordenado2.json"
    convertidor = SmartJSONConverter(archivo_entrada)
    archivo_salida = convertidor.transformar()
    
    if archivo_salida:
        print(f"✓ {Path(archivo_salida).name}")
```

---

Documentación ampliada: [`documentacion/flujo.md`](./documentacion/flujo.md)
(explicación detallada de cada paso y sus heurísticas) y
[`documentacion/scripts.md`](./documentacion/scripts.md) (referencia de
entradas/salidas de cada script).
