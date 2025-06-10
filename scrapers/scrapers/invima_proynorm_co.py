import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re

async def scrape_invima_proyectos_normativos_co():
    """
    Scraper simplificado para la página de proyectos normativos del INVIMA.
    Enfoque: extraer todo el texto y procesar secuencialmente.
    """
    url = "https://www.invima.gov.co/normatividad/proyectos-normativos"
    items = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Realizar la solicitud HTTP
            response = await client.get(url)
            if response.status_code != 200:
                print(f"Error: No se pudo acceder a la página. Código {response.status_code}")
                return []

            # Parsear el HTML de la página
            soup = BeautifulSoup(response.text, "html.parser")
            print(f"HTML obtenido, tamaño: {len(response.text)} caracteres")

            # Buscar todos los enlaces de proyectos
            enlaces_proyectos = soup.find_all("a", href=re.compile(r"\.pdf$|\.docx?$"))
            print(f"Encontrados {len(enlaces_proyectos)} enlaces a documentos")

            # Filtrar solo proyectos de resolución
            proyectos_validos = []
            for enlace in enlaces_proyectos:
                texto_enlace = enlace.get_text(strip=True)
                if any(keyword in texto_enlace.lower() for keyword in ["proyecto", "resolución", "resolution"]):
                    proyectos_validos.append(enlace)

            print(f"Proyectos válidos encontrados: {len(proyectos_validos)}")

            # Dividir el contenido en bloques basados en separadores HTML específicos
            bloques_html = dividir_contenido_por_separadores_html(soup)
            print(f"Contenido dividido en {len(bloques_html)} bloques HTML")

            # También extraer texto completo como fallback
            texto_completo = soup.get_text()
            print(f"Texto completo extraído: {len(texto_completo)} caracteres")

            # Procesar cada proyecto válido
            for i, enlace in enumerate(proyectos_validos):
                try:
                    texto_enlace = enlace.get_text(strip=True)
                    
                    print(f"\n--- Procesando proyecto {i+1}: {texto_enlace[:50]}... ---")
                    
                    # Verificar que este enlace es realmente el del título principal
                    if not es_enlace_titulo_principal(enlace):
                        print("Este enlace no es del título principal, saltando...")
                        continue
                    
                    # El source_url siempre será el enlace del título "Proyecto de Resolución"
                    href = enlace.get("href", "")
                    if href.startswith("/"):
                        url_completa = f"https://www.invima.gov.co{href}"
                    else:
                        url_completa = href
                    
                    print(f"URL del proyecto principal: {url_completa}")
                    
                    # Encontrar el bloque HTML correspondiente a este proyecto
                    bloque_proyecto = encontrar_bloque_html_proyecto(enlace, bloques_html)
                    if not bloque_proyecto:
                        # Fallback: buscar en texto completo
                        print("No se encontró bloque HTML, usando fallback de texto...")
                        bloque_proyecto = extraer_contexto_proyecto(texto_enlace, texto_completo)
                    
                    print(f"Bloque encontrado: {bloque_proyecto[:300]}...")
                    
                    # Extraer título y descripción del bloque (incluyendo otros enlaces)
                    titulo, descripcion = extraer_titulo_y_descripcion_con_enlaces(bloque_proyecto, enlace, bloques_html)
                    
                    print(f"Título extraído: {titulo[:100]}...")
                    print(f"Descripción: {descripcion[:200]}...")
                    
                    # Extraer información del bloque para debugging
                    fecha_publicacion = extract_date_from_text(bloque_proyecto, "publicación")
                    fecha_finalizacion = extract_date_from_text(bloque_proyecto, "finalización")
                    correo_observaciones = extract_email_from_text(bloque_proyecto)
                    
                    print(f"Datos extraídos (solo para debugging):")
                    print(f"  - Fecha publicación: {fecha_publicacion}")
                    print(f"  - Fecha finalización: {fecha_finalizacion}")
                    print(f"  - Correo: {correo_observaciones}")
                    
                    # Determinar el estado solo para debugging
                    estado = "Activo"
                    if fecha_finalizacion and fecha_finalizacion < datetime.now():
                        estado = "Finalizado"
                    print(f"  - Estado: {estado}")
                    
                    # Crear el item
                    item = {
                        'title': titulo,
                        'description': descripcion,
                        'source_type': "Ejecutivo",
                        'category': "Proyectos Normativos",
                        'country': "Colombia",
                        'source_url': url_completa,
                        'presentation_date': datetime.now(),  # Fecha de extracción
                        'institution': "INVIMA Colombia"
                    }
                    
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando proyecto: {e}")
                    continue

        except Exception as e:
            print(f"Error al realizar la solicitud: {e}")
            return []

    print(f"\nTotal de proyectos extraídos: {len(items)}")
    return items


