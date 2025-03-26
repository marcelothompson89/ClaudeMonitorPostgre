import asyncio
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json

async def scrape_diputados_noti_cl():
    print("[Diputados Noticias Scraper] Iniciando scraping...")
    base_url = "https://www.camara.cl/cms/noticias/"
    items = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url) as response:
                if response.status != 200:
                    print(f"[Diputados Noticias_CL] Error HTTP: {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                noticias = soup.find_all('div', class_='td_module_4')
                for noticia in noticias:
                    try:
                        link_element = noticia.find('h3', class_='entry-title').find('a')
                        title = link_element['title']
                        url = link_element['href']
                        description = noticia.find('div', class_='td-excerpt').text.strip()
                        
                        # Fecha ISO-8601 en <time datetime="">
                        date_text = noticia.find('time', class_='entry-date')['datetime']
                        date = datetime.fromisoformat(date_text.replace('-03:00', '+00:00'))
                        
                        category_elem = noticia.find('a', class_='td-post-category')
                        category_text = category_elem.text.strip() if category_elem else "Sin categoría"
                        
                        img = noticia.find('img', class_='entry-thumb')
                        img_url = img['src'] if img else None
                        
                        # CAMBIO AQUÍ: metadata como diccionario, no como string JSON
                        item = {
                            "title": title,
                            "description": description,
                            "source_url": url,
                            "source_type": "Legislativo",
                            "country": "Chile",
                            "presentation_date": date, 
                            'category': "Noticias",
                            "institution": 'Cámara de Diputados Chile',
                            "metadata": {
                                "image_url": img_url
                            }
                        }
                        items.append(item)
                    except Exception as e:
                        print(f"[Diputados Noticias_CL] Error procesando noticia: {str(e)}")
                        continue
                
        print(f"[Diputados Noticias_CL] Se encontraron {len(items)} noticias")
        return items
    except Exception as e:
        print(f"[Diputados Noticias_CL] Error: {str(e)}")
        return []