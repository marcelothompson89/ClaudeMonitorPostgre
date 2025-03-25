from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime


async def scrape_proceso_mx():
    """
    Scraper para la sección de salud del portal Proceso usando Playwright.
    """
    base_url = "https://www.proceso.com.mx"
    url = "https://www.proceso.com.mx/ciencia-tecnologia/salud/"
    items = []

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)

        # Esperar a que las secciones principales y secundarias se carguen
        await page.wait_for_selector(".region-principal, .region-secundaria")

        # Extraer el contenido HTML renderizado
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Combinar las secciones principales y secundarias
        secciones = soup.select(".region-principal .caja, .region-secundaria .caja")

        for caja in secciones:
            try:
                # Extraer imagen
                img_tag = caja.find("img")
                imagen_url = img_tag["src"] if img_tag else None

                # Extraer título y enlace
                titulo_tag = caja.select_one(".titulo a")
                title = titulo_tag.text.strip() if titulo_tag else "SIN TÍTULO"
                enlace_relativo = titulo_tag["href"] if titulo_tag else None
                source_url = f"{base_url}{enlace_relativo}" if enlace_relativo else None

                # Validar que el título no sea nulo o inválido
                if not title or title == "SIN TÍTULO":
                    continue

                # Extraer descripción
                descripcion_tag = caja.select_one(".bajada p")
                description = descripcion_tag.text.strip() if descripcion_tag else ""

                # Extraer categoría
                categoria_tag = caja.select_one(".marcado")
                category = categoria_tag.text.strip() if categoria_tag else "Salud"

                # Extraer fecha (si estuviera presente en el HTML)
                fecha_tag = caja.find("time")
                fecha_texto = fecha_tag["datetime"] if fecha_tag else None
                presentation_date = (
                    datetime.strptime(fecha_texto, "%Y-%m-%dT%H:%M:%S").date()
                    if fecha_texto
                    else datetime.now().date()
                )

                # Crear objeto en el formato esperado
                item = {
                    'title': title,
                    'description': description,
                    'source_url': source_url,
                    'source_type': "Periódico",
                    'category': "Noticias",
                    'country': "México",
                    'institution': "Periodico El Proceso",
                    'presentation_date': presentation_date,
                }

                items.append(item)
            except Exception as e:
                print(f"Error procesando artículo: {e}")

        await browser.close()

    return items


# if __name__ == "__main__":
#     # Ejecutar el scraper de forma asíncrona
#     items = asyncio.run(scrape_proceso_mx())

#     # Imprimir resultados
#     for item in items:
#         print(item)
