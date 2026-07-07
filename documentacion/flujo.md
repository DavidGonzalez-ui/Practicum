# Explicación detallada del flujo

Este documento amplía el **porqué** de cada paso, con los ejemplos reales de
los dos PDF procesados. El objetivo final del flujo es obtener un único
diccionario jerárquico `clave: valor`, sin metadata, listo para MongoDB.

```
PDF ──1──► JSON crudo ──2──► solo texto ──3──► documento ordenado ──4──► clave:valor p/ Mongo
```

## Paso 1 — Extracción cruda

`opendataloader_pdf` (motor Java) analiza el PDF y devuelve un árbol JSON con
todo lo que detecta: `heading`, `paragraph`, `list`, `table`, `image`, cada
uno con su página y su *bounding box*. También genera una versión Markdown y
extrae las imágenes (6 en `DSOF_1067-O20F21.pdf`, 1 en
`PLAN_3952-DSOF_1067.pdf`).

¿Por qué no quedarse con este JSON? Dos razones: (a) sus tablas no siempre
respetan la estructura visual real, y (b) el orden de los elementos no
siempre coincide con el orden de lectura. De ahí los pasos 2 y 3.

## Paso 2 — Filtrar solo el texto

Se conservan únicamente `heading`, `paragraph` y `list`. Las tablas se
descartan **a propósito**: en el paso 3 se re-extraen con `pdfplumber`, que
da mejor estructura de filas/columnas y, sobre todo, la posición exacta de
cada tabla en la página.

Resultados reales: 23 elementos de texto en DSOF, 314 en PLAN.

## Paso 3 — Tablas reales + orden de lectura

### El problema de las coordenadas

Las dos fuentes usan sistemas distintos:

- `opendataloader_pdf` entrega el texto con bounding box en **coordenadas
  PDF**: origen abajo-izquierda, la Y **crece hacia arriba**.
- `pdfplumber` (`find_tables`) entrega cada tabla con bbox en su propio
  sistema: origen arriba-izquierda, `top` **crece hacia abajo**.

La conversión que los unifica:

```
y_top = page.height - top      # borde superior de la tabla, en coords PDF
```

Con todo en el mismo sistema, se ordena cada página por Y descendente (de
arriba hacia abajo) con desempate por X ascendente (izquierda a derecha):

```python
sorted(elementos, key=lambda e: (e["page_number"], -e["y_top"], e["x0"]))
```

Eso reconstruye el **orden de lectura real**: cada tabla queda intercalada
exactamente entre el texto que la precede y el que la sigue en el PDF.

### Duplicados en 3 niveles

`opendataloader_pdf` a veces reporta como párrafo o heading texto que en
realidad es el contenido de una celda. Para no duplicar, cada texto se
compara contra las tablas de **su misma página** en 3 niveles:

1. coincidencia exacta con una celda (normalizando espacios y mayúsculas);
2. contención dentro del texto concatenado de toda la tabla;
3. contención dentro de una celda individual.

En PLAN esto eliminó **280 duplicados**, dejando 34 elementos de texto
legítimos junto a las 80 tablas (114 elementos totales).

## Paso 4 — Aplanado clave:valor para MongoDB

Es el paso con más lógica propia (`aplanar_para_mongo_generico.py`). Trabaja
en tres fases:

### Fase A — Reconstruir tablas cortadas por página

Los PDF cortan tablas al cambiar de página, y `pdfplumber` las devuelve como
tablas separadas. Tres heurísticas las reconstruyen **antes** de
interpretarlas:

- **Título duplicado**: si una "tabla" es una sola fila de 1 celda cuyo texto
  repite exactamente el título con el que terminó la tabla anterior
  (artefacto del salto de página), se descarta.
- **Título colgante**: si la tabla anterior terminó en una fila-título de 1
  celda (p. ej. `Semana 6`) y la siguiente tabla **no** abre con título
  propio, sus filas se pegan a la anterior: ese contenido pertenecía al
  título que quedó colgando.
