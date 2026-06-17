"""
4_aplanar_documento.py
────────────────────────
PASO 4 del flujo (final).

Aplanador 100% GENÉRICO Y RECURSIVO: convierte CUALQUIER árbol JSON
(dict / list anidados) en una lista plana de filas con:

    id          → identificador único secuencial (entero, determinista)
    parent_id   → id de la fila padre (None para la raíz)
    order       → posición entre hermanos (0, 1, 2, ...)
    type        → tipo de la fila (ver "Cómo se calcula type" abajo)
    source_id   → el "id" ORIGINAL del elemento si lo tenía
                   (ej: 221 para un heading, "T16_2" para una tabla;
                   None si el elemento no tenía "id" propio)
    + el resto de campos simples (content, page_number, etc.)

No asume nada sobre la estructura: NO sabe que una "table" tiene
"rows"->"cells" ni que una "list" tiene "items". Recorre cualquier
clave que sea lista o diccionario, sin importar su nombre. Por eso
sirve para CUALQUIER PDF que pase por el script 3, e incluso para
el JSON crudo de opendataloader_pdf si se quisiera aplanar directo.

Cómo se calcula "type"
───────────────────────
1. Si el elemento tiene su propia clave "type" (heading, paragraph,
   list, table, image, ...) -> se usa ese valor tal cual, y se vuelve
   el "contexto" para sus descendientes.
2. Si NO tiene "type" propio, se construye como
   "{contexto}_{singular(nombre_de_la_clave_que_lo_contenía)}"
   Ejemplos:  table + "rows"  -> "table_row"
              table_row + "cells" (contexto sigue siendo "table")
                                  -> "table_cell"
              list  + "items" -> "list_item"
3. Si tampoco hay contexto (es la raíz del documento), type = "document".

ENTRADA:
    JSONObtenidos/documento_final_ordenado.json

SALIDA:
    JSONObtenidos/documento_aplanado.json
"""

import json
from collections import Counter


filas = []
contador_id = 0


def nuevo_id():
    global contador_id
    contador_id += 1
    return contador_id


def singular(palabra):
    """'rows'->'row', 'cells'->'cell', 'items'->'item', 'kids'->'kid'..."""
    especiales = {"kids": "kid", "children": "child"}
    if palabra in especiales:
        return especiales[palabra]
    if palabra.endswith("s") and len(palabra) > 1:
        return palabra[:-1]
    return palabra


def agregar_fila(tipo, parent_id, order, source_id=None, **campos):
    fila = {
        "id": nuevo_id(),
        "parent_id": parent_id,
        "order": order,
        "type": tipo,
        "source_id": source_id,
    }
    fila.update(campos)
    filas.append(fila)
    return fila["id"]


def aplanar(nodo, parent_id, order, clave_contenedora=None, contexto=None):
    """
    Recorre `nodo` (dict o list) de forma recursiva y agrega filas a `filas`.
    - clave_contenedora: nombre de la clave del padre que contiene a `nodo`
                          (ej: "rows", "items", "elements")
    - contexto: el último "type" explícito visto en algún ancestro
                (ej: "table", "list"); se usa para nombrar a los hijos
                que no tienen "type" propio.
    """

    # ── Caso LISTA: cada item se aplana con el mismo contexto ──
    if isinstance(nodo, list):
        for i, item in enumerate(nodo):
            aplanar(item, parent_id, i,
                    clave_contenedora=clave_contenedora,
                    contexto=contexto)
        return

    # ── Caso DICCIONARIO ──
    if isinstance(nodo, dict):

        tipo_explicito = nodo.get("type")

        if tipo_explicito:
            tipo = tipo_explicito
        elif contexto and clave_contenedora:
            tipo = f"{contexto}_{singular(clave_contenedora)}"
        else:
            tipo = clave_contenedora or "document"

        # el contexto para los hijos: si este nodo definió un "type"
        # propio, ese se vuelve el nuevo contexto; si no, se conserva
        nuevo_contexto = tipo_explicito or contexto

        # campos simples (no dict/list, sin "type"/"id" -> van aparte)
        campos = {
            clave: valor
            for clave, valor in nodo.items()
            if clave not in ("type", "id")
            and not isinstance(valor, (dict, list))
        }

        nodo_id = agregar_fila(
            tipo,
            parent_id,
            order,
            source_id=nodo.get("id"),
            **campos
        )

        # recorrer hijos (cualquier clave que sea dict o list)
        for clave, valor in nodo.items():
            if isinstance(valor, (list, dict)):
                aplanar(valor, nodo_id, 0,
                        clave_contenedora=clave,
                        contexto=nuevo_contexto)

        return


# ══════════════════════════════════════════════════════════
#  LEER documento_final_ordenado.json
# ══════════════════════════════════════════════════════════

with open(
    "JSONObtenidos/documento_final_ordenadoPdf2.json",
    "r",
    encoding="utf-8"
) as f:
    documento = json.load(f)


# ══════════════════════════════════════════════════════════
#  APLANAR (recursivo, sin asumir nada de la estructura)
# ══════════════════════════════════════════════════════════

aplanar(documento, parent_id=None, order=0)


# ══════════════════════════════════════════════════════════
#  GUARDAR
# ══════════════════════════════════════════════════════════

with open(
    "JSONObtenidos/documento_aplanadoPdf2.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(filas, f, ensure_ascii=False, indent=4)


# ══════════════════════════════════════════════════════════
#  REPORTE
# ══════════════════════════════════════════════════════════

conteo = Counter(f["type"] for f in filas)

print("=" * 50)
print("  documento_aplanado.json generado")
print("=" * 50)
print(f"  Total de filas: {len(filas)}")
for tipo, cnt in sorted(conteo.items()):
    print(f"    {tipo:<15} : {cnt}")
print("=" * 50)
