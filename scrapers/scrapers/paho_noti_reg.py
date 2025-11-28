import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_paho_noti_reg():
    """
    Scraper para la página de noticias de PAHO usando Playwright.
    """
    base_url = "https://www.paho.org"
    url = "https://www.paho.org/en/news/news-releases"
    items = []
    registros_sin_titulo = 0

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Navegar a la URL
            await page.goto(url, wait_until="networkidle")
            
            # Obtener el contenido HTML
            content = await page.content()
            await browser.close()
            
            soup = BeautifulSoup(content, "html.parser")
            noticias = soup.select("div.view-content div.col")
            print(f"Noticias encontradas: {len(noticias)}")

            for noticia in noticias:
                try:
                    # Extraer enlace
                    enlace_tag = noticia.select_one("div.views-field-title a")
                    enlace = enlace_tag.get("href") if enlace_tag else None
                    url_completa = f"{base_url}{enlace}" if enlace else None

                    # Extraer título
                    titulo = enlace_tag.text.strip() if enlace_tag else None

                    # Validar si el título es válido
                    if not titulo or titulo.lower() == "sin título":
                        registros_sin_titulo += 1
                        continue

                    # Extraer fecha
                    fecha_tag = noticia.select_one("div.views-field-created time")
                    fecha_iso = fecha_tag.get("datetime") if fecha_tag else None

                    fecha_hora = None
                    if fecha_iso:
                        try:
                            fecha_hora = datetime.fromisoformat(fecha_iso)
                        except ValueError as e:
                            print(f"Error al procesar fecha: {e}. Texto de fecha: {fecha_iso}")

                    # Extraer descripción
                    descripcion_tag = noticia.select_one("div.views-field-body div.field-content")
                    descripcion = descripcion_tag.text.strip() if descripcion_tag else "No description available"

                    # Crear el diccionario del item
                    item = {
                        'title': titulo,
                        'description': descripcion,
                        'source_type': "PAHO News Releases",
                        'category': "Noticias",
                        'country': "Regional",
                        'source_url': url_completa,
                        'presentation_date': fecha_hora,
                        'metadata': {},
                        'institution': "Pan American Health Organization"
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando noticia: {e}")

        except Exception as e:
            print(f"Error al procesar la página: {e}")

    print(f"Noticias omitidas sin título: {registros_sin_titulo}")
    return items


if __name__ == "__main__":
    # Ejecutar el scraper y mostrar los resultados
    items = asyncio.run(scrape_paho_noti_reg())

    # Formatear salida como JSON
    print(json.dumps([{
        **item,
        'presentation_date': item['presentation_date'].strftime('%Y-%m-%d') if item['presentation_date'] else None
    } for item in items], indent=4, ensure_ascii=False))