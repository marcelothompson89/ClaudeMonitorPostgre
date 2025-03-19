import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json


async def scrape_parlatino_reg():
    """
    Scraper para el sitio de noticias de Parlatino utilizando Playwright.
    """
    base_url = "https://parlatino.org/noticias/"
    items = []  # Lista para almacenar los resultados
    registros_sin_fecha = 0
    fecha_actual = datetime.now().date()  # Fecha del día actual

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Inicializar el navegador en modo headless
        page = await browser.new_page()

        try:
            await page.goto(base_url)
            # Esperar a que las noticias estén cargadas en la página
            await page.wait_for_selector(".wpnaw-news-grid-content", timeout=10000)

            # Obtener el contenido HTML de la página
            html_content = await page.content()
            soup = BeautifulSoup(html_content, "html.parser")

            # Buscar noticias dentro del contenedor
            noticias = soup.select("div.wpnaw-news-grid-content")
            print(f"Noticias encontradas: {len(noticias)}")

            for noticia in noticias:
                try:
                    # A) Imagen y URL relativo
                    img_tag = noticia.select_one("div.wpnaw-news-image-bg img")
                    imagen_url = img_tag["src"] if img_tag else None

                    # B) Fecha (buscada dentro del contenido corto)
                    short_content = noticia.select_one("div.wpnaw-news-short-content")
                    short_text = short_content.text.strip() if short_content else ""
                    fecha_hora = _parse_date_from_text(short_text)

                    # Si no hay fecha, asignar la fecha del día actual
                    if not fecha_hora:
                        registros_sin_fecha += 1
                        fecha_hora = fecha_actual

                    # C) Título y enlace
                    titulo_tag = noticia.select_one("h2.wpnaw-news-title a")
                    titulo_texto = titulo_tag.get_text(strip=True) if titulo_tag else "SIN TÍTULO"
                    enlace_url = titulo_tag["href"] if titulo_tag else None

                    # Crear el diccionario del item
                    item = {
                        "title": titulo_texto,
                        "description": f"{short_text}\nImagen: {imagen_url}" if imagen_url else short_text,
                        "source_type": "Parlatino",
                        "category": "Noticias",
                        "country": "Regional",
                        "source_url": enlace_url,
                        "institution": "Parlatino",
                        "presentation_date": fecha_hora,
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando noticia: {e}")

        except Exception as e:
            print(f"Error al procesar la página: {e}")

        finally:
            await browser.close()

    # Imprimir resumen
    print(f"Noticias sin fecha asignadas con fecha actual: {registros_sin_fecha}")
    return items


def _parse_date_from_text(text):
    """
    Intenta extraer una fecha de un texto utilizando expresiones regulares.
    """
    import re
    match = re.search(r"\b\d{1,2}/\d{1,2}/\d{2}\b", text)
    if match:
        try:
            return datetime.strptime(match.group(0), "%d/%m/%y").date()
        except ValueError:
            pass
    return None


# if __name__ == "__main__":
#     # Ejecutar el scraper
#     items = asyncio.run(scrape_parlatino())

#     # Mostrar resultados en formato JSON
#     print(json.dumps([{
#         **item,
#         'presentation_date': item['presentation_date'].strftime('%Y-%m-%d') if item['presentation_date'] else None
#     } for item in items], indent=4, ensure_ascii=False))