def dividir_contenido_por_separadores_html(soup):
    """
    Divide el contenido HTML en bloques basándose en separadores específicos:
    <hr> y <p>&nbsp;</p>
    """
    bloques = []
    
    # Buscar el contenedor principal
    contenedor_principal = None
    selectores = [
        ".field--name-body .field__item",
        ".node__content .field__item", 
        ".text-formatted.field__item",
        ".clearfix.text-formatted.field",
        "article .node__content"
    ]
    
    for selector in selectores:
        contenedor_principal = soup.select_one(selector)
        if contenedor_principal:
            break
    
    if not contenedor_principal:
        contenedor_principal = soup
    
    # Obtener todos los elementos hijos
    elementos = list(contenedor_principal.children)
    
    # Filtrar solo elementos reales (no text nodes)
    elementos_reales = [elem for elem in elementos if hasattr(elem, 'name') and elem.name]
    
    bloque_actual = []
    
    for elemento in elementos_reales:
        # Verificar si es un separador
        es_separador = False
        
        # Separador HR
        if elemento.name == 'hr':
            es_separador = True
        
        # Separador <p>&nbsp;</p>
        elif elemento.name == 'p':
            texto_p = elemento.get_text(strip=True)
            # Verificar si es un párrafo vacío o solo con &nbsp;
            if not texto_p or texto_p == '\xa0' or texto_p == '' or '&nbsp;' in str(elemento):
                # Verificar que no contenga enlaces importantes
                if not elemento.find('a', href=True):
                    es_separador = True
        
        if es_separador:
            # Si encontramos un separador y hay contenido en el bloque actual
            if bloque_actual:
                bloque_texto = extraer_texto_de_elementos(bloque_actual)
                if len(bloque_texto.strip()) > 50:  # Solo bloques significativos
                    bloques.append({
                        'texto': bloque_texto,
                        'elementos': bloque_actual.copy()
                    })
                bloque_actual = []
        else:
            # Agregar elemento al bloque actual
            bloque_actual.append(elemento)
    
    # Agregar el último bloque si existe
    if bloque_actual:
        bloque_texto = extraer_texto_de_elementos(bloque_actual)
        if len(bloque_texto.strip()) > 50:
            bloques.append({
                'texto': bloque_texto,
                'elementos': bloque_actual.copy()
            })
    
    print(f"Separadores encontrados y bloques creados: {len(bloques)}")
    return bloques


def extraer_texto_de_elementos(elementos):
    """
    Extrae texto limpio de una lista de elementos HTML.
    """
    textos = []
    for elem in elementos:
        if hasattr(elem, 'get_text'):
            texto = elem.get_text()
            if texto.strip():
                textos.append(texto.strip())
    
    return ' '.join(textos).replace('\n', ' ').replace('\r', ' ')


def encontrar_bloque_html_proyecto(enlace, bloques_html):
    """
    Encuentra el bloque HTML que contiene un enlace específico.
    """
    for bloque in bloques_html:
        # Verificar si el enlace está en alguno de los elementos del bloque
        for elemento in bloque['elementos']:
            if enlace in elemento.find_all('a', href=True):
                return bloque['texto']
    
    return None


