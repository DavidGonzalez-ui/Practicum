# Referencia de scripts

| Script | Entrada | Salida real |
|--------|---------|-------------|
| `_detectar_pdf.py` | — | auxiliar (no se ejecuta solo) |
| `1_extraer_pdf_opendataloader.py` | `<pdf>` detectado o por argumento | `JSONObtenidos/<nombre_pdf>.json`, `<nombre_pdf>.md`, `<nombre_pdf>_images/` |
| `2_filtrar_contenido_sin_tablas.py` | `JSONObtenidos/<nombre_pdf>.json` | `JSONObtenidos/contenido_sin_tablas2.json` |
| `3_construir_documento_final_ordenado.py` | PDF + `contenido_sin_tablas2.json` | `JSONObtenidos/documento_final_ordenado2.json` |
| `aplanar_para_mongo_generico.py` | por argumento (documento ordenado) | por argumento (JSON clave:valor para Mongo) |

## `_detectar_pdf.py`

Es lo que hace que el flujo sirva para cualquier PDF sin tocar el código.
`detectar_pdf()` usa el argumento de línea de comandos si se le pasó uno; si
no, busca los `.pdf` de la carpeta actual: con uno solo lo toma directo, con
varios muestra un menú numerado, y si no hay ninguno lanza un
FileNotFoundError. `nombre_base()` le quita la ruta y la extensión al
archivo.

## `1_extraer_pdf_opendataloader.py` 

Crea la carpeta `JSONObtenidos/` si no existe y llama a
`opendataloader_pdf.convert()` con `format="markdown,json"`. Necesita Java en
el PATH. Genera el JSON crudo, la versión en Markdown y la carpeta de
imágenes del PDF.

## `2_filtrar_contenido_sin_tablas.py` 

Arma la ruta del JSON crudo a partir del nombre del PDF detectado; si no
existe, avisa que primero hay que correr el paso 1. Filtra el arreglo `kids`
dejando solo heading, paragraph y list, y guarda el resultado (con la forma
`{"file_name": ..., "kids": [...]}`) en `contenido_sin_tablas2.json`.

Números reales: 23 elementos con el DSOF y 314 con el PLAN.

## `3_construir_documento_final_ordenado.py` 

Hace cuatro cosas, en este orden:

1. Recorre el PDF con pdfplumber y por cada tabla que encuentra
   (`page.find_tables()`) guarda su id con el formato `T{página}_{n}`, sus
   filas limpias (sin celdas vacías y con las columnas renumeradas) y su
   posición, convertida con `y_top = page.height - top`.
2. Carga el texto del paso 2 y elimina el que está duplicado dentro de alguna
   tabla de su misma página, comparando en tres niveles: celda exacta, texto
   concatenado de la tabla, y dentro de una celda.
3. Une texto y tablas y ordena todo por página, Y descendente y X ascendente.
4. Exporta `{"file_name", "total_elements", "elements"}` sin los campos
   auxiliares de posición.

Números reales: el DSOF quedó en 28 elementos (12 heading, 7 paragraph,
5 table, 4 list) y el PLAN en 114 (12 heading, 7 paragraph, 80 table,
15 list), con 280 duplicados eliminados.

## `aplanar_para_mongo_generico.py` 

Se usa así: `python aplanar_para_mongo_generico.py entrada.json salida.json`.
Convierte el documento ordenado en un solo diccionario jerárquico clave:valor
listo para MongoDB. Por dentro:

- `preparar_tablas()` reconstruye las tablas que quedaron cortadas por los
  saltos de página (título duplicado, título colgante, matriz cortada).
- `is_matrix_table()` decide si una tabla es matriz (con encabezados de
  columna) o formulario. `parse_matrix_table()` produce registros y hereda
  las celdas combinadas de la fila anterior (rowspan);
  `parse_form_table()` aplica la regla padre-hijo, donde una fila de una
  celda es el título del bloque.
- Los headings y párrafos con el patrón "Etiqueta: valor" se vuelven campos;
  los párrafos se clasifican en título o contenido; las listas se numeran
  como `lista_N`.
- `clean_key()` normaliza las claves (snake_case, sin tildes ni símbolos) y
  `add_unique()` acumula en lista en vez de sobrescribir cuando una clave se
  repite.

Números reales: con el DSOF se generó
`documento_final_ordenado1_para_mongo.json` y con el PLAN
`documento_para_mongo_generico.json`.
