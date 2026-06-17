# Flujo de extracción y limpieza

Este documento amplía el porqué de cada paso del flujo. Todos los scripts
experimentales previos (extracción de tablas suelta, limpieza de columnas
vacías, fusiones, detección de duplicados por texto, etc.) quedaron
**reemplazados** por el script 3, que hace todo eso internamente de forma
más robusta ordenando por posición real en la página.

## Por qué funciona el ordenamiento (paso 3)

El reto es mezclar dos fuentes que usan **sistemas de coordenadas distintos**:

- Cada `heading` / `paragraph` / `list` extraído por `opendataloader_pdf`
  trae una *bounding box* en coordenadas PDF: el origen está
  **abajo-izquierda** y la **Y crece hacia ARRIBA**.
- Cada tabla detectada por `pdfplumber` (`find_tables`) trae un `bbox` en
  su propio sistema: el origen está **arriba-izquierda** y el valor `top`
  **crece hacia ABAJO** desde el tope de la página.

La conversión que unifica ambos sistemas es:

```
y_tabla = page_height - bbox.top   # borde superior de la tabla en coords PDF
```

Con ambos en el mismo sistema, basta con **ordenar cada página por Y
descendente** (de arriba hacia abajo) para reconstruir el **orden de
lectura real** del documento, intercalando correctamente texto y tablas.

### Caso real (páginas 16 y 28)

La tabla *"Horas de trabajo (Totales del bimestre)"* tiene su borde
superior justo **debajo** del heading y **encima** del párrafo
*"Fechas importantes:"*. Gracias al ordenamiento por posición, la tabla
queda intercalada en el lugar correcto, y no al final del bloque de texto.

## Por qué el aplanador (paso 4) es recursivo y genérico

El paso 4 **no asume** que una `table` tenga `rows → cells` ni que una
`list` tenga `items`. Recorre **cualquier** clave que sea `dict` o `list`,
sin importar su nombre. Esto lo hace válido para cualquier PDF, e incluso
para el JSON crudo de `opendataloader_pdf` si se quisiera aplanar directo.

El `type` de cada fila se calcula así:

1. Si el elemento tiene su propia clave `"type"` (heading, paragraph,
   list, table, image...) → se usa tal cual y pasa a ser el **contexto**
   de sus descendientes.
2. Si no la tiene → `"{contexto}_{singular(clave_que_lo_contiene)}"`.
   Ejemplos: `table` + `"rows"` → `table_row`; `list` + `"items"` →
   `list_item`.
3. Si tampoco hay contexto (es la raíz) → `"document"`.

Si el script 3 cambiara de formato, o se usara otro PDF con estructura
distinta, el aplanador **sigue funcionando sin modificarlo**.