def extraer_contexto_proyecto(texto_enlace, texto_completo):
    """
    Extrae contexto alrededor de la mención de un proyecto en el texto completo.
    """
    # Buscar el texto del enlace o partes de él
    texto_busqueda = texto_enlace.replace('"', '').replace('"', '').replace('"', '')
    
    # Intentar buscar fragmentos del título
    fragmentos = [texto_busqueda[:50], texto_busqueda[:30], texto_busqueda[:20]]
    
    for fragmento in fragmentos:
        posicion = texto_completo.lower().find(fragmento.lower())
        if posicion != -1:
            # Extraer contexto amplio
            inicio = max(0, posicion - 500)
            fin = min(len(texto_completo), posicion + 1500)
            return texto_completo[inicio:fin]
    
    return ""


def extract_date_from_text(texto, tipo_fecha):
    """
    Extrae fechas del texto con múltiples patrones.
    """
    # Patrones específicos para cada tipo de fecha
    if tipo_fecha == "publicación":
        patrones = [
            r'Fecha de publicación[^:]*:\s*([^\.]+?)(?=\s*Fecha|\s*Correo|\s*Respuesta|\s*$)',
            r'publicación[^:]*:\s*([^\.]+?)(?=\s*Fecha|\s*Correo|\s*Respuesta|\s*$)',
            r'Fecha de publicación[^:]*:\s*(\w+\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
            r'Fecha de publicación[^:]*:\s*(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
        ]
    else:  # finalización
        patrones = [
            r'Fecha de finalizaci[oó]n[^:]*:\s*([^\.]+?)(?=\s*Correo|\s*Respuesta|\s*$)',
            r'finalizaci[oó]n[^:]*:\s*([^\.]+?)(?=\s*Correo|\s*Respuesta|\s*$)',
            r'Fecha de finalizaci[oó]n[^:]*:\s*(\w+\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
            r'Fecha de finalizaci[oó]n[^:]*:\s*(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
        ]
    
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            fecha_str = match.group(1).strip()
            # Limpiar caracteres no deseados
            fecha_str = re.sub(r'[^\w\s]', '', fecha_str)
            parsed_date = parse_spanish_date(fecha_str)
            if parsed_date:
                return parsed_date
    
    return None


def extract_email_from_text(texto):
    """
    Extrae correos electrónicos del texto.
    """
    patrones = [
        r'[Cc]orreo electr[oó]nico[^:]*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'observaciones[^:]*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'consulta[^:]*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
    ]
    
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Búsqueda general de correos que contengan "invima"
    correos = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', texto)
    for correo in correos:
        if 'invima' in correo.lower():
            return correo.strip()
    
    return None


def es_enlace_titulo_principal(enlace):
    """
    Verifica si un enlace corresponde al título principal "Proyecto de Resolución".
    """
    texto_enlace = enlace.get_text(strip=True)
    
    # Debe contener "Proyecto de Resolución" y ser relativamente largo (el título completo)
    if "Proyecto de Resolución" in texto_enlace and len(texto_enlace) > 50:
        return True
    
    # Si contiene "Proyecto" y es un enlace largo, probablemente es el principal
    if "Proyecto" in texto_enlace and len(texto_enlace) > 80:
        return True
    
    return False


