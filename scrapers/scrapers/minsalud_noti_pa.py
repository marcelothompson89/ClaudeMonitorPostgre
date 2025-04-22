import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_minsa_noti_pa():
    print("[MINSA Noticias_PA] Iniciando scraping...")
    base_url = "https://www.minsa.gob.pa"
    url = f"{base_url}/noticias-breves"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print(f"[MINSA Noticias_PA] Accediendo a URL: {url}")
            await page.goto(url, timeout=60000)
            
            # Esperar a que cargue el contenido
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.wait_for_selector("div.view-content", timeout=20000)

            # Extraer HTML y analizarlo con BeautifulSoup
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Obtener todas las noticias
            noticias = soup.select("div.view-content div.views-row")
            if not noticias:
                print("[MINSA Noticias_PA] ⚠️ No se encontraron noticias.")
                return []

            items = []

            for noticia in noticias:
                try:
                    # Extraer título y URL
                    link = noticia.select_one("div.minsa-title a")
                    if not link:
                        continue
                    
                    title = link.text.strip()
                    noticia_url = link["href"]
                    noticia_url = f"{base_url}{noticia_url}" if noticia_url.startswith("/") else noticia_url

                    # Extraer fecha
                    fecha_element = noticia.select_one("div.minsa-date")
                    fecha = _parse_date(fecha_element.text.strip()) if fecha_element else datetime.now().date()

                    # Extraer descripción
                    descripcion_element = noticia.select_one("div.minsa-body")
                    descripcion = descripcion_element.text.strip() if descripcion_element else title

                    # Extraer imagen
                    img_element = noticia.select_one("div.minsa-image img")
                    imagen_url = img_element["src"] if img_element else None
                    if imagen_url and not imagen_url.startswith("http"):
                        imagen_url = f"{base_url}{imagen_url}"

                    # Crear objeto de noticia
                    item = {
                        "title": title,
                        "description": descripcion,
                        "source_url": noticia_url,
                        "source_type": "Ejecutivo",
                        "country": "Panamá",
                        "presentation_date": fecha,
                        "category": "Noticias",
                        "institution": "Ministerio de Salud Panamá",
                        "metadata": json.dumps({"imagen": imagen_url})
                    }

                    items.append(item)
                    print(f"[MINSA Noticias_PA] ✅ Noticia procesada: {title[:100]}")

                except Exception as e:
                    print(f"[MINSA Noticias_PA] ⚠️ Error procesando noticia: {str(e)}")
                    continue

            print(f"[MINSA Noticias_PA] 🎯 Se encontraron {len(items)} noticias")
            return items

        except Exception as e:
            print(f"[MINSA Noticias_PA] ❌ Error: {str(e)}")
            return []
        finally:
            await browser.close()


def _parse_date(fecha_str):
    """
    Convierte fechas en español como "18 de Febrero de 2025" a formato datetime.
    Si falla, usa la fecha actual.
    """
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }

    try:
        fecha_str = fecha_str.replace("de", "").strip()
        dia, mes, anio = fecha_str.split()
        mes_num = meses[mes.lower()]
        return datetime(int(anio), mes_num, int(dia)).date()
    except Exception as e:
        print(f"[MINSA Noticias_PA] ⚠️ Error procesando fecha '{fecha_str}', se usará la fecha actual: {e}")
        return datetime.now().date()


if __name__ == "__main__":
    # Ejecutar el scraper y mostrar los resultados en JSON
    noticias = asyncio.run(scrape_minsa_noti_pa())
    print(json.dumps([{
        **noticia,
        'presentation_date': noticia['presentation_date'].strftime('%Y-%m-%d') if noticia['presentation_date'] else None
    } for noticia in noticias], indent=4, ensure_ascii=False))
