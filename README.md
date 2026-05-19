# Practicum

Primer trabajo del Practicum 1.2, realizado en el laboratorio para comprobar las utilidades de la librería `opendataloader_pdf`.

## Descripción

Código utilizado para la extracción de datos tipo JSON desde archivos PDF facilitados por el docente tutor.

## Código

```python
import opendataloader_pdf

# Procesa múltiples archivos PDF en una sola llamada
opendataloader_pdf.convert(
    input_path=[
        "DSOF_1067-O20F21.pdf",
        "PLAN_3952-DSOF_1067.pdf"
    ],
    output_dir="./salida",
    format="markdown,json"
)