def extraer_titulo_y_descripcion_con_enlaces(bloque_texto, enlace_principal, bloques_html):
    """
    Extrae el título del enlace principal y la descripción incluyendo otros enlaces del bloque.
    """
    # Obtener el texto del enlace principal (que contiene el título)
    texto_enlace_principal = enlace_principal.get_text(strip=True)
    
    # Extraer el título del enlace principal
    titulo_completo = extraer_titulo_del_enlace(texto_enlace_principal)
    
    # Decidir si cortar el título por longitud
    titulo_final = titulo_completo
    descripcion_partes = []
    
    # Si el título es muy largo (más de 150 caracteres), cortarlo
    if len(titulo_completo) > 150:
        punto_corte = encontrar_punto_corte_titulo(titulo_completo)
        titulo_final = titulo_completo[:punto_corte] + "..."
        descripcion_partes.append(f"Título completo: {titulo_completo}")
    
    # Buscar el bloque HTML que contiene este enlace para encontrar otros enlaces
    bloque_html_elementos = None
    for bloque in bloques_html:
        for elemento in bloque['elementos']:
            if enlace_principal in elemento.find_all('a', href=True):
                bloque_html_elementos = bloque['elementos']
                break
        if bloque_html_elementos:
            break
    
    # Extraer contenido adicional incluyendo otros enlaces
    contenido_adicional = extraer_contenido_con_enlaces_adicionales(
        bloque_texto, texto_enlace_principal, bloque_html_elementos
    )
    
    if contenido_adicional:
        descripcion_partes.append(contenido_adicional)
    
    # Si no hay descripción adicional, usar una parte del título
    if not descripcion_partes:
        descripcion_partes.append(titulo_completo[:300] + ("..." if len(titulo_completo) > 300 else ""))
    
    descripcion_final = " | ".join(descripcion_partes)
    
    return titulo_final, descripcion_final


def extraer_contenido_con_enlaces_adicionales(bloque_texto, texto_enlace_principal, elementos_html):
    """
    Extrae el contenido adicional del bloque incluyendo otros enlaces que no sean el principal.
    """
    # Limpiar el bloque de texto
    bloque_limpio = bloque_texto.replace("\n", " ").replace("\r", " ")
    bloque_limpio = re.sub(r'\s+', ' ', bloque_limpio).strip()
    
    # Intentar remover el texto del enlace principal del bloque
    texto_enlace_limpio = texto_enlace_principal.replace('"', '').replace('"', '').replace('"', '')
    
    # Buscar otros enlaces en los elementos HTML
    enlaces_adicionales = []
    if elementos_html:
        for elemento in elementos_html:
            enlaces_en_elemento = elemento.find_all('a', href=True)
            for enlace in enlaces_en_elemento:
                texto_enlace = enlace.get_text(strip=True)
                href_enlace = enlace.get('href', '')
                
                # No incluir el enlace principal
                if texto_enlace != texto_enlace_principal and len(texto_enlace) > 5:
                    # Construir URL completa si es necesario
                    if href_enlace.startswith('/'):
                        url_enlace = f"https://www.invima.gov.co{href_enlace}"
                    else:
                        url_enlace = href_enlace
                    
                    enlaces_adicionales.append(f"{texto_enlace} ({url_enlace})")
    
    # Buscar la posición del título principal en el bloque
    pos_titulo = bloque_limpio.lower().find(texto_enlace_limpio.lower()[:50])
    
    contenido_texto = ""
    if pos_titulo != -1:
        # Tomar el texto después del título principal
        pos_fin_titulo = pos_titulo + len(texto_enlace_limpio)
        contenido_posterior = bloque_limpio[pos_fin_titulo:].strip()
        
        # Limpiar el contenido posterior
        contenido_posterior = re.sub(r'^[^\w]*', '', contenido_posterior)
        
        if len(contenido_posterior) > 20:
            contenido_texto = contenido_posterior[:600] + ("..." if len(contenido_posterior) > 600 else "")
    else:
        # Si no se puede separar, usar una porción del bloque completo
        if len(bloque_limpio) > len(texto_enlace_principal) + 50:
            contenido_texto = bloque_limpio[:600] + ("..." if len(bloque_limpio) > 600 else "")
    
    # Combinar contenido de texto con enlaces adicionales
    partes_descripcion = []
    if contenido_texto:
        partes_descripcion.append(contenido_texto)
    
    if enlaces_adicionales:
        partes_descripcion.append("Enlaces adicionales: " + " | ".join(enlaces_adicionales))
    
    return " | ".join(partes_descripcion) if partes_descripcion else ""


