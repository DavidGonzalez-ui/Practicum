"""
1_extraer_pdf_opendataloader.py
─────────────────────────────────
PASO 1 del flujo.

Usa la librería `opendataloader_pdf` (requiere Java instalado) para leer
el PDF y generar un JSON con TODO el contenido detectado por la
herramienta: headings, paragraphs, lists, tables, images, etc.

FUNCIONA CON CUALQUIER PDF:
    - Si hay un solo .pdf en esta carpeta, se detecta automáticamente.
    - Si quieres especificar otro, pásalo como argumento:
          python 1_extraer_pdf_opendataloader.py mi_archivo.pdf

ENTRADA:
    <cualquier>.pdf  (detectado automáticamente)

SALIDA:
    JSONObtenidos/<nombre_del_pdf>.json
    JSONObtenidos/<nombre_del_pdf>.md   (versión markdown, opcional)

NOTA:
    Este paso solo necesita ejecutarse UNA VEZ. Si ya tienes el JSON
    crudo en JSONObtenidos/, puedes saltar este paso y continuar
    directamente con el script 2.
"""

import opendataloader_pdf
from _detectar_pdf import detectar_pdf

pdf_path = detectar_pdf()

print(f"PDF detectado: {pdf_path}")

opendataloader_pdf.convert(
    input_path=[pdf_path],
    output_dir="JSONObtenidos",
    format="markdown,json"
)

print("Extracción con opendataloader_pdf completada -> JSONObtenidos/")
