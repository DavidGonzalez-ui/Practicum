# Practicum 1.2 — Extracción estructurada de un PDF a JSON

A continuación se muestra el flujo completo que toma un archivo PDF, extrae todo su contenido, lo limpia, lo ordena según
el orden de lectura del documento y lo transforma en un único
diccionario jerárquico de tipo `clave: valor` listo para subir a MongoDB.

Las herramientas usadas fueron: 

* **opendataloader_pdf**:
Se usa para la extracción inicial y requiere Java.
(https://github.com/opendataloader-project/opendataloader-pdf))

* **pdfplumber**: Para la re-extracción de tablas
con su posición real.
(https://github.com/jsvine/pdfplumber) 

## Cómo se guardan los resultados

Algo importante de entender antes de ver el proceso es que el flujo trabaja con
un solo archivo JSON por PDF, que se va sobrescribiendo en cada paso en
lugar de ir creando un archivo nuevo cada vez. Ese archivo es
`JSONObtenidos/<nombre_pdf>.json` y va cambiando así:

```
paso 1  ->  contenido crudo que devuelve opendataloader_pdf
paso 2  ->  se sobrescribe: solo heading, paragraph y list
paso 3  ->  se sobrescribe: texto + tablas, ordenado por posición visual
paso 4  ->  se sobrescribe: documento aplanado final, con su metadata
paso 5  ->  ese mismo archivo se sube a MongoDB
```

La ventaja es que no quedan archivos intermedios regados por la carpeta, y
siempre se sabe cuál es el archivo de trabajo de cada PDF. La contra es que
si se quiere conservar el estado de un paso intermedio, hay que copiarlo
aparte antes de seguir.

En `JSONObtenidos/` de este repositorio están los JSON de los dos PDF que nos
facilitó el docente tutor, junto con su versión en Markdown y las imágenes
que se extrajeron de cada uno.

## Resultados obtenidos

Corrimos el flujo completo sobre los dos PDF que nos facilitó el docente
tutor. Estos son los documentos que quedaron en `JSONObtenidos/`:

| | `DSOF_1067-O20F21.pdf` | `PLAN_3952-DSOF_1067.pdf` |
|---|---|---|
| Secciones raíz (sin contar metadata) | 9 | 8 |
| Secciones que son lista de registros | 3 (`d_contenidos`, `f_procedimientos_de_evaluacion`, `h_elaboracion_y_aprobacion`) | 1 (`horario_de_clases`, dentro de la sección A) |
| Subsecciones anidadas | `g_bibliografia` con `basica` y `complementaria` | ninguna |
| Sección más grande | `a_datos_de_identificacion_de_la_asignatura`, con 14 campos | `d_planificacion_general_de_la_asignatura_primer_bimestre`, con 54 campos |

Un pedazo del resultado del DSOF, para que se vea a qué se llega:

```json
{
  "metadata": {
    "archivo_origen": "DSOF_1067-O20F21.pdf",
    "universidad": "UNIVERSIDAD TÉCNICA PARTICULAR DE LOJA",
    "modalidad": "Presencial",
    "lugar": "Loja – Ecuador",
    "anio_documento": "2020",
    "area_academica": "Técnica",
    "carrera": "Computación",
    "asignatura": "Introducción a la programación"
  },
  "a_datos_de_identificacion_de_la_asignatura": {
    "asignatura": "Introducción a la programación",
    "modalidad_de_estudio": "Presencial",
    "codigo": "DSOF_1067",
    "numero_de_credito_horas": { "credito": "3", "horas": "144" }
  }
}
```

Las claves quedan en snake_case, sin tildes ni símbolos, porque los puntos y
caracteres raros rompen las consultas con notación de puntos en Mongo. Los
valores no se tocan, conservan el texto tal como viene en el PDF.

En el PLAN se puede ver funcionando la lógica de tablas matriz. El horario de
clases quedó como una lista de registros, y el nombre del docente se repite
en cada uno porque en el PDF esa celda estaba combinada verticalmente:

```json
"horario_de_clases": [
  { "docente": "RENE ROLANDO ELIZALDE SOLANO", "paralelo": "A",
    "dia": "MIERCOLES", "horario": "03:00 PM-04:59 PM0 (CLAS)" },
  { "docente": "RENE ROLANDO ELIZALDE SOLANO", "paralelo": "A",
    "dia": "JUEVES", "horario": "03:00 PM-04:59 PM0 (PRAC)" }
]
```


## Estructura del repositorio

```
Practicum1.2/
├── scripts/                       
│   ├── _detectar_pdf.py               
│   ├── 1_extraer_pdf_opendataloader.py   
│   ├── 2_filtrar_contenido_sin_tablas.py  
│   ├── 3_construir_documento_final_ordenado.py  
│   └── aplanar_para_mongo_generico.py     
├── pdfs_entrada/                  
├── JSONObtenidos/                 
├── documentacion/                
├── requirements.txt
└── README.md
```

## Requisitos e instalación

- Python 3.12+
- Java instalado y en el `PATH` (es necesario para el `opendataloader_pdf`).
- Dependencias de Python:

```bash
pip install -r requirements.txt
```

(Se instala `opendataloader_pdf` y `pdfplumber`; el resto es librería estándar.)

## Proceso replicable paso a paso

Antes de empezar, se copia el PDF a procesar y los scripts a una sola carpeta
de trabajo, porque los scripts buscaran el `.pdf` en la carpeta actual. La
carpeta `JSONObtenidos/` se crea sola en el paso 1. Todos los comandos se
corren desde esa carpeta.

### 1) Extracción cruda con opendataloader_pdf

```bash
1_extraer_pdf_opendataloader.py
```

Si hay un solo PDF en la carpeta lo detecta solo. Si hay varios, muestra un
menú numerado para elegir. También se le puede pasar el archivo directamente:
`python 1_extraer_pdf_opendataloader.py PLAN_3952-DSOF_1067.pdf`.

Esto genera `JSONObtenidos/<nombre_pdf>.json` con todo lo que la librería
detecta (ya sean headings, paragraphs, lists, tables, images), más una versión en
Markdown y una carpeta `<nombre_pdf>_images/` que cuenta con las imágenes del PDF.

### 2) Filtrar solo el texto

```bash
2_filtrar_contenido_sin_tablas.py
```

Lee el JSON crudo del PDF detectado y se queda solo con los elementos de tipo
`heading`, `paragraph` y `list`. Las tablas se descartan aquí a propósito,
porque en el paso 3 se vuelven a extraer con pdfplumber, que las saca mejor.

El archivo que se genera es `JSONObtenidos/contenido_sin_tablas2.json`. Con
el PLAN la consola reporta 314 elementos filtrados; con el DSOF salen 23.

### 3) Re-extraer tablas e intercalar por posición real

```bash
3_construir_documento_final_ordenado.py
```

Este paso vuelve a extraer todas las tablas con pdfplumber (esta vez con su
bounding box), elimina los párrafos y headings que en realidad son texto que
ya está dentro de una tabla, y ordena todo (tanto texto como tablas juntos) por la
posición en que aparece en cada página.

Esto genera el archivo: `JSONObtenidos/documento_final_ordenado2.json`. Este fue el reporte
real al correrlo con el PLAN:

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

### 4) Aplanar a clave: para subir a MongoDB

```bash
python aplanar_para_mongo_generico.py JSONObtenidos/documento_final_ordenado2.json JSONObtenidos/documento_para_mongo_generico.json
```

Este script recibe la entrada y la salida como argumentos. Convierte el
documento ordenado en un solo diccionario jerárquico clave:valor, sin campos
de metadata, nada de `type`, `id`, ni `page_number`, con las claves ya
normalizadas para su subida a Mongo.

Así se generaron los dos resultados incluidos en este repositorio:

```bash
# PDF 1 (DSOF)
JSONObtenidos/documento_final_ordenado1_para_mongo.json

# PDF 2 (PLAN)
JSONObtenidos/documento_para_mongo_generico.json
```

### 5) Subir a MongoDB

El JSON final es un solo documento, así que se puede importar de manera directa:

```bash
mongoimport --db practicum --collection asignaturas --file JSONObtenidos/documento_para_mongo_generico.json
```

### Procesar un segundo PDF

Los pasos 2 y 3 escriben siempre los mismos nombres de archivo
(`contenido_sin_tablas2.json` y `documento_final_ordenado2.json`), así que si
se corre el flujo con otro PDF, la segunda corrida pisa a la primera. La
solución sería renombrar las salidas antes de procesar el siguiente PDF. Así se
hizo en esta entrega: las salidas del DSOF se guardaron sin el sufijo 2 y las
del PLAN con él.

## Cómo funciona

La explicación completa está en
[`documentacion/flujo.md`](./documentacion/flujo.md). Acá va lo esencial.

* El orden de lectura (paso 3). El problema es que opendataloader_pdf da la
posición del texto en coordenadas PDF (el origen está abajo a la izquierda y
la Y crece hacia arriba), mientras que pdfplumber da la posición de las
tablas al revés (origen arriba a la izquierda, `top` crece hacia abajo). La
solución fue convertir el bbox de cada tabla con
`y_top = page.height - top`, con lo que texto y tablas quedan en el mismo
sistema y se puede ordenar cada página de arriba hacia abajo. Así cada tabla
queda intercalada justo donde va en el documento.

* Los duplicados (paso 3). A veces opendataloader_pdf reporta como párrafo o
heading un texto que en realidad es el contenido de una celda. Para no
duplicar, cada texto se compara contra las tablas de su misma página en tres
niveles: si coincide exacto con una celda, si está contenido en el texto
completo de la tabla, o si está contenido dentro de una celda. En el PLAN
esto eliminó 280 duplicados.

* Las tablas cortadas por página (paso 4). Los PDF cortan las tablas al cambiar
de página y pdfplumber las devuelve a manera de tablas separadas. Antes de
interpretarlas, el script las reconstruye, descarta los títulos que se
repiten por el salto de página, pega el contenido que quedó separado de su
título (el caso típico es que un título como "Semana 6" queda solo al final
de una tabla y sus datos caen en la siguiente), y fusiona las tablas tipo
matriz que quedaron partidas, usando el número de columna.

* La interpretación de tablas (paso 4). Aquí hay dos casos. Si la tabla es una
matriz (con encabezados de columna de verdad, como el horario de clases), se
convierte en una lista de registros; cuando a una fila le falta la primera
columna es porque en el PDF esa celda estaba combinada con la de arriba
(rowspan, como pasa con la columna "Componente"), y se hereda el valor de la
fila anterior. Si la tabla es tipo formulario, se aplica la regla padre-hijo:
una fila de una sola celda (como "A. Datos básicos de la asignatura") es el
padre de las filas que siguen, y cada fila de dos celdas es un par
clave:valor.

* El texto (paso 4). Un heading o párrafo con el patrón "Etiqueta: valor"
(como "ÁREA ACADÉMICA: Técnica") se convierte en un campo de la sección
actual. Un párrafo que termina en dos puntos, o que es corto y viene justo
antes de una tabla o lista, se trata como título de sección (por ejemplo
"Fechas importantes:"). El resto se guarda como contenido.

* Las claves (paso 4). La función `clean_key()` normaliza solo las claves
(nunca los valores): quita las tildes, cambia cualquier símbolo por guión bajo y
pasa todo a minúsculas. Y `add_unique()` evita perder datos: si una clave se
repite, en lugar de sobrescribir agrupa los valores en una lista.

## Notas de replicabilidad

- Los scripts se ejecutan desde la carpeta donde está el PDF; las rutas de
  salida (`JSONObtenidos/...`) son relativas a la carpeta actual.
- Hay que tener cuidado con los mensajes en consola de los pasos 2 y 3: muestran los nombres
  sin el sufijo 2 (`contenido_sin_tablas.json`,
  `documento_final_ordenado.json`), pero los archivos que realmente se
  escriben son `contenido_sin_tablas2.json` y
  `documento_final_ordenado2.json`. El flujo entre pasos sí es consistente,
  el paso 3 lee exactamente lo que escribe el paso 2.
- `aplanar_para_mongo_generico.py` recibe las rutas por argumento, así que
  funciona igual tanto en Windows, Linux y Mac.
- El paso 1 falla si Java no está instalado o no está en el PATH.

## Código

Este es el código de cada script, tal como se usó para generar los resultados
de `JSONObtenidos/`.

### `_detectar_pdf.py`

Auxiliar que usan los pasos 1, 2 y 3. Si se pasa un PDF por argumento usa
ese; si no, busca los `.pdf` de la carpeta actual: si hay uno lo toma, si hay
varios muestra un menú y si no hay ninguno lanza un error. La función
`nombre_base()` devuelve el nombre del archivo sin extensión, que sirve para
nombrar las salidas del paso 1.

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

### `1_extraer_pdf_opendataloader.py`

Crea la carpeta `JSONObtenidos/` si no existe y llama a
`opendataloader_pdf.convert()`, que genera el JSON crudo con todo el
contenido detectado, la versión Markdown y las imágenes del PDF.

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

### `2_filtrar_contenido_sin_tablas.py` 

Este se encarga de buscar el JSON crudo del PDF detectado (`JSONObtenidos/<nombre_pdf>.json`) y
se queda solo con los elementos de texto: heading, paragraph y list.

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

### `3_construir_documento_final_ordenado.py` 

Se encarga de re-extraer las tablas con pdfplumber guardando su bounding box, limpia las
celdas vacías, elimina el texto duplicado (los tres niveles de comparación) y
ordena todos los elementos por página, Y descendente y X ascendente, que es
el orden en que se lee el documento.

```python
import json
import pdfplumber
from _detectar_pdf import detectar_pdf

PDF_PATH = detectar_pdf()
print(f"PDF: {PDF_PATH}")

#Re-extraer tablas con bbox

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

# Cargar texto

with open("JSONObtenidos/contenido_sin_tablas2.json", "r", encoding="utf-8") as f:
    contenido = json.load(f)

elementos_texto = contenido["kids"]
print(f"Elementos de texto: {len(elementos_texto)}")

#  Índices para detección de duplicados (3 niveles) 
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

#  Serializar texto sobreviviente 

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

#  Unir + ordenar por posición visual 

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

### `aplanar_para_mongo_generico.py`

Este es el paso final. Reconstruye las tablas que quedaron cortadas por los saltos de
página, interpreta cada tabla como matriz o como formulario padre-hijo,
clasifica los párrafos en título o contenido, y arma el diccionario
clave:valor con las claves normalizadas para Mongo. Se usa así:
`python aplanar_para_mongo_generico.py entrada.json salida.json`.

```python
import json
import re
import sys
import unicodedata


def clean_key(text) -> str:

    if text is None:
        return "campo"
    key = str(text).strip()
    key = unicodedata.normalize("NFKD", key)
    key = "".join(c for c in key if not unicodedata.combining(c))  # quita tildes
    key = re.sub(r"[^A-Za-z0-9]+", " ", key)  # cualquier símbolo (incluye '.') -> espacio
    key = re.sub(r"\s+", "_", key.strip())
    return key.lower() if key else "campo"


def add_unique(target: dict, key: str, value):
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
    if not text:
        return None
    m = _EMBEDDED_KV.match(text.strip())
    if not m:
        return None
    etiqueta, valor = m.group(1).strip(), m.group(2).strip()
    if not etiqueta or not valor:
        return None
    return clean_key(etiqueta), valor


def _es_titulo_duplicado(actual, anterior):
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
    rows = table.get("rows") or []
    if not rows or is_matrix_table(rows):
        return False
    if len(rows[-1].get("cells", [])) != 1:
        return False
    if len(rows) == 1:
        return True
    return len(rows[-2].get("cells", [])) >= 2


def _empieza_sin_titulo(table):
    rows = table.get("rows") or []
    return bool(rows) and len(rows[0].get("cells", [])) != 1


def _es_continuacion_de_matriz(table):
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

---

La documentación ampliada y a mejor detalle está en
[`documentacion/flujo.md`](./documentacion/flujo.md) y en [`documentacion/scripts.md`](./documentacion/scripts.md)
hay referencia de entradas y salidas de cada script.
