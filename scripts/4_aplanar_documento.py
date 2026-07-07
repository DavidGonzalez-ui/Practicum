#!/usr/bin/env python3

import json
import re
import unicodedata
from pathlib import Path
from datetime import datetime


class SmartJSONConverter:
    
    def __init__(self, archivo_json: str):
        self.archivo_json = archivo_json
        self.datos_originales = None
        self.datos_planos = {}
        self.claves_usadas = set()
    
    def cargar_json(self) -> bool:
        try:
            with open(self.archivo_json, 'r', encoding='utf-8') as f:
                self.datos_originales = json.load(f)
            return True
        except Exception:
            return False
    
    def normalizar_clave(self, texto: str) -> str:
        if not isinstance(texto, str):
            return str(texto).lower()
        
        texto = re.sub(r'\s+', ' ', texto).strip().lower()
        nfd = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
        texto = re.sub(r'[^a-z0-9ñ]+', '_', texto)
        texto = texto.strip('_')
        texto = re.sub(r'_+', '_', texto)
        
        clave_final = texto
        contador = 1
        original = texto
        
        while clave_final in self.claves_usadas:
            clave_final = f"{original}_{contador}"
            contador += 1
        
        self.claves_usadas.add(clave_final)
        return clave_final
    
    def limpiar(self, valor: str) -> str:
        if not isinstance(valor, str):
            return str(valor)
        return re.sub(r'\s+', ' ', valor).replace('\n', ' ').strip()
    
    def detectar_marcador(self, texto: str) -> bool:
        return texto.lower().strip() in ['x', '✓']
    
    def procesar_tabla(self, tabla: dict) -> dict:
        resultado = {}
        filas = tabla.get('rows', [])
        
        if not filas:
            return resultado
        
        for idx, fila in enumerate(filas):
            cells = fila.get('cells', [])
            contenidos = [self.limpiar(c.get('content', '')) for c in cells if c.get('content')]
            
            if not contenidos:
                continue
            
            if len(contenidos) == 1:
                contenido = contenidos[0]
                if len(contenido) >= 3 and not self.detectar_marcador(contenido):
                    clave = self.normalizar_clave(contenido)
                    resultado[clave] = contenido
            
            elif len(contenidos) == 2:
                clave_texto, valor_texto = contenidos[0], contenidos[1]
                
                if self.detectar_marcador(valor_texto) and len(clave_texto) >= 3:
                    clave = self.normalizar_clave(clave_texto)
                    resultado[clave] = clave_texto
                
                elif (len(clave_texto) >= 3 and len(valor_texto) >= 2 and 
                      not self.detectar_marcador(clave_texto) and 
                      not self.detectar_marcador(valor_texto)):
                    clave = self.normalizar_clave(clave_texto)
                    resultado[clave] = valor_texto
            
            elif len(contenidos) > 2:
                primer = contenidos[0]
                if len(primer) >= 3 and not self.detectar_marcador(primer):
                    if len(contenidos) == 3 and self.detectar_marcador(contenidos[-1]):
                        clave = self.normalizar_clave(primer)
                        resultado[clave] = primer
                    elif not all(self.detectar_marcador(c) for c in contenidos[1:]):
                        clave = self.normalizar_clave(primer)
                        valor = ' '.join(contenidos[1:])
                        resultado[clave] = valor
        
        return resultado
    
    def procesar(self) -> dict:
        if not self.cargar_json():
            return {}
        
        self.datos_planos['_metadata'] = {
            'archivo_original': self.datos_originales.get('file_name', ''),
            'fecha_procesamiento': datetime.now().isoformat(),
            'total_elementos': self.datos_originales.get('total_elements', 0)
        }
        
        elementos = self.datos_originales.get('elements', [])
        parrafos = []
        encabezados = []
        listas = {}
        
        for elemento in elementos:
            tipo = elemento.get('type', '')
            
            if tipo == 'table':
                tabla_datos = self.procesar_tabla(elemento)
                self.datos_planos.update(tabla_datos)
            
            elif tipo == 'paragraph':
                contenido = self.limpiar(elemento.get('content', ''))
                if len(contenido) >= 5:
                    parrafos.append(contenido)
            
            elif tipo == 'heading':
                contenido = self.limpiar(elemento.get('content', ''))
                if len(contenido) >= 3:
                    encabezados.append(contenido)
            
            elif tipo == 'list':
                items = [self.limpiar(i.get('content', '')) 
                        for i in elemento.get('items', []) if i.get('content')]
                if items:
                    elemento_id = elemento.get('id', len(listas))
                    listas[f"lista_{elemento_id}"] = items
        
        if parrafos:
            self.datos_planos['parrafos'] = parrafos
        if encabezados:
            self.datos_planos['encabezados'] = encabezados
        
        self.datos_planos.update(listas)
        
        return self.datos_planos
    
    def guardar(self, archivo_salida: str = None) -> str:
        if not archivo_salida:
            ruta = Path(self.archivo_json)
            ## Aca esta para cambiar el nombre 
            archivo_salida = str(ruta.parent / f"{ruta.stem}_PLANO2.json")
        
        try:
            with open(archivo_salida, 'w', encoding='utf-8') as f:
                json.dump(self.datos_planos, f, ensure_ascii=False, indent=2)
            return archivo_salida
        except Exception:
            return None
    
    def transformar(self) -> str:
        self.procesar()
        return self.guardar()


if __name__ == "__main__":
    archivo_entrada = "JSONObtenidos\documento_final_ordenado2.json"
    convertidor = SmartJSONConverter(archivo_entrada)
    archivo_salida = convertidor.transformar()
    
    if archivo_salida:
        print(f"✓ {Path(archivo_salida).name}")