def extraer_titulo_del_enlace(texto_enlace):
    """
    Extrae el título completo que acompaña a "Proyecto de Resolución".
    """
    # Limpiar comillas y caracteres extra
    titulo_limpio = texto_enlace.strip()
    titulo_limpio = re.sub(r'^["\'""'']+|["\'""'']+$', '', titulo_limpio)
    
    # Si empieza con "Proyecto de Resolución", mantener todo
    if titulo_limpio.startswith("Proyecto de Resolución"):
        return titulo_limpio
    
    # Si no empieza con "Proyecto de Resolución", agregarlo
    if "Proyecto de Resolución" not in titulo_limpio:
        return f"Proyecto de Resolución: {titulo_limpio}"
    
    return titulo_limpio


def encontrar_punto_corte_titulo(titulo):
    """
    Encuentra un punto natural para cortar el título.
    """
    puntos_corte = [
        (" - ", 140),  # Guión con espacios
        (". ", 130),   # Punto y espacio
        (", ", 120),   # Coma y espacio
        (" y ", 110),  # Conjunción
        (" de ", 100), # Preposición
    ]
    
    for separador, max_pos in puntos_corte:
        pos = titulo.rfind(separador, 0, max_pos)
        if pos > 50:  # Asegurar que el corte no sea muy temprano
            return pos + len(separador)
    
    # Si no encuentra un punto natural, cortar en 140 caracteres
    return 140


def extraer_contenido_adicional(bloque_texto, texto_enlace):
    """
    Extrae el contenido adicional del bloque que no es el título principal.
    """
    # Limpiar el bloque de texto
    bloque_limpio = bloque_texto.replace("\n", " ").replace("\r", " ")
    bloque_limpio = re.sub(r'\s+', ' ', bloque_limpio).strip()
    
    # Intentar remover el texto del enlace del bloque
    texto_enlace_limpio = texto_enlace.replace('"', '').replace('"', '').replace('"', '')
    
    # Buscar la posición del título en el bloque
    pos_titulo = bloque_limpio.lower().find(texto_enlace_limpio.lower()[:50])
    
    if pos_titulo != -1:
        # Tomar el texto después del título
        pos_fin_titulo = pos_titulo + len(texto_enlace_limpio)
        contenido_posterior = bloque_limpio[pos_fin_titulo:].strip()
        
        # Limpiar el contenido posterior
        contenido_posterior = re.sub(r'^[^\w]*', '', contenido_posterior)  # Remover caracteres no-palabra al inicio
        
        if len(contenido_posterior) > 20:  # Solo si hay contenido significativo
            return contenido_posterior[:800] + ("..." if len(contenido_posterior) > 800 else "")
    
    # Si no se puede separar, usar una porción del bloque completo
    if len(bloque_limpio) > len(texto_enlace) + 50:
        return bloque_limpio[:800] + ("..." if len(bloque_limpio) > 800 else "")
    
    return ""


def parse_spanish_date(fecha_str):
    """
    Convierte fechas en español a objeto datetime.
    """
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    fecha_limpia = re.sub(r'^(lunes|martes|miércoles|jueves|viernes|sábado|domingo)\s+', '', fecha_str.lower().strip())
    
    patron = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})'
    match = re.search(patron, fecha_limpia)
    
    if match:
        dia = int(match.group(1))
        mes_nombre = match.group(2)
        año = int(match.group(3))
        
        if mes_nombre in meses:
            mes = meses[mes_nombre]
            return datetime(año, mes, dia)
    
    return None


if __name__ == "__main__":
    # Ejecutar el scraper y mostrar los resultados
    items = asyncio.run(scrape_invima_proyectos_normativos_v2())

    if items:
        # Formatear salida como JSON
        print(json.dumps([{
            **item,
            'presentation_date': item['presentation_date'].strftime('%Y-%m-%d') if item['presentation_date'] else None
        } for item in items], indent=4, ensure_ascii=False))
    else:
        print("No se encontraron proyectos normativos")