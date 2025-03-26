import asyncio
from datetime import datetime
import re
from bs4 import BeautifulSoup
import aiohttp
from urllib.parse import urljoin
import json

MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Setiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# Invertir el diccionario para búsquedas por nombre
MESES_NUM = {v: k for k, v in MESES.items()}

async def scrape_digesa_noticias_pe():
    """
    Scraper para noticias de DIGESA que procesa solo el mes más reciente encontrado.
    """
    print("[DIGESA Noticias_PE] Iniciando scraping...")
    base_url = "http://www.digesa.minsa.gob.pe/noticias/index.asp"
    items = []

    try:
        # Configurar sesión HTTP con timeout y headers
        timeout = aiohttp.ClientTimeout(total=60)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            print(f"[DIGESA Noticias_PE] Accediendo a URL: {base_url}")
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with session.get(base_url) as response:
                        if response.status == 200:
                            html = await response.text()
                            print(f"[DIGESA Noticias_PE] Respuesta obtenida, longitud HTML: {len(html)} caracteres")
                            
                            # Analizar el HTML
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # PASO 1: Encontrar todos los encabezados h4 que contengan mes y año
                            all_headers = soup.find_all('h4')
                            print(f"[DIGESA Noticias_PE] Total de encabezados encontrados: {len(all_headers)}")
                            
                            # Listado de todos los encabezados de meses
                            month_headers = []
                            
                            # Para cada encabezado, verificar si contiene un mes y año
                            for header in all_headers:
                                header_text = header.text.strip()
                                
                                # Buscar patrones de mes y año (por ejemplo: "Enero 2025")
                                for month_name in MESES.values():
                                    if month_name in header_text:
                                        year_match = re.search(r'(\d{4})', header_text)
                                        if year_match:
                                            year = int(year_match.group(1))
                                            month_num = MESES_NUM[month_name]
                                            month_headers.append({
                                                'header': header,
                                                'month_name': month_name,
                                                'month_num': month_num,
                                                'year': year,
                                                'text': header_text
                                            })
                                            break
                            
                            # Ordenar los encabezados por año y mes (más reciente primero)
                            month_headers.sort(key=lambda x: (x['year'], x['month_num']), reverse=True)
                            
                            # Mostrar los meses encontrados
                            print(f"[DIGESA Noticias_PE] Meses ordenados encontrados: {len(month_headers)}")
                            for i, mh in enumerate(month_headers[:5]):  # Mostrar solo los 5 más recientes
                                print(f"  {i+1}. {mh['month_name']} {mh['year']}")
                            
                            # PASO 2: Procesar SOLO el mes más reciente
                            if month_headers:
                                month_data = month_headers[0]  # Tomar solo el primer mes (más reciente)
                                
                                header = month_data['header']
                                month_name = month_data['month_name']
                                year = month_data['year']
                                
                                print(f"[DIGESA Noticias_PE] Procesando SOLO el mes más reciente: {month_name} {year}")
                                
                                # Buscar el <ul> de noticias - puede estar en diferentes configuraciones
                                news_list = None
                                
                                # 1. Verificar si el header está dentro de un <li> que contiene un <ul>
                                parent_li = header.find_parent('li')
                                if parent_li:
                                    news_list = parent_li.find('ul')
                                    
                                # 2. Si no, buscar el siguiente <ul> después del encabezado
                                if not news_list:
                                    news_list = header.find_next('ul')
                                
                                # 3. Si todavía no encontramos la lista, buscar un <ul> cercano
                                if not news_list:
                                    # Buscar entre hermanos y primos
                                    for sibling in header.find_next_siblings():
                                        if sibling.name == 'ul':
                                            news_list = sibling
                                            break
                                        elif sibling.find('ul'):
                                            news_list = sibling.find('ul')
                                            break
                                
                                if not news_list:
                                    print(f"[DIGESA Noticias_PE] No se encontró lista de noticias para {month_name} {year}")
                                else:
                                    # Encontrar todas las noticias en la lista
                                    news_items = news_list.find_all('li')
                                    print(f"[DIGESA Noticias_PE] Encontradas {len(news_items)} noticias para {month_name} {year}")
                                    
                                    # Procesar cada noticia
                                    month_item_count = 0
                                    for news_item in news_items:
                                        try:
                                            link = news_item.find('a')
                                            if not link:
                                                continue
                                            
                                            href = link.get('href', '')
                                            texto = link.text.strip()
                                            
                                            # Extraer la fecha del texto (formato: DD.MM.YYYY)
                                            fecha_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', texto)
                                            
                                            if fecha_match:
                                                dia, mes, anio = fecha_match.groups()
                                                fecha = datetime.strptime(f"{anio}-{mes}-{dia}", "%Y-%m-%d")
                                                
                                                # Construir URL completa
                                                noticia_url = urljoin("http://www.digesa.minsa.gob.pe/noticias/", href)
                                                
                                                # Limpiar el título (quitar la fecha del inicio)
                                                titulo = re.sub(r'^\d{2}\.\d{2}\.\d{4}\.?\s*', '', texto).strip()
                                                
                                                metadata = {
                                                    'tipo': 'noticia',
                                                    'año': anio,
                                                    'mes': mes,
                                                    'dia': dia,
                                                    'fecha': fecha.strftime("%Y-%m-%d"),
                                                    'titulo': titulo,
                                                    'url': noticia_url
                                                }
                                                
                                                item = {
                                                    'title': titulo,
                                                    'description': titulo,
                                                    'country': 'Perú',
                                                    'source_url': noticia_url,
                                                    'source_type': 'Ejecutivo',
                                                    'presentation_date': fecha,
                                                    'category': 'Noticias',
                                                    'institution': 'DIGESA Perú',
                                                    'metadata': json.dumps(metadata)
                                                }
                                                
                                                items.append(item)
                                                month_item_count += 1
                                                print(f"[DIGESA Noticias_PE] Noticia {month_item_count}: {titulo[:50]}...")
                                            else:
                                                print(f"[DIGESA Noticias_PE] No se encontró fecha en: {texto[:50]}...")
                                        
                                        except Exception as e:
                                            print(f"[DIGESA Noticias_PE] Error procesando noticia: {str(e)}")
                                    
                                    print(f"[DIGESA Noticias_PE] Total de noticias procesadas para {month_name} {year}: {month_item_count}")
                            else:
                                print("[DIGESA Noticias_PE] No se encontraron meses disponibles")
                            
                            # PASO 3: Si no encontramos noticias, hacer una búsqueda alternativa
                            if not items:
                                print("[DIGESA Noticias_PE] No se encontraron noticias con el método principal. Intentando método alternativo...")
                                
                                # Buscar directamente todos los enlaces que parezcan noticias
                                all_links = soup.find_all('a', href=re.compile(r'nota\d+\.asp'))
                                print(f"[DIGESA Noticias_PE] Encontrados {len(all_links)} enlaces de noticias directamente")
                                
                                # Limitar a 30 para no procesar demasiados
                                for i, link in enumerate(all_links[:30]):
                                    try:
                                        href = link.get('href', '')
                                        texto = link.text.strip()
                                        
                                        # Extraer la fecha
                                        fecha_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', texto)
                                        if fecha_match:
                                            dia, mes, anio = fecha_match.groups()
                                            fecha = datetime.strptime(f"{anio}-{mes}-{dia}", "%Y-%m-%d")
                                            
                                            # Construir URL y título
                                            noticia_url = urljoin("http://www.digesa.minsa.gob.pe/noticias/", href)
                                            titulo = re.sub(r'^\d{2}\.\d{2}\.\d{4}\.?\s*', '', texto).strip()
                                            
                                            item = {
                                                'title': titulo,
                                                'description': titulo,
                                                'country': 'Perú',
                                                'source_url': noticia_url,
                                                'source_type': 'DIGESA',
                                                'presentation_date': fecha,
                                                'category': 'Noticias',
                                                'institution': 'DIGESA_noticias_pe',
                                                'metadata': json.dumps({
                                                    'tipo': 'noticia',
                                                    'año': anio,
                                                    'fecha': fecha.strftime("%Y-%m-%d"),
                                                    'titulo': titulo,
                                                    'url': noticia_url
                                                })
                                            }
                                            
                                            items.append(item)
                                            print(f"[DIGESA Noticias_PE] Noticia alternativa {i+1}: {titulo[:50]}...")
                                    except Exception as e:
                                        print(f"[DIGESA Noticias_PE] Error procesando enlace alternativo: {str(e)}")
                            
                            # Finalizar
                            print(f"[DIGESA Noticias_PE] Total de noticias extraídas: {len(items)}")
                            return items
                            
                        else:
                            print(f"[DIGESA Noticias_PE] Error HTTP: {response.status}")
                            if attempt < max_retries - 1:
                                print(f"[DIGESA Noticias_PE] Reintentando ({attempt+1}/{max_retries})...")
                                await asyncio.sleep(2)  # Esperar antes de reintentar
                            else:
                                return []
                                
                except Exception as e:
                    print(f"[DIGESA Noticias_PE] Error en intento {attempt+1}: {str(e)}")
                    if attempt < max_retries - 1:
                        print(f"[DIGESA Noticias_PE] Reintentando ({attempt+1}/{max_retries})...")
                        await asyncio.sleep(2)
                    else:
                        raise
            
            return []
            
    except Exception as e:
        print(f"[DIGESA Noticias_PE] Error general: {str(e)}")
        return []

# # Ejecutar el script directamente
# if __name__ == "__main__":
#     items = asyncio.run(scrape_digesa_noticias_pe())
    
#     # Imprimir resultados en formato JSON
#     if items:
#         formatted_items = [
#             {
#                 **item,
#                 'presentation_date': item['presentation_date'].strftime('%Y-%m-%d %H:%M:%S') 
#                     if isinstance(item['presentation_date'], datetime) else None
#             }
#             for item in items
#         ]
        
#         print(json.dumps(formatted_items, indent=4, ensure_ascii=False))
#     else:
#         print("No se encontraron noticias para mostrar.")