- **Matriz cortada**: si en la nueva tabla ninguna celda usa la columna 1, es
  la continuación de una tabla-matriz (p. ej. horarios). Se fusiona por
  `column_number`; si es una única fila, su texto se concatena a las celdas
  correspondientes de la última fila anterior.

### Fase B — Interpretar cada tabla

Dos tipos, detectados automáticamente:

- **Tabla-matriz** (`is_matrix_table`): la primera fila tiene 3+ celdas que
  no terminan en `:` — son encabezados de columna (p. ej. el horario de
  clases). Se convierte en una **lista de registros** `{encabezado: valor}`
  usando `column_number` para emparejar cada celda con su columna real.
  Si a una fila le falta la primera columna es porque en el PDF esa celda
  estaba **combinada verticalmente** (*rowspan*, p. ej. la columna
  "Componente"): se hereda el valor de la fila anterior, igual que se ve
  visualmente en el PDF.
- **Tabla-formulario** (`parse_form_table`): el resto. Regla **padre-hijo**:
  una fila de 1 celda (p. ej. `A. Datos básicos de la asignatura`) es el
  padre de las filas siguientes, hasta la próxima fila de 1 celda. Dentro de
  cada bloque: 2 celdas → par `clave: valor` directo; 3+ celdas → la primera
  es un mini-título y el resto se agrupa en pares; una celda marcada con
  `x`/`✓` significa "esta opción está seleccionada" y se guarda la etiqueta.

### Fase C — Texto y ensamblado de secciones

- Un **heading** normalmente abre una sección raíz nueva. Pero si trae el
  patrón `Etiqueta: valor` (p. ej. `ÁREA ACADÉMICA: Técnica`), en realidad es
  un **campo** de la sección actual y se guarda como
  `area_academica: "Técnica"`.
- Un **párrafo** se clasifica: termina en `:` → título de sección (p. ej.
  `Fechas importantes:`); termina en `.`, `,` o `;` → contenido; corto
  (≤10 palabras) y justo antes de una tabla/lista → título que las agrupa;
  el resto → contenido (`texto: ...` dentro de la sección actual).
- Las **listas** se guardan como `lista_N: [items]` dentro de la sección
  actual.
- `merge_section_content` une todo sin perder datos aunque los tipos no
  calcen (dict con list, etc.).

### Claves seguras y sin pérdida de datos

- `clean_key()` normaliza **solo las claves** (nunca los valores): quita
  tildes, reemplaza cualquier símbolo por `_` (los puntos rompen la notación
  `seccion.campo` de Mongo) y pasa a snake_case en minúsculas.
- `add_unique()` evita sobrescribir: si una clave se repite, convierte el
  valor en lista y acumula.

### Resultado

Un único documento JSON por PDF, con las secciones del documento como claves
raíz. Reales de esta entrega:

- DSOF → 11 secciones raíz (`a_datos_de_identificacion_de_la_asignatura`,
  `b_descripcion_general_de_la_asignatura`, `c_resultados_de_aprendizaje...`,
  `d_contenidos`, `e_metodologia`, …)
- PLAN → 13 secciones raíz (`horario_de_clases`,
  `b_datos_basicos_del_docente`, `c_competencias_a_desarrollar`,
  `d_planificacion_general_de_la_asignatura_primer_bimestre`,
  `fechas_importantes`, …)

## Sobre `4_aplanar_documento.py` (conversor alternativo)

Es una versión previa del aplanado (`SmartJSONConverter`): también produce
clave:valor, pero interpreta cada tabla fila por fila según su número de
celdas y agrupa aparte `parrafos`, `encabezados` y `lista_N`, sin
reconstrucción de tablas cortadas ni secciones jerárquicas. Se conserva como
alternativa; los resultados de MongoDB de esta entrega se generaron con
`aplanar_para_mongo_generico.py`.
