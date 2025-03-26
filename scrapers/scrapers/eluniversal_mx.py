from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, date


async def scrape_el_universal_salud_mx():
    """
    Scraper para la sección de salud de El Universal utilizando Playwright.
    """
    base_url = "https://www.eluniversal.com.mx"
    url = "https://www.eluniversal.com.mx/tag/salud/"
    items = []

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)  # Cambiar a False para ver el navegador
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9",
                "Referer": base_url
            }
        )
        page = await context.new_page()

        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_selector(".paginated-list .story-item", timeout=60000)

            # Extraer el contenido HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar artículos dentro del contenedor principal
            contenedor = soup.find("div", class_="paginated-list")
            articulos = contenedor.find_all("article", class_="story-item") if contenedor else []

            for articulo in articulos:
                try:
                    # A) Extraer título y enlace
                    titulo_tag = articulo.find("h2", class_="story-item__title").find("a")
                    title = titulo_tag.get_text(strip=True) if titulo_tag else "SIN TÍTULO"
                    enlace_relativo = titulo_tag["href"] if titulo_tag else None
                    source_url = f"{base_url}{enlace_relativo}" if enlace_relativo else None

                    # B) Extraer fecha
                    fecha_tag = articulo.find("span", class_="story-item__time-cont")
                    fecha_texto = fecha_tag.get_text(strip=True) if fecha_tag else None
                    presentation_date = _parse_date(fecha_texto)

                    # C) Extraer descripción
                    descripcion_tag = articulo.find("p", class_="story-item__description")
                    description = descripcion_tag.get_text(strip=True) if descripcion_tag else ""

                    # Crear objeto en el formato esperado
                    item = {
                        'title': title,
                        'description': description,
                        'source_url': source_url,
                        'source_type': "Periódico",
                        'category': "Noticias",
                        'country': "México",
                        'institution': "El Universal México",
                        'presentation_date': presentation_date,
                    }

                    items.append(item)
                except:
                    continue  # Ignorar errores individuales en artículos

        finally:
            await browser.close()

    return items


def _parse_date(date_str):
    """
    Parsear una fecha como "06/01/2025" o similar a un objeto datetime.date.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except ValueError:
        return None


# if __name__ == "__main__":
#     # Ejecutar el scraper de forma asíncrona
#     items = asyncio.run(scrape_el_universal_salud())

#     # Imprimir resultados
#     for item in items:
#         print(item)
