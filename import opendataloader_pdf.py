import opendataloader_pdf

# Batch all files in one call — each convert() spawns a JVM process, so repeated calls are slow
opendataloader_pdf.convert(
    input_path=["DSOF_1067-O20F21.pdf", "PLAN_3952-DSOF_1067.pdf"],
    output_dir=r"C:\Users\Usuario\OneDrive - Universidad Técnica Particular de Loja - UTPL\Escritorio\Programar\Programacion\Practicum1.2",
    format="markdown,json"
)