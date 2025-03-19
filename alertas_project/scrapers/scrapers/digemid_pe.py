import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import asyncio

async def scrape_digemid_noticias():
    url = "https://www.digemid.minsa.gob.pe/webDigemid/?s="
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            print(f"Iniciando scraping de {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            noticias = soup.find_all('article', class_='post')
            
            items = []
            for noticia in noticias:
                try:
                    # Título y URL
                    titulo_elem = noticia.find('h2', class_='entry-title')
                    link = titulo_elem.find('a')
                    titulo = link.text.strip()
                    url_noticia = link['href']
                    
                    # Fecha (ISO-8601 en el attr datetime)
                    fecha_div = noticia.find('div', class_='post-date')
                    fecha_time = fecha_div.find('time')['datetime']  # p.e. "2024-12-05T21:27:54-05:00"
                    fecha = datetime.fromisoformat(fecha_time)
                    
                    # Descripción
                    descripcion_elem = noticia.find('p', class_='post-excerpt')
                    descripcion = descripcion_elem.text.strip() if descripcion_elem else titulo
                    
                    # Categoría
                    categoria_elem = noticia.find('span', class_='meta-cats')
                    categoria = categoria_elem.find('a').text.strip() if categoria_elem else "General"
                    
                    item = {
                        'title': titulo,
                        'description': descripcion,
                        'source_url': url_noticia,
                        'source_type': 'noticia',
                        'country': 'Perú',
                        'category': categoria,
                        'presentation_date': fecha,
                        'institution': 'Digemid_Perú'
                    }
                    
                    items.append(item)
                except Exception as e:
                    print(f"Error procesando noticia DIGEMID: {str(e)}")
                    continue
            
            print(f"Se encontraron {len(items)} noticias de DIGEMID")
            return items
            
        except Exception as e:
            print(f"Error durante el scraping DIGEMID: {str(e)}")
            return []
