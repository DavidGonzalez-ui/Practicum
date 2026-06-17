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

