# scrapers/anamed_scraper.py
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import re

async def scrape_anamed_cl():
    url = "https://www.ispch.gob.cl/categorias-alertas/anamed/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            table = soup.find('table')
            if not table:
                print("No se encontró la tabla en la página")
                return []
            
            rows = table.find_all('tr')[1:]  # Ignoramos la fila de encabezado
            items = []
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 5:
                    continue
                
                # Extraer enlaces
                alerta_link = cols[4].find('a', text=re.compile('Alerta', re.I))
                nota_link = cols[4].find('a', text=re.compile('Nota', re.I))
                publicacion_link = cols[4].find('a', text=re.compile('Publicación', re.I))

                # Parsear fecha
                fecha_str = cols[0].get_text(strip=True)
                try:
                    fecha = datetime.strptime(fecha_str, '%d-%m-%Y')
                except ValueError:
                    continue
                
                item = {
                    'title': cols[3].get_text(strip=True),
                    'description': cols[3].get_text(strip=True),
                    'source_type': "Ejecutivo",
                    'category': "Normas",
                    'country': 'Chile',
                    'source_url': alerta_link.get('href') if alerta_link else None,
                    'presentation_date': fecha,
                    'metadata': {
                        'nota_url': nota_link.get('href') if nota_link else None,
                        'publicacion_url': publicacion_link.get('href') if publicacion_link else None
                    },
                    'institution': 'ANAMED Chile'
                }
                items.append(item)
            
            return items

        except Exception as e:
            print(f"Error: {e}")
            return []
