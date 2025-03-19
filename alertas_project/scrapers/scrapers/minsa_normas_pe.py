import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_minsa_normas_pe():
    print("[MINSA Normas_PE] Iniciando scraping...")
    url = "https://www.gob.pe/institucion/minsa/normas-legales"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            print(f"[MINSA Normas_PE] Accediendo a URL: {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            print(f"[MINSA Normas_PE] Respuesta recibida. Status code: {response.status_code}")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Encontrar todas las normas
            normas = soup.find_all('li', class_='hover:bg-gray-70')
            items = []
            
            for norma in normas:
                try:
                    # Extraer título y URL
                    link = norma.find('a', class_='mb-2')
                    if not link:
                        continue
                        
                    title = link.text.strip()
                    url = f"https://www.gob.pe{link['href']}"
                    
                    # Extraer fecha
                    fecha_element = norma.find('time')
                    if not fecha_element:
                        continue
                        
                    fecha_str = fecha_element.text.strip()  # "26 de diciembre de 2024"
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
                        print(f"[MINSA Normas_PE] Error procesando fecha: {fecha_str}")
                        continue
                    
                    # Extraer descripción
                    description = norma.find('div', {'id': lambda x: x and x.startswith('p-filter-item-')})
                    description = description.text.strip() if description else ""
                    if not description:
                        description = title
                    
                    # Extraer URL del PDF
                    pdf_link = norma.find('a', class_='btn')
                    pdf_url = pdf_link['href'] if pdf_link else url
                    
                    # Crear el objeto de la norma
                    item = {
                        "title": title,
                        "description": description,
                        "source_url": pdf_url,
                        "source_type": "minsa_normas_pe",
                        "country": "Perú",
                        "presentation_date": fecha,
                        "category": "Normas",
                        "institution": "minsa_normas_pe",
                        "metadata": json.dumps({
                            "url_detalle": url,
                            "tipo": "Norma Legal MINSA",
                            "institucion": "MINSA"
                        })
                    }
                    
                    items.append(item)
                    print(f"[MINSA Normas_PE] Norma procesada: {title[:100]}")
                    
                except Exception as e:
                    print(f"[MINSA Normas_PE] Error procesando norma: {str(e)}")
                    continue
            
            print(f"[MINSA Normas_PE] Se encontraron {len(items)} normas")
            return items
            
        except Exception as e:
            print(f"[MINSA Normas_PE] Error: {str(e)}")
            return []
