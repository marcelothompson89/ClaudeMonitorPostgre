import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_ispch_resoluciones_cl():
    print("[ISPCH Resoluciones_CL] Iniciando scraping...")
    url = "https://www.ispch.gob.cl/resoluciones/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            print(f"[ISPCH Resoluciones_CL] Accediendo a URL: {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            print(f"[ISPCH Resoluciones_CL] Respuesta recibida. Status code: {response.status_code}")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Encontrar la tabla de resoluciones
            tabla = soup.find('table', class_='table')
            if not tabla:
                print("[ISPCH Resoluciones_CL] No se encontró la tabla de resoluciones")
                return []
            
            # Encontrar todas las resoluciones en la tabla
            resoluciones = tabla.find_all('tr')
            items = []
            
            for resolucion in resoluciones[1:]:  # Skip header row
                try:
                    cols = resolucion.find_all('td')
                    if len(cols) < 4:
                        continue
                        
                    # Extraer datos básicos
                    numero = cols[0].text.strip()
                    link_element = cols[1].find('a')
                    if not link_element:
                        continue
                        
                    titulo = link_element.text.strip()
                    url = link_element['href']
                    
                    # Extraer y validar fecha
                    fecha_str = cols[2].text.strip()  # "08-11-2024"
                    try:
                        dia, mes, anio = map(int, fecha_str.split('-'))
                        fecha = datetime(anio, mes, dia)
                    except ValueError:
                        print(f"[ISPCH Resoluciones_CL] Error procesando fecha: {fecha_str}")
                        continue
                    
                    # Extraer categoría
                    categoria = cols[3].text.strip()
                    
                    # Crear el objeto de la resolución
                    item = {
                        'title': f"Resolución N° {numero}: {titulo}",
                        'description': f"Categoría: {categoria}\n{titulo}",
                        'source_url': url,
                        'source_type': 'ispch_resoluciones_cl',
                        'country': 'Chile',
                        'presentation_date': fecha,
                        'category': "Resoluciones",
                        'institution': 'ispch_resoluciones_cl',
                        'metadata': json.dumps({
                            'numero_resolucion': numero,
                            'categoria': categoria,
                            'tipo': 'Resolución ISPCH'
                        })
                    }
                    items.append(item)
                    print(f"[ISPCH Resoluciones_CL] Resolución procesada: N° {numero}")
                    
                except Exception as e:
                    print(f"[ISPCH Resoluciones_CL] Error procesando resolución: {str(e)}")
                    continue
            
            print(f"[ISPCH Resoluciones_CL] Se encontraron {len(items)} resoluciones")
            return items
            
        except Exception as e:
            print(f"[ISPCH Resoluciones_CL] Error: {str(e)}")
            return []
