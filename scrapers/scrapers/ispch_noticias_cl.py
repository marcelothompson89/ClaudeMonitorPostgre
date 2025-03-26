import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_ispch_noticias_cl():
    print("[ISPCH Noticias_CL] Iniciando scraping...")
    url = "https://www.ispch.gob.cl/noticia/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print(f"[ISPCH Noticias_CL] Accediendo a URL: {url}")
            await page.goto(url, timeout=60000)  # Esperar hasta 60s si la página tarda en cargar

            # Esperar a que carguen los enlaces de noticias
            await page.wait_for_selector("a.link-search", timeout=10000)

            # Obtener el HTML y procesarlo con BeautifulSoup
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Encontrar todas las noticias
            # El error estaba aquí - se buscaba por una clase vacía que no coincide
            # Cambiado para buscar directamente los contenedores que tienen los links de noticias
            noticias = soup.select('div:has(a.link-search)')

            if not noticias:
                print("[ISPCH Noticias_CL] ⚠️ No se encontraron noticias. Verifica los selectores.")
                return []

            items = []
            
            for noticia in noticias:
                try:
                    # Extraer enlace y título
                    link = noticia.find('a', class_='link-search')
                    if not link:
                        continue
                    
                    title_tag = link.find('h4')
                    if not title_tag:
                        continue
                    
                    title = title_tag.text.strip()
                    noticia_url = link['href']
                    noticia_url = noticia_url if noticia_url.startswith("http") else f"https://www.ispch.gob.cl{noticia_url}"
                    
                    # Extraer fecha
                    fecha_element = noticia.find('time')
                    fecha = _parse_date(fecha_element.text.strip()) if fecha_element else datetime.now().date()
                    
                    # Extraer descripción
                    description_tag = link.find('p')
                    description = description_tag.text.strip() if description_tag else title
                    
                    # Crear el objeto de la noticia
                    item = {
                        "title": title,
                        "description": description,
                        "source_url": noticia_url,
                        "source_type": "Ejecutivo",
                        "country": "Chile",
                        "presentation_date": fecha,
                        "category": "Noticias",
                        "institution": "ISPCH Chile",
                        "metadata": json.dumps({"tipo": "Noticia ISPCH"})
                    }
                    
                    items.append(item)
                    print(f"[ISPCH Noticias_CL] ✅ Noticia procesada: {title[:100]}")
                    
                except Exception as e:
                    print(f"[ISPCH Noticias_CL] ⚠️ Error procesando noticia: {str(e)}")
                    continue
            
            print(f"[ISPCH Noticias_CL] 🎯 Se encontraron {len(items)} noticias")
            return items

        except Exception as e:
            print(f"[ISPCH Noticias_CL] ❌ Error: {str(e)}")
            return []
        finally:
            await browser.close()


def _parse_date(fecha_str):
    """
    Convierte fechas en español como "10 febrero, 2025" a formato datetime.
    Si falla, usa la fecha actual.
    """
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    try:
        dia, mes, anio = fecha_str.replace(',', '').split()
        mes_num = meses[mes.lower()]
        return datetime(int(anio), mes_num, int(dia)).date()
    except Exception as e:
        print(f"[ISPCH Noticias_CL] ⚠️ Error procesando fecha '{fecha_str}', se usará la fecha actual: {e}")
        return datetime.now().date()


# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados en JSON
#     noticias = asyncio.run(scrape_ispch_noticias_cl())
#     print(json.dumps([{
#         **noticia,
#         'presentation_date': noticia['presentation_date'].strftime('%Y-%m-%d') if noticia['presentation_date'] else None
#     } for noticia in noticias], indent=4, ensure_ascii=False))