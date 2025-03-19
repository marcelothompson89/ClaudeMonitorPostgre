import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re

async def scrape_senado_noticias_cl():
    print("[Senado Noticias_CL] Iniciando scraping...")
    url = "https://www.senado.cl/comunicaciones/noticias"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            print(f"[Senado Noticias_CL] Accediendo a URL: {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            print(f"[Senado Noticias_CL] Respuesta recibida. Status code: {response.status_code}")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Encontrar todas las noticias
            noticias = soup.find_all('a', class_='card')
            items = []
            
            for noticia in noticias:
                try:
                    # Extraer URL
                    url = f"https://www.senado.cl{noticia['href']}"
                    
                    # Extraer título
                    titulo_element = noticia.find('h3', class_='subtitle')
                    if not titulo_element:
                        continue
                    title = titulo_element.text.strip()
                    
                    # Extraer fecha
                    fecha_element = noticia.find('p', class_='color-blue-75')
                    if not fecha_element:
                        continue
                        
                    fecha_str = fecha_element.text.strip()  # "26 de diciembre de 2024" o "26 de diciembre 2024"
                    
                    # Convertir mes a número
                    meses = {
                        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
                        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
                    }
                    
                    try:
                        # Intentar ambos formatos de fecha
                        fecha = None
                        # Primero intentar con "de" antes del año
                        match = re.match(r'(\d+)\s+de\s+(\w+)\s+de\s+(\d{4})', fecha_str)
                        if match:
                            dia, mes, anio = match.groups()
                        else:
                            # Si no funciona, intentar sin "de" antes del año
                            match = re.match(r'(\d+)\s+de\s+(\w+)\s+(\d{4})', fecha_str)
                            if match:
                                dia, mes, anio = match.groups()
                            else:
                                print(f"[Senado Noticias_CL] Error: formato de fecha no reconocido: {fecha_str}")
                                continue
                        
                        mes_num = meses[mes.lower()]
                        fecha = datetime(int(anio), mes_num, int(dia))
                        
                    except (ValueError, KeyError) as e:
                        print(f"[Senado Noticias_CL] Error procesando fecha: {fecha_str} - {str(e)}")
                        continue
                    
                    # Extraer categorías
                    categorias_div = noticia.find('div', class_='categorias')
                    categorias = []
                    if categorias_div:
                        for cat in categorias_div.find_all('p', class_='color-blue-100'):
                            categorias.append(cat.text.strip())
                    categoria = categorias[0] if categorias else "General"
                    
                    # Extraer imagen si existe
                    img = noticia.find('img')
                    img_data = {}
                    if img:
                        img_data = {
                            'url': img.get('src', ''),
                            'alt': img.get('alt', ''),
                            'srcset': img.get('srcset', '')
                        }
                    
                    # Crear el objeto de la noticia
                    item = {
                        "title": title,
                        "description": f"[{categoria}] {title}",
                        "source_url": url,
                        "source_type": "senado_noticias_cl",
                        "country": "Chile",
                        "presentation_date": fecha,
                        "category": "Noticias",
                        "institution": "senado_noticias_cl",
                        "metadata": json.dumps({
                            "categoria": categoria,
                            "categorias": categorias,
                            "imagen": img_data,
                            "institucion": "Senado"
                        })
                    }
                    
                    items.append(item)
                    print(f"[Senado Noticias_CL] Noticia procesada: {title[:100]}")
                    
                except Exception as e:
                    print(f"[Senado Noticias_CL] Error procesando noticia: {str(e)}")
                    continue
            
            print(f"[Senado Noticias_CL] Se encontraron {len(items)} noticias")
            return items
            
        except Exception as e:
            print(f"[Senado Noticias_CL] Error: {str(e)}")
            return []
