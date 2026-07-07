"""
aplanar_para_mongo_generico.py

Aplana el JSON extraído del PDF en UN único diccionario jerárquico
clave:valor (sin campos de metadata como tipo/id/pagina/archivo), listo
para subir a MongoDB. Las CLAVES se normalizan (sin tildes, sin puntos,
sin espacios, snake_case) para que cualquier consulta con notación de
puntos funcione sin errores; los VALORES (el contenido real) se dejan
intactos, con tildes y formato original.

Uso: python3 aplanar_para_mongo_generico.py entrada.json salida.json
"""

import json
import re
import sys
import unicodedata


def clean_key(text) -> str:
    """Convierte texto crudo (celda/encabezado) en una clave de Mongo
    100% segura: sin tildes/diéresis/ñ especiales, sin puntos ni otros
    símbolos (rompen la notación de puntos de Mongo), sin espacios
    (todo en snake_case). Esto NUNCA se aplica a los valores, solo a
    las claves."""
    if text is None:
        return "campo"
    key = str(text).strip()
    key = unicodedata.normalize("NFKD", key)
    key = "".join(c for c in key if not unicodedata.combining(c))  # quita tildes
    key = re.sub(r"[^A-Za-z0-9]+", " ", key)  # cualquier símbolo (incluye '.') -> espacio
    key = re.sub(r"\s+", "_", key.strip())
    return key.lower() if key else "campo"


def add_unique(target: dict, key: str, value):
    """Agrega key:value; si la clave ya existe, la convierte en lista
    en vez de sobrescribirla. Si tanto el valor existente como el nuevo
    son listas, se concatenan (no se anida una lista dentro de otra)."""
    if key in target:
        if isinstance(target[key], list) and isinstance(value, list):
            target[key].extend(value)
        elif isinstance(target[key], list):
            target[key].append(value)
        else:
            target[key] = [target[key], value]
    else:
        target[key] = value


_EMBEDDED_KV = re.compile(r"^([^:：]{1,60}):\s*(.+)$", re.DOTALL)


def split_embedded_kv(text: str):
    """Separa el patrón 'Etiqueta: valor' cuando viene junto en un mismo
    texto (ej. 'Crédito: 3' o 'ÁREA ACADÉMICA: Técnica'). None si el
    texto termina en ':' sin nada después."""
    if not text:
        return None
    m = _EMBEDDED_KV.match(text.strip())
    if not m:
        return None
    etiqueta, valor = m.group(1).strip(), m.group(2).strip()
    if not etiqueta or not valor:
        return None
    return clean_key(etiqueta), valor


# ---------------------------------------------------------------------
# Preparación de tablas: el PDF corta muchas tablas al cambiar de página.
# El título de una sección (ej. "Semana 6") suele quedar solo en una
# tabla, y su contenido real cae en la(s) tabla(s) siguientes SIN su
# propio título. Estas reglas reconstruyen la tabla completa antes de
# interpretarla.
# ---------------------------------------------------------------------

def _es_titulo_duplicado(actual, anterior):
    """La tabla 'actual' es una fila suelta cuyo texto repite EXACTO el
    título con el que terminó la tabla anterior (artefacto típico de
    salto de página): se descarta, no aporta nada nuevo."""
    filas_a = actual.get("rows") or []
    filas_p = anterior.get("rows") or []
    if len(filas_a) != 1 or not filas_p:
        return False
    celdas_a = filas_a[0].get("cells", [])
    celdas_p = filas_p[-1].get("cells", [])
    if len(celdas_a) != 1 or len(celdas_p) != 1:
        return False
    return clean_key(celdas_a[0].get("content")) == clean_key(celdas_p[0].get("content"))


def _tiene_titulo_colgante_confiable(table):
    """True solo si hay evidencia fuerte de que la tabla quedó cortada a
    mitad de un bloque título+contenido (y no es simplemente una lista de
    casilleros que termina en un ítem suelto, ni una tabla-matriz cuya
    última fila es un dato disperso y no un título).

    Evidencia fuerte = la tabla termina en una fila de 1 celda, Y ADEMÁS:
    - es la ÚNICA fila de la tabla (un título suelto, sin nada más), o
    - la fila justo antes tiene 2+ celdas (datos reales), señal de que
      el bloque título+contenido se interrumpió a mitad de camino.
    """
    rows = table.get("rows") or []
    if not rows or is_matrix_table(rows):
        return False
    if len(rows[-1].get("cells", [])) != 1:
        return False
    if len(rows) == 1:
        return True
    return len(rows[-2].get("cells", [])) >= 2


