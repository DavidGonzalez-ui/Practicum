# Referencia de scripts

| Script | Entrada | Salida real |
|--------|---------|-------------|
| `_detectar_pdf.py` | — | auxiliar (no se ejecuta solo) |
| `1_extraer_pdf_opendataloader.py` | `<pdf>` detectado o por argumento | `JSONObtenidos/<nombre_pdf>.json`, `<nombre_pdf>.md`, `<nombre_pdf>_images/` |
| `2_filtrar_contenido_sin_tablas.py` | `JSONObtenidos/<nombre_pdf>.json` | `JSONObtenidos/contenido_sin_tablas2.json` |
| `3_construir_documento_final_ordenado.py` | PDF + `contenido_sin_tablas2.json` | `JSONObtenidos/documento_final_ordenado2.json` |
| `aplanar_para_mongo_generico.py` | por argumento (documento ordenado) | por argumento (JSON clave:valor p/ Mongo) |
| `4_aplanar_documento.py` | `JSONObtenidos\documento_final_ordenado2.json` (ruta Windows) | `<entrada>_PLANO2.json` |

## `_detectar_pdf.py`

Hace el flujo válido para **cualquier PDF** sin tocar código:
`detectar_pdf()` usa el argumento de línea de comandos si existe; si no,
busca `*.pdf` en la carpeta actual (uno → lo usa; varios → menú numerado;
ninguno → `FileNotFoundError`). `nombre_base()` quita ruta y extensión.

## `1_extraer_pdf_opendataloader.py` — Paso 1

Crea `JSONObtenidos/` (`os.makedirs(..., exist_ok=True)`) y llama a
`opendataloader_pdf.convert(input_path=[pdf], output_dir="JSONObtenidos",
format="markdown,json")`. Requiere **Java** en el `PATH`. Genera el JSON
crudo, el Markdown y la carpeta de imágenes del PDF.

## `2_filtrar_contenido_sin_tablas.py` — Paso 2

Arma la ruta del JSON crudo a partir del nombre del PDF detectado; si no
existe, avisa que hay que ejecutar primero el paso 1. Filtra `kids` dejando
solo `heading` / `paragraph` / `list` y guarda
`{"file_name": ..., "kids": [...]}` en `contenido_sin_tablas2.json`.

Reales: DSOF → 23 elementos; PLAN → 314 elementos.

## `3_construir_documento_final_ordenado.py` — Paso 3

1. Recorre el PDF con `pdfplumber` y por cada `page.find_tables()` guarda la
   tabla con id `T{página}_{n}`, sus filas limpias (celdas vacías fuera,
   columnas renumeradas) y su posición (`y_top = page.height - top`).
2. Carga el texto del paso 2 y elimina el que está duplicado dentro de alguna
   tabla de su misma página (3 niveles: celda exacta, concatenado de la
   tabla, dentro de una celda).
3. Une texto + tablas y ordena por `(página, −y_top, x0)`.
4. Exporta `{"file_name", "total_elements", "elements"}` sin los campos
   auxiliares de posición.

Reales: DSOF → 28 elementos (12 heading, 7 paragraph, 5 table, 4 list);
PLAN → 114 elementos (12 heading, 7 paragraph, 80 table, 15 list),
280 duplicados eliminados.

## `aplanar_para_mongo_generico.py` — Paso 4 (final)

Uso: `python aplanar_para_mongo_generico.py entrada.json salida.json`.
Convierte el documento ordenado en **un único diccionario jerárquico
clave:valor** listo para MongoDB:

- `preparar_tablas()` reconstruye las tablas cortadas por los saltos de
  página (título duplicado, título colgante, matriz cortada).
- `is_matrix_table()` decide si una tabla es matriz (encabezados de columna)
  o formulario; `parse_matrix_table()` produce registros heredando celdas
  combinadas (*rowspan*); `parse_form_table()` aplica la regla padre-hijo
  (fila de 1 celda = título del bloque).
- Los headings/párrafos con `Etiqueta: valor` se vuelven campos; los párrafos
  se clasifican en título o contenido; las listas se numeran `lista_N`.
- `clean_key()` normaliza las claves (snake_case, sin tildes ni símbolos) y
  `add_unique()` acumula en lista en vez de sobrescribir.

Reales: DSOF → `documento_final_ordenado1_para_mongo.json` (11 secciones
raíz); PLAN → `documento_para_mongo_generico.json` (13 secciones raíz).

## `4_aplanar_documento.py` — Conversor alternativo

Clase `SmartJSONConverter`: versión previa del aplanado clave:valor.
Interpreta cada tabla fila por fila según el número de celdas (1 celda →
`otros_elementos`; 2 → `clave: valor`; 3+ → mini-título + valores), detecta
marcadores `x`/`✓`, y agrupa `parrafos`, `encabezados` y `lista_N` con un
bloque `_metadata`. Entrada hardcodeada con ruta Windows
(`JSONObtenidos\documento_final_ordenado2.json`; en Linux/Mac cambiar a `/`)
y salida `<entrada>_PLANO2.json`. Se conserva como alternativa: los
resultados entregados se generaron con `aplanar_para_mongo_generico.py`.
