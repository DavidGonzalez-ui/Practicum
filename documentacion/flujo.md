# Explicación detallada del flujo

En este documento explicamos el porqué de cada paso, con los ejemplos reales de los
dos PDF que se procesaron. La meta final del flujo es llegar a un solo
diccionario clave:valor, sin metadata, que se pueda subir directo a MongoDB.

El flujo completo es:

```
PDF -> (1) JSON crudo -> (2) solo texto -> (3) documento ordenado -> (4) clave:valor para Mongo
```

## 1) Extracción cruda

La librería opendataloader_pdf (que corre en Java) se encarga de analizar el PDF
y devuelve un árbol de JSON con todo lo que detecta: heading, paragraph, list,
table, image, cada uno con su página y su bounding box respectiva. También genera una
versión en Markdown y extrae las imágenes (6 en el DSOF y 1 en el PLAN).

¿Por qué no nos quedamos con este JSON y ya? Por dos razones. Primero, sus tablas
no siempre respetan la estructura visual real del PDF. Y segundo, el orden en
que entrega los elementos no siempre coincide con el orden en que se lee el
documento. Para eso existen los pasos 2 y 3.

## 2) Filtrar solo el texto

De todo el JSON crudo se conservan solo heading, paragraph y list. Las tablas
se descartan a propósito: en el paso 3 se vuelven a extraer con pdfplumber,
que da mejor estructura de filas y columnas y, sobre todo, la posición exacta
de cada tabla en la página.

Los números reales serian: 23 elementos de texto en el DSOF y 314 en el PLAN.

## 3) Tablas reales y orden de lectura

### El problema de las coordenadas

Las dos fuentes usan sistemas de coordenadas distintos:

- opendataloader_pdf entrega el texto con su bounding box en coordenadas PDF:
  el origen está abajo a la izquierda y la Y crece hacia arriba.
- pdfplumber (con `find_tables`) en cambio, entrega cada tabla en su propio sistema: el
  origen está arriba a la izquierda y el valor `top` crece hacia abajo.

La conversión que une ambos sistemas es una sola línea:

```
y_top = page.height - top      # borde superior de la tabla, en coords PDF
```

Con todo en el mismo sistema, se ordena cada página de arriba hacia abajo
(Y descendente) y, si dos elementos están a la misma altura, de izquierda a
derecha (X ascendente):

```python
sorted(elementos, key=lambda e: (e["page_number"], -e["y_top"], e["x0"]))
```

Con eso reconstruimos el orden de lectura real: cada tabla queda intercalada
exactamente entre el texto que la precede y el que la sigue en el PDF.

### Los duplicados, en tres niveles

opendataloader_pdf a veces reporta como párrafo o heading un texto que en
realidad es el contenido de una celda. Para no repetir la información, cada
texto se compara contra las tablas de su misma página en tres niveles:

1. coincidencia exacta con una celda (normalizando espacios y mayúsculas);
2. contención dentro del texto concatenado de toda la tabla;
3. contención dentro de una celda individual.

En el PLAN esto eliminó 280 duplicados, y quedaron 34 elementos de texto
legítimos junto a las 80 tablas (114 elementos en total).

## 4) Aplanado clave:valor para MongoDB

Es el paso con más lógica propia (`aplanar_para_mongo_generico.py`). Trabaja
en tres fases.

### A) Reconstruir las tablas cortadas por página

Los PDF cortan las tablas al cambiar de página, y pdfplumber las devuelve
como si fueran tablas separadas. Antes de interpretarlas, el script las
reconstruye basandose en estas tres reglas:

- Título duplicado: si una "tabla" es una sola fila de una celda cuyo texto
  repite exacto el título con el que terminó la tabla anterior (un artefacto
  típico del salto de página), se descarta.
- Título colgante: si la tabla anterior terminó en una fila-título de una
  celda (por ejemplo "Semana 6") y la tabla siguiente no abre con un título
  propio, sus filas se pegan a la anterior, porque ese contenido pertenecía
  al título que quedó colgando.
- Matriz cortada: si en la nueva tabla ninguna celda usa la columna 1, es la
  continuación de una tabla tipo matriz (como el horario de clases). Se
  fusiona usando el número de columna; si es una sola fila, su texto se
  concatena a las celdas correspondientes de la última fila anterior.

### B) Interpretar cada tabla

Hay dos tipos de tabla, y el script los detecta solo:

- Tabla matriz (`is_matrix_table`): la primera fila tiene 3 o más celdas que
  no terminan en dos puntos, o sea que son encabezados de columna (el caso
  del horario de clases). Se convierte en una lista de registros
  {encabezado: valor}, usando el número de columna para emparejar cada celda
  con su columna real. Cuando a una fila le falta la primera columna es
  porque en el PDF esa celda estaba combinada verticalmente con la de arriba
  (rowspan, como pasa con la columna "Componente"); en ese caso se hereda el
  valor de la fila anterior, igual que se ve en el PDF.
- Tabla formulario (`parse_form_table`): todas las demás. Se aplica la regla
  padre-hijo: una fila de una sola celda (por ejemplo "A. Datos básicos de la
  asignatura") es el padre de las filas que siguen, hasta la próxima fila de
  una celda. Dentro de cada bloque, una fila de dos celdas es un par
  clave:valor directo; con tres o más celdas, la primera funciona como
  mini-título y el resto se agrupa en pares. Una celda marcada con "x" o "✓"
  significa que esa opción está seleccionada, y se guarda la etiqueta.

### C)  El texto y el armado de secciones

- Un heading normalmente abre una sección raíz nueva. Pero si trae el patrón
  "Etiqueta: valor" (como "ÁREA ACADÉMICA: Técnica"), en realidad es un campo
  de la sección actual, y se guarda como `area_academica: "Técnica"`.
- Un párrafo se clasifica según su forma: si termina en dos puntos es un
  título de sección (como "Fechas importantes:"); si termina en punto, coma o
  punto y coma es contenido; si es corto (10 palabras o menos) y viene justo
  antes de una tabla o lista, se toma como el título que las agrupa; y en
  cualquier otro caso es contenido.
- Las listas se guardan como `lista_N: [items]` dentro de la sección actual.
- La función `merge_section_content` va uniendo todo sin perder datos, aunque
  los tipos no calcen (por ejemplo un dict existente con una lista nueva).

### Claves seguras y sin pérdida de datos

- `clean_key()` normaliza solo las claves, nunca los valores: quita tildes,
  reemplaza cualquier símbolo por guión bajo (los puntos rompen la notación
  seccion.campo de Mongo) y deja todo en snake_case en minúsculas.
- `add_unique()` evita sobrescribir: si una clave se repite, convierte el
  valor en una lista y va acumulando.

### El resultado

Un solo documento JSON por cada PDF, con las secciones del documento como
claves raíz. Los reales de esta entrega:

- DSOF: 11 secciones raíz (`a_datos_de_identificacion_de_la_asignatura`,
  `b_descripcion_general_de_la_asignatura`, `c_resultados_de_aprendizaje...`,
  `d_contenidos`, `e_metodologia`, etc.)
- PLAN: 13 secciones raíz (`horario_de_clases`,
  `b_datos_basicos_del_docente`, `c_competencias_a_desarrollar`,
  `d_planificacion_general_de_la_asignatura_primer_bimestre`,
  `fechas_importantes`, etc.)