def _empieza_sin_titulo(table):
    """True si la primera fila de la tabla NO es un título (no tiene
    exactamente 1 celda): esta tabla no abre su propia sección."""
    rows = table.get("rows") or []
    return bool(rows) and len(rows[0].get("cells", [])) != 1


def _es_continuacion_de_matriz(table):
    """Tabla-matriz (ej. horarios) cortada por página: ninguna de sus
    celdas usa la columna 1 porque esa columna quedó vacía en el corte."""
    rows = table.get("rows") or []
    if not rows:
        return False
    return all(c.get("column_number") != 1 for r in rows for c in r.get("cells", []))


def preparar_tablas(elementos: list) -> list:
    resultado = []
    for e in elementos:
        es_tabla = isinstance(e, dict) and e.get("type") == "table"
        anterior = resultado[-1] if resultado and isinstance(resultado[-1], dict) else None
        anterior_es_tabla = anterior is not None and anterior.get("type") == "table"

        if es_tabla and anterior_es_tabla:
            if _es_titulo_duplicado(e, anterior):
                continue  # título repetido por el corte de página: se descarta

            if _tiene_titulo_colgante_confiable(anterior) and _empieza_sin_titulo(e):
                # Contenido sin título propio, y la tabla anterior quedó
                # con un título sin resolver: se pega como continuación.
                anterior["rows"] = (anterior.get("rows") or []) + (e.get("rows") or [])
                continue

            if _es_continuacion_de_matriz(e):
                nuevas_filas = e.get("rows") or []
                prev_rows = anterior.get("rows") or []
                fusionado = False
                if len(nuevas_filas) == 1 and prev_rows:
                    cols_previas = {c["column_number"]: c for c in prev_rows[-1].get("cells", [])}
                    for c in nuevas_filas[0].get("cells", []):
                        if c["column_number"] in cols_previas:
                            celda = cols_previas[c["column_number"]]
                            celda["content"] = f"{str(celda.get('content', '')).rstrip()}\n{c.get('content', '')}"
                            fusionado = True
                if not fusionado:
                    anterior["rows"] = prev_rows + nuevas_filas
                continue

        resultado.append(e)
    return resultado


def is_matrix_table(rows) -> bool:
    """Tabla-matriz (columnas reales, ej. horarios): la primera fila
    tiene 3+ celdas que no terminan en ':' (son encabezados de columna)."""
    if not rows:
        return False
    first_cells = rows[0].get("cells", [])
    if len(first_cells) < 3:
        return False
    if any(str(c.get("content", "")).rstrip().endswith(":") for c in first_cells):
        return False
    max_col = max((c.get("column_number", 1) for r in rows for c in r.get("cells", [])), default=1)
    return max_col > 2


def parse_matrix_table(rows):
    """Lista de registros usando column_number para emparejar cada celda
    con el encabezado real de su columna. Cuando a una fila le falta la
    PRIMERA columna (ej. 'Componente'), es porque en el PDF original esa
    celda estaba combinada (rowspan) con la fila de arriba: se hereda el
    valor de la fila anterior para esa y cualquier otra columna faltante,
    igual que se ve visualmente en la tabla del PDF."""
    headers = {c.get("column_number"): clean_key(c.get("content")) for c in rows[0].get("cells", [])}
    columnas = sorted(headers.keys())
    primera_columna = columnas[0] if columnas else None

    registros = []
    anterior = {}
    for row in rows[1:]:
        celdas = {c.get("column_number"): c.get("content") for c in row.get("cells", [])}
        es_continuacion = primera_columna is not None and primera_columna not in celdas
        registro = {}
        for col in columnas:
            nombre_col = headers[col]
            if col in celdas:
                add_unique(registro, nombre_col, celdas[col])
            elif es_continuacion and nombre_col in anterior:
                add_unique(registro, nombre_col, anterior[nombre_col])
        for col, valor in celdas.items():
            if col not in headers:
                add_unique(registro, f"columna_{col}", valor)
        registros.append(registro)
        anterior = registro
    return registros


