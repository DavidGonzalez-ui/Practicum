"""
2_filtrar_contenido_sin_tablas.py
─────────────────────────────────
PASO 2 del flujo.

Toma el JSON crudo de opendataloader_pdf y se queda únicamente con los
elementos de tipo "heading", "paragraph" y "list" (descarta "image",
"table" y cualquier otro tipo detectado por la propia herramienta).

Este es el "texto" del documento, antes de mezclarlo con las tablas
que extraeremos por separado con pdfplumber (paso 3).

FUNCIONA CON CUALQUIER PDF:
    - Detecta automáticamente el .pdf de esta carpeta y busca su JSON
      crudo correspondiente en JSONObtenidos/<nombre_del_pdf>.json
    - Si no lo encuentra con ese nombre exacto, busca cualquier JSON
      en JSONObtenidos/ que tenga la forma "cruda" (claves "file name"
      y "kids" a nivel raíz) y no sea uno de los archivos generados
      por este mismo flujo.

ENTRADA:
    JSONObtenidos/<nombre_del_pdf>.json

SALIDA:
    JSONObtenidos/contenido_sin_tablas.json
"""

import json
import os
import glob

from _detectar_pdf import detectar_pdf, nombre_base


GENERADOS_POR_EL_FLUJO = {
    "contenido_sin_tablas.json",
    "documento_final_ordenado.json",
    "documento_aplanado.json",
}


def localizar_json_crudo():
    pdf_path = detectar_pdf()
    esperado = os.path.join("JSONObtenidos", f"{nombre_base(pdf_path)}.json")

    if os.path.isfile(esperado):
        return esperado

    # Fallback: buscar cualquier json "crudo" (file name + kids)
    for ruta in glob.glob(os.path.join("JSONObtenidos", "*.json")):
        if os.path.basename(ruta) in GENERADOS_POR_EL_FLUJO:
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and "file name" in data and "kids" in data:
            return ruta

    raise FileNotFoundError(
        f"No se encontró el JSON crudo esperado ({esperado}) ni ningún "
        f"JSON con formato 'file name' + 'kids' en JSONObtenidos/. "
        f"Ejecuta primero 1_extraer_pdf_opendataloader.py"
    )


ruta_json = localizar_json_crudo()
print(f"JSON crudo: {ruta_json}")

with open(ruta_json, "r", encoding="utf-8") as archivo:
    documento = json.load(archivo)

elementos_filtrados = []

for elemento in documento["kids"]:

    tipo = elemento.get("type")

    if tipo in ("heading", "paragraph", "list"):
        elementos_filtrados.append(elemento)

nuevo_json = {
    "file_name": documento["file name"],
    "kids": elementos_filtrados
}

with open(
    "JSONObtenidos/contenido_sin_tablasPdf2.json",
    "w",
    encoding="utf-8"
) as archivo:
    json.dump(nuevo_json, archivo, ensure_ascii=False, indent=4)

print(f"Contenido filtrado: {len(elementos_filtrados)} elementos "
      f"(heading/paragraph/list) -> JSONObtenidos/contenido_sin_tablas.json")
