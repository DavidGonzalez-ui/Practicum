# Referencia de scripts

| Script | Entrada | Salida |
|--------|---------|--------|
| `_detectar_pdf.py` | — | función auxiliar (no se ejecuta solo) |
| `1_extraer_pdf_opendataloader.py` | `<cualquier>.pdf` | `JSONObtenidos/<nombre_pdf>.json` (+ `.md`) |
| `2_filtrar_contenido_sin_tablas.py` | JSON crudo del paso 1 | `JSONObtenidos/contenido_sin_tablas.json` |
| `3_construir_documento_final_ordenado.py` | PDF + JSON filtrado | `JSONObtenidos/documento_final_ordenado.json` |
| `4_aplanar_documento.py` | `documento_final_ordenado.json` | `JSONObtenidos/documento_aplanado.json` |

> **Nota:** las salidas de los pasos 2, 3 y 4 usan **nombres fijos** (no
> incluyen el nombre del PDF). Al procesar un segundo PDF, esas salidas se
> sobreescribirían. En esta entrega se procesaron dos PDF y, para conservar
> ambos juegos de resultados, los del segundo PDF (`DSOF_1067-O20F21.pdf`)
> se guardaron con el sufijo `Pdf2`. Ver el README para el detalle de qué
> archivo corresponde a cada PDF.

## `_detectar_pdf.py`

Función auxiliar usada por los scripts 1, 2 y 3 para que el flujo funcione
con **cualquier PDF**, sin nombres hardcodeados.

Reglas de detección:
1. Si se pasa un argumento por línea de comandos, se usa ese archivo.
2. Si no, busca los `.pdf` de la carpeta:
   - exactamente uno → lo usa;
   - varios → muestra un menú para elegir;
   - ninguno → lanza un error.

## `1_extraer_pdf_opendataloader.py` — Paso 1

Usa `opendataloader_pdf` (requiere Java) para leer el PDF y generar un JSON
con **todo** el contenido detectado: headings, paragraphs, lists, tables,
images, etc. Solo necesita ejecutarse **una vez**; si ya existe el JSON
crudo, se puede saltar directo al paso 2.

## `2_filtrar_contenido_sin_tablas.py` — Paso 2

Toma el JSON crudo y conserva únicamente `heading`, `paragraph` y `list`
(descarta `image`, `table` y otros). Este es el "texto" del documento antes
de mezclarlo con las tablas extraídas aparte en el paso 3. Si no encuentra
el JSON con el nombre exacto del PDF, busca cualquier JSON con forma "cruda"
(claves `file name` y `kids` en la raíz) que no haya generado el propio flujo.

## `3_construir_documento_final_ordenado.py` — Paso 3

Genera **un solo** JSON unificado con:
- texto (heading/paragraph/list) limpio, sin duplicados de tablas;
- tablas con id canónico `T{pagina}_{numero}`;
- todo ordenado por **posición visual real** (bounding box), no por orden
  de extracción.

Ver [`flujo.md`](./flujo.md) para el detalle de la conversión de coordenadas.

## `4_aplanar_documento.py` — Paso 4 (final)

Aplanador **100% genérico y recursivo**: convierte cualquier árbol JSON
anidado en una lista plana de filas con `id`, `parent_id`, `order`, `type`
y `source_id` (más los campos simples como `content`, `page_number`...).
No asume nada sobre la estructura del documento.