def parse_row_into(row, target: dict):
    """Regla padre-hijo por fila: 2 celdas = clave:valor directo; 3+ =
    primera celda como mini-título y el resto en pares clave:valor (o
    separando 'Etiqueta: valor' si viene junto en una celda)."""
    cells = row.get("cells", [])
    n = len(cells)
    if n == 0:
        return
    if n == 1:
        target.setdefault("otros_elementos", []).append(cells[0].get("content"))
    elif n == 2:
        add_unique(target, clean_key(cells[0].get("content")), cells[1].get("content"))
    else:
        label = clean_key(cells[0].get("content"))
        resto = cells[1:]
        sub = {}
        i = 0
        while i < len(resto):
            embebido = split_embedded_kv(resto[i].get("content"))
            if embebido:
                add_unique(sub, embebido[0], embebido[1])
                i += 1
            elif i + 1 < len(resto):
                add_unique(sub, clean_key(resto[i].get("content")), resto[i + 1].get("content"))
                i += 2
            else:
                add_unique(sub, "valor_adicional", resto[i].get("content"))
                i += 1
        add_unique(target, label, sub)


def _tiene_hijos_antes_del_siguiente_titulo(rows, start_idx):
    j = start_idx
    found = False
    while j < len(rows) and len(rows[j].get("cells", [])) != 1:
        if len(rows[j].get("cells", [])) >= 2:
            found = True
        j += 1
    return found, j


def parse_form_table(rows):
    """Tabla tipo formulario: una fila de 1 celda es el PADRE de las
    filas que siguen (hasta la próxima fila de 1 celda), igual que en el
    ejemplo original ('A. Datos básicos...' como padre de 'Nombre de la
    asignatura' -> 'INTRODUCCION A LA PROGRAMACION')."""
    contenido = {}
    idx, n = 0, len(rows)
    while idx < n:
        row = rows[idx]
        cells = row.get("cells", [])
        if len(cells) == 1:
            label = clean_key(cells[0].get("content"))
            tiene_hijos, next_idx = _tiene_hijos_antes_del_siguiente_titulo(rows, idx + 1)
            if tiene_hijos:
                sub = {}
                for j in range(idx + 1, next_idx):
                    parse_row_into(rows[j], sub)
                add_unique(contenido, label, sub)
                idx = next_idx
            else:
                contenido.setdefault("otros_elementos", []).append(cells[0].get("content"))
                idx += 1
        else:
            parse_row_into(row, contenido)
            idx += 1
    return contenido


def merge_section_content(root: dict, section_key: str, data):
    """Une 'data' (dict o list) dentro de root[section_key] sin agregar
    metadata. Si los tipos no calzan (dict existente + list nueva, o
    viceversa) se envuelven bajo 'registros' en vez de perder datos."""
    existente = root.get(section_key)
    if existente is None or existente == {}:
        root[section_key] = data
        return
    if isinstance(existente, dict):
        if isinstance(data, dict):
            for k, v in data.items():
                add_unique(existente, k, v)
        else:
            add_unique(existente, "registros", data)
    elif isinstance(existente, list):
        if isinstance(data, list):
            existente.extend(data)
        else:
            nuevo = {"registros": existente}
            for k, v in data.items():
                add_unique(nuevo, k, v)
            root[section_key] = nuevo
    else:
        root[section_key] = {"valor_previo": existente}
        merge_section_content(root, section_key, data)


