import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import asyncio
import re

async def scrape_digemid_noticias():
    # URL principal donde se encuentran las noticias
    url = "https://www.digemid.minsa.gob.pe/webDigemid/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
    }
    
    # Configuración de httpx con tiempo de espera aumentado
    timeout = httpx.Timeout(30.0)
    
    async with httpx.AsyncClient(verify=False, timeout=timeout, follow_redirects=True) as client:
        try:
            print(f"Iniciando scraping de {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            print(f"Estado de la respuesta: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar los elementos 'post-item' que contienen las noticias
            noticias = soup.find_all('div', class_='post-item')
            
            items = []
            for noticia in noticias:
                try:
                    # Título y URL
                    titulo_elem = noticia.find('h3', class_='porto-post-title')
                    if not titulo_elem:
                        continue
                        
                    link = titulo_elem.find('a')
                    titulo = link.text.strip()
                    url_noticia = link['href']
                    
                    # Descripción
                    descripcion_elem = noticia.find('p', class_='post-excerpt')
                    descripcion = descripcion_elem.text.strip() if descripcion_elem else titulo
                    
                    # Fecha - formato DD/MM/YYYY
                    fecha_elem = noticia.find('span', class_='meta-date')
                    fecha_text = fecha_elem.text.strip() if fecha_elem else ""
                    # Extraer la fecha con una expresión regular
                    fecha_match = re.search(r'(\d{2}/\d{2}/\d{4})', fecha_text)
                    
                    if fecha_match:
                        fecha_str = fecha_match.group(1)
                        fecha = datetime.strptime(fecha_str, '%d/%m/%Y')
                    else:
                        # Si no se encuentra la fecha, usar la fecha actual
                        fecha = datetime.now()
                    
                    # Categoría
                    categoria_elem = noticia.find('span', class_='cat-names')
                    categoria = categoria_elem.text.strip() if categoria_elem else "General"
                    
                    item = {
                        'title': titulo,
                        'description': descripcion,
                        'source_url': url_noticia,
                        'source_type': 'Ejecutivo',
                        'country': 'Perú',
                        'category': 'Noticias',
                        'presentation_date': fecha,
                        'institution': 'DIGEMID Perú'
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

# Ejecutar el scraper
if __name__ == "__main__":
    items = asyncio.run(scrape_digemid_noticias())
    for item in items:
        print(f"\nTítulo: {item['title']}")
        print(f"Descripción: {item['description']}")
        print(f"URL: {item['source_url']}")
        print(f"Fecha: {item['presentation_date']}")
        print(f"Categoría: {item['category']}")
    
    print(f"\nTotal noticias extraídas: {len(items)}")