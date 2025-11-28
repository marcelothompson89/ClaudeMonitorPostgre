import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re

async def scrape_senado_noticias_cl():
    print("[Senado Noticias_CL] Iniciando scraping...")
    url = "https://www.senado.cl/comunicaciones/noticias"
    
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    def parse_fecha(fecha_str):
        if not fecha_str:
            return None
        fecha_str = fecha_str.strip()
        
        # Formato: "17 de noviembre 2025 12:45 hrs"
        match = re.match(r'(\d+)\s+de\s+(\w+)\s+(\d{4})\s+\d+:\d+', fecha_str)
        if match:
            dia, mes, anio = match.groups()
            try:
                return datetime(int(anio), meses[mes.lower()], int(dia))
            except (ValueError, KeyError):
                pass
        
        # Formato: "26 de noviembre de 2025"
        match = re.match(r'(\d+)\s+de\s+(\w+)\s+de\s+(\d{4})', fecha_str)
        if match:
            dia, mes, anio = match.groups()
            try:
                return datetime(int(anio), meses[mes.lower()], int(dia))
            except (ValueError, KeyError):
                pass
        
        # Formato: "26 de noviembre 2025"
        match = re.match(r'(\d+)\s+de\s+(\w+)\s+(\d{4})', fecha_str)
        if match:
            dia, mes, anio = match.groups()
            try:
                return datetime(int(anio), meses[mes.lower()], int(dia))
            except (ValueError, KeyError):
                pass
        
        return None
    
    def extraer_imagen(elemento):
        img = elemento.find('img')
        if img:
            return {
                'url': img.get('src', ''),
                'alt': img.get('alt', ''),
                'srcset': img.get('srcset', '')
            }
        return {}
    
    async with async_playwright() as p:
        try:
            print("[Senado Noticias_CL] Iniciando navegador...")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            print(f"[Senado Noticias_CL] Accediendo a URL: {url}")
            await page.goto(url)
            
            # Esperar a que carguen las noticias de la lista principal
            print("[Senado Noticias_CL] Esperando carga de contenido...")
            await page.wait_for_selector('div.col-lg-10 a.card', timeout=15000)
            
            # Esperar un poco más para asegurar que todo el contenido dinámico cargó
            await page.wait_for_timeout(2000)
            
            html = await page.content()
            await browser.close()
            
            print("[Senado Noticias_CL] Contenido obtenido, procesando...")
            soup = BeautifulSoup(html, 'html.parser')
            
            items = []
            urls_procesadas = set()
            
            # ========================================
            # PARTE 1: Noticia principal destacada
            # ========================================
            print("[Senado Noticias_CL] Procesando noticia destacada principal...")
            
            article_destacado = soup.find('article', class_='card--featured')
            if article_destacado:
                try:
                    enlace_padre = article_destacado.find_parent('a')
                    href = enlace_padre.get('href', '') if enlace_padre else ''
                    noticia_url = f"https://www.senado.cl{href}" if href else None
                    
                    if noticia_url and noticia_url not in urls_procesadas:
                        titulo_el = article_destacado.find('h3', class_='h4')
                        titulo = titulo_el.text.strip() if titulo_el else None
                        
                        fecha_el = article_destacado.find('p', class_='mb-1')
                        fecha = parse_fecha(fecha_el.text if fecha_el else None)
                        
                        cat_el = article_destacado.find('p', class_='uppercase')
                        categoria = cat_el.text.strip() if cat_el else "General"
                        
                        if titulo:
                            items.append({
                                "title": titulo,
                                "description": f"[{categoria}] {titulo}",
                                "source_url": noticia_url,
                                "source_type": "Legislativo",
                                "country": "Chile",
                                "presentation_date": fecha,
                                "category": "Noticias",
                                "institution": "Senado Chile",
                                "metadata": json.dumps({
                                    "categoria": categoria,
                                    "imagen": extraer_imagen(article_destacado),
                                    "tipo": "destacada_principal"
                                })
                            })
                            urls_procesadas.add(noticia_url)
                            print(f"[Senado Noticias_CL] Destacada principal: {titulo[:60]}...")
                except Exception as e:
                    print(f"[Senado Noticias_CL] Error en noticia principal: {str(e)}")
            
            # ========================================
            # PARTE 2: Noticias secundarias (col-lg-4)
            # ========================================
            print("[Senado Noticias_CL] Procesando noticias secundarias...")
            
            noticias_secundarias = soup.select('div.col-lg-4 > a.card')
            for noticia in noticias_secundarias:
                try:
                    href = noticia.get('href', '')
                    noticia_url = f"https://www.senado.cl{href}" if href else None
                    
                    if not noticia_url or noticia_url in urls_procesadas:
                        continue
                    
                    titulo_el = noticia.find('h3', class_='subtitle')
                    titulo = titulo_el.text.strip() if titulo_el else None
                    
                    fecha_el = noticia.find('p', class_='color-blue-75')
                    fecha = parse_fecha(fecha_el.text if fecha_el else None)
                    
                    cat_el = noticia.find('p', class_='color-blue-100')
                    categoria = cat_el.text.strip() if cat_el else "General"
                    
                    if titulo:
                        items.append({
                            "title": titulo,
                            "description": f"[{categoria}] {titulo}",
                            "source_url": noticia_url,
                            "source_type": "Legislativo",
                            "country": "Chile",
                            "presentation_date": fecha,
                            "category": "Noticias",
                            "institution": "Senado Chile",
                            "metadata": json.dumps({
                                "categoria": categoria,
                                "imagen": extraer_imagen(noticia),
                                "tipo": "destacada_secundaria"
                            })
                        })
                        urls_procesadas.add(noticia_url)
                        print(f"[Senado Noticias_CL] Destacada secundaria: {titulo[:60]}...")
                except Exception as e:
                    print(f"[Senado Noticias_CL] Error en noticia secundaria: {str(e)}")
            
            # ========================================
            # PARTE 3: Lista "Todas las noticias"
            # ========================================
            print("[Senado Noticias_CL] Procesando lista de todas las noticias...")
            
            noticias_lista = soup.select('div.col-lg-10 > a.card')
            
            for noticia in noticias_lista:
                try:
                    if not noticia.find('div', class_='row'):
                        continue
                    
                    href = noticia.get('href', '')
                    noticia_url = f"https://www.senado.cl{href}" if href else None
                    
                    if not noticia_url or noticia_url in urls_procesadas:
                        continue
                    
                    titulo_el = noticia.find('h3', class_='subtitle')
                    titulo = titulo_el.text.strip() if titulo_el else None
                    
                    fecha_el = noticia.find('p', class_='color-blue-75')
                    fecha = parse_fecha(fecha_el.text if fecha_el else None)
                    
                    cat_el = noticia.find('p', class_='color-blue-100')
                    categoria = cat_el.text.strip() if cat_el else "General"
                    
                    if titulo:
                        items.append({
                            "title": titulo,
                            "description": f"[{categoria}] {titulo}",
                            "source_url": noticia_url,
                            "source_type": "Legislativo",
                            "country": "Chile",
                            "presentation_date": fecha,
                            "category": "Noticias",
                            "institution": "Senado Chile",
                            "metadata": json.dumps({
                                "categoria": categoria,
                                "imagen": extraer_imagen(noticia),
                                "tipo": "lista_general"
                            })
                        })
                        urls_procesadas.add(noticia_url)
                        print(f"[Senado Noticias_CL] Lista general: {titulo[:60]}...")
                except Exception as e:
                    print(f"[Senado Noticias_CL] Error procesando noticia de lista: {str(e)}")
            
            print(f"[Senado Noticias_CL] Se encontraron {len(items)} noticias en total")
            return items
            
        except Exception as e:
            print(f"[Senado Noticias_CL] Error: {str(e)}")
            return []


if __name__ == "__main__":
    items = asyncio.run(scrape_senado_noticias_cl())
    print("\n" + "="*60)
    print("RESULTADO JSON:")
    print("="*60)
    print(json.dumps(items, indent=4, default=str, ensure_ascii=False))