def encontrar_lista_de_elementos(data):
    """Ubica la lista de elementos aunque no esté bajo la clave 'elements'."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("elements"), list):
            return data["elements"]
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and "type" in v[0]:
                return v
    raise ValueError(
        "No pude encontrar la lista de elementos del documento. Esperaba "
        "una clave 'elements' (lista de objetos con 'type'), o directamente "
        "una lista de esos objetos en la raíz."
    )


_FIN_ORACION = (".", ",", ";")


def _clasificar_parrafo(texto: str, siguiente_tipo):
    """Distingue párrafo-TÍTULO (ej. 'Fechas importantes:') de
    párrafo-CONTENIDO (ej. una descripción larga). Termina en ':' ->
    título. Termina en '.', ',' o ';' -> contenido. Corto y justo antes
    de tabla/lista -> título que las agrupa. Otro caso -> contenido."""
    t = (texto or "").strip()
    if not t:
        return "vacio"
    if t.endswith(":"):
        return "titulo"
    if t.endswith(_FIN_ORACION):
        return "contenido"
    return "titulo" if len(t.split()) <= 10 and siguiente_tipo in ("table", "list") else "contenido"


def transformar(data) -> dict:
    elementos = preparar_tablas(encontrar_lista_de_elementos(data))

    root: dict = {}
    seccion_actual = None
    contador_listas = 0

    for idx, e in enumerate(elementos):
        if not isinstance(e, dict):
            continue

        tipo = e.get("type")
        siguiente = elementos[idx + 1] if idx + 1 < len(elementos) else None
        siguiente_tipo = siguiente.get("type") if isinstance(siguiente, dict) else None

        try:
            if tipo == "heading":
                contenido_txt = e.get("content")
                if contenido_txt is None:
                    continue
                # Un heading tipo "ÁREA ACADÉMICA: Técnica" es en realidad
                # un campo clave:valor de la sección actual, no un título
                # nuevo (a diferencia de "A. Datos básicos...", que no
                # trae un valor embebido y sí abre sección).
                embebido = split_embedded_kv(contenido_txt)
                if embebido and seccion_actual is not None:
                    merge_section_content(root, seccion_actual, {embebido[0]: embebido[1]})
                else:
                    clave = clean_key(contenido_txt)
                    root.setdefault(clave, {})
                    seccion_actual = clave

            elif tipo == "paragraph":
                contenido_txt = e.get("content")
                if contenido_txt is None:
                    continue
                embebido = split_embedded_kv(contenido_txt)
                if embebido:
                    seccion_actual = seccion_actual or "contenido"
                    root.setdefault(seccion_actual, {})
                    merge_section_content(root, seccion_actual, {embebido[0]: embebido[1]})
                elif _clasificar_parrafo(contenido_txt, siguiente_tipo) == "titulo":
                    clave = clean_key(contenido_txt)
                    root.setdefault(clave, {})
                    seccion_actual = clave
                else:
                    seccion_actual = seccion_actual or "contenido"
                    root.setdefault(seccion_actual, {})
                    merge_section_content(root, seccion_actual, {"texto": contenido_txt})

            elif tipo == "table":
                rows = e.get("rows", [])
                contenido = parse_matrix_table(rows) if is_matrix_table(rows) else parse_form_table(rows)
                seccion_actual = seccion_actual or "contenido"
                root.setdefault(seccion_actual, {})
                merge_section_content(root, seccion_actual, contenido)

            elif tipo == "list":
                contador_listas += 1
                items = [item.get("content") for item in e.get("items", [])]
                seccion_actual = seccion_actual or "contenido"
                root.setdefault(seccion_actual, {})
                merge_section_content(root, seccion_actual, {f"lista_{contador_listas}": items})

            else:
                seccion_actual = seccion_actual or "contenido"
                root.setdefault(seccion_actual, {})
                if isinstance(e.get("rows"), list):
                    rows = e["rows"]
                    contenido = parse_matrix_table(rows) if is_matrix_table(rows) else parse_form_table(rows)
                    merge_section_content(root, seccion_actual, contenido)
                elif isinstance(e.get("items"), list):
                    contador_listas += 1
                    items = [i.get("content", i) if isinstance(i, dict) else i for i in e["items"]]
                    merge_section_content(root, seccion_actual, {f"lista_{contador_listas}": items})
                elif e.get("content") is not None:
                    clave = clean_key(e["content"])
                    root.setdefault(clave, {})
                    seccion_actual = clave
        except Exception:
            continue

    return root


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "documento_final_ordenado.json"
    salida_path = sys.argv[2] if len(sys.argv) > 2 else "documento_para_mongo_generico.json"

    with open(entrada, encoding="utf-8") as f:
        data = json.load(f)

    with open(salida_path, "w", encoding="utf-8") as f:
        json.dump(transformar(data), f, ensure_ascii=False, indent=2)

    print(salida_path)
