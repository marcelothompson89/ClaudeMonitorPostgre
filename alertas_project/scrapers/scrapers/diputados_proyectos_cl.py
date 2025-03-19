import asyncio
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json

async def scrape_diputados_proyectos_cl():
    print("[Diputados Proyectos_CL] Iniciando scraping...")
    base_url = "https://www.camara.cl/legislacion/ProyectosDeLey/proyectos_ley.aspx"
    items = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url) as response:
                if response.status != 200:
                    print(f"[Diputados Proyectos_CL] Error HTTP: {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Buscar todos los artículos de proyectos
                proyectos = soup.find_all('article', class_='proyecto')
                if not proyectos:
                    print("[Diputados Proyectos_CL] No se encontraron proyectos")
                    return []
                
                for proyecto in proyectos:
                    try:
                        # Extraer número de boletín
                        boletin = proyecto.find('span', class_='numero').text.strip()
                        
                        # Extraer tipo de proyecto
                        tipo_elem = proyecto.find('ul', class_='etapas-legislativas')
                        tipo = tipo_elem.find_all('li')[1].text.strip() if tipo_elem else "No especificado"
                        
                        # Extraer título y URL
                        link = proyecto.find('h3').find('a')
                        titulo = link.text.strip()
                        url = urljoin(base_url, link['href'])
                        
                        # Extraer fecha
                        fecha_str = proyecto.find('span', class_='fecha').text.strip()  # formato: "18 Dic. 2024"
                        try:
                            dia, mes, anio = fecha_str.split()
                            meses = {
                                'Ene.': 1, 'Feb.': 2, 'Mar.': 3, 'Abr.': 4, 'May.': 5, 'Jun.': 6,
                                'Jul.': 7, 'Ago.': 8, 'Sep.': 9, 'Oct.': 10, 'Nov.': 11, 'Dic.': 12
                            }
                            fecha = datetime(int(anio), meses[mes], int(dia))
                        except Exception as e:
                            print(f"[Diputados Proyectos_CL] Error procesando fecha {fecha_str}: {str(e)}")
                            fecha = datetime.now()
                        
                        # Extraer estado
                        estado_elem = proyecto.find_all('ul', class_='etapas-legislativas')[-1]
                        estado = estado_elem.find_all('li')[1].text.strip() if estado_elem else "No especificado"
                        
                        item = {
                            "title": titulo,
                            "description": f"Boletín: {boletin} - Estado: {estado} - Tipo: {tipo}",
                            "source_url": url,
                            "source_type": "diputados_proyectos_cl",
                            "country": "Chile",
                            "presentation_date": fecha,
                            "category": "Proyectos de Ley",
                            "institution": "diputados_proyectos_cl",
                            "metadata": json.dumps({
                                "boletin": boletin,
                                "estado": estado,
                                "tipo": tipo
                            })
                        }
                        items.append(item)
                    except Exception as e:
                        print(f"[Diputados Proyectos_CL] Error procesando proyecto: {str(e)}")
                        continue
                
        print(f"[Diputados Proyectos_CL] Se encontraron {len(items)} proyectos")
        return items
    except Exception as e:
        print(f"[Diputados Proyectos_CL] Error: {str(e)}")
        return []
