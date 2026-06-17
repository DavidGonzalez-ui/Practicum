"""
_detectar_pdf.py
─────────────────
Función auxiliar usada por los scripts 1, 2 y 3 para que el flujo
funcione con CUALQUIER PDF, sin nombres hardcodeados.

Reglas de detección:
  1. Si se pasa un argumento por línea de comandos
     (python 1_extraer_pdf_opendataloader.py archivo.pdf), se usa ese.
  2. Si no, busca todos los .pdf en la carpeta actual:
       - si hay exactamente uno -> lo usa
       - si hay varios -> muestra un menú para elegir
       - si no hay ninguno -> lanza un error
"""

import sys
import glob
import os


def detectar_pdf():
    # Caso 1: PDF pasado como argumento
    if len(sys.argv) > 1:
        ruta = sys.argv[1]

        if not os.path.isfile(ruta):
            raise FileNotFoundError(
                f"No existe el archivo: {ruta}"
            )

        return ruta

    # Caso 2: Buscar PDFs en la carpeta actual
    pdfs = glob.glob("*.pdf")

    if len(pdfs) == 0:
        raise FileNotFoundError(
            "No se encontró ningún archivo .pdf en la carpeta actual.\n"
            "Ejecuta el script indicando el archivo:\n"
            "    python nombre_script.py mi_archivo.pdf"
        )

    if len(pdfs) == 1:
        print(f"PDF detectado automáticamente: {pdfs[0]}")
        return pdfs[0]

    # Caso 3: Hay varios PDFs
    print("\nSe encontraron varios archivos PDF:\n")

    for i, pdf in enumerate(pdfs, start=1):
        print(f"{i}. {pdf}")

    while True:
        try:
            opcion = int(
                input("\nSeleccione el número del PDF que desea procesar: ")
            )

            if 1 <= opcion <= len(pdfs):
                pdf_seleccionado = pdfs[opcion - 1]
                print(f"\nPDF seleccionado: {pdf_seleccionado}")
                return pdf_seleccionado

            print(
                f"Debe ingresar un número entre 1 y {len(pdfs)}."
            )

        except ValueError:
            print("Ingrese un número válido.")


def nombre_base(ruta_pdf):
    """
    'DSOF_1067-O20F21.pdf' -> 'DSOF_1067-O20F21'
    """
    return os.path.splitext(
        os.path.basename(ruta_pdf)
    )[0]