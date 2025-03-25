import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_minsa_noticias_pe():
    print("[MINSA Noticias_PE] Iniciando scraping...")
    url = "https://www.gob.pe/institucion/minsa/noticias"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            print(f"[MINSA Noticias_PE] Accediendo a URL: {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            print(f"[MINSA Noticias_PE] Respuesta recibida. Status code: {response.status_code}")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Encontrar todas las noticias
            noticias = soup.find_all('li', class_='scrollable__item')
            items = []
            
            for noticia in noticias:
                try:
                    # Extraer título y URL
                    link = noticia.find('a', class_='text-primary')
                    if not link:
                        continue
                        
                    title = link.text.strip()
                    url = f"https://www.gob.pe{link['href']}"
                    
                    # Extraer fecha
                    fecha_element = noticia.find('time')
                    if not fecha_element:
                        continue
                        
                    fecha_str = fecha_element.text.strip()  # "26 de diciembre de 2024 - 3:15 p. m."
                    fecha_str = fecha_str.split('-')[0].strip()  # "26 de diciembre de 2024"
                    
                    # Convertir mes a número
                    meses = {
                        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
                        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
                    }
                    try:
                        dia, _, mes, _, anio = fecha_str.split()
                        mes_num = meses[mes.lower()]
                        fecha = datetime(int(anio), mes_num, int(dia))
                    except (ValueError, KeyError):
                        print(f"[MINSA Noticias_PE] Error procesando fecha: {fecha_str}")
                        continue
                    
                    # Extraer descripción
                    description_div = noticia.find('div', {'id': lambda x: x and x.endswith('-description')})
                    description = description_div.text.strip() if description_div else ""
                    
                    # Extraer imagen si existe
                    img = noticia.find('img')
                    img_data = {}
                    if img:
                        img_data = {
                            'url': img.get('src', ''),
                            'alt': img.get('alt', '')
                        }
                    
                    # Si no hay descripción, usar el título
                    if not description:
                        description = title
                    
                    # Crear el objeto de la noticia
                    item = {
                        "title": title,
                        "description": description,
                        "source_url": url,
                        "source_type": "Ejecutivo",
                        "country": "Perú",
                        "presentation_date": fecha,
                        "category": "Noticias",
                        "institution": "Ministerio de Salud Perú",
                        "metadata": json.dumps({
                            "imagen": img_data,
                            "tipo": "Noticia Ministerio de Salud Perú",
                            "institucion": "Ministerio de Salud Perú"
                        })
                    }
                    
                    items.append(item)
                    print(f"[MINSA Noticias_PE] Noticia procesada: {title[:100]}")
                    
                except Exception as e:
                    print(f"[MINSA Noticias_PE] Error procesando noticia: {str(e)}")
                    continue
            
            print(f"[MINSA Noticias_PE] Se encontraron {len(items)} noticias")
            return items
            
        except Exception as e:
            print(f"[MINSA Noticias_PE] Error: {str(e)}")
            return []
