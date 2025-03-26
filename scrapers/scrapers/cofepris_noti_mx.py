from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
import json
from datetime import datetime


async def scrape_cofepris_noti_mx():
    """
    Scraper para la página del archivo de artículos de COFEPRIS.
    """
    base_url = "https://www.gob.mx"
    url = "https://www.gob.mx/cofepris/archivo/articulos?idiom=es&&filter_origin=archive"
    items = []

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)

        # Esperar a que los artículos se carguen
        await page.wait_for_selector("div#prensa article")

        # Extraer el contenido HTML renderizado
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Buscar artículos dentro del contenedor principal
        contenedor = soup.find("div", id="prensa")
        articulos = contenedor.find_all("article") if contenedor else []

        for articulo in articulos:
            try:
                # A) Extraer título y enlace
                titulo_tag = articulo.find("h2")
                title = titulo_tag.get_text(strip=True) if titulo_tag else "Sin título"
                enlace_tag = articulo.find("a", class_="small-link")
                enlace_relativo = enlace_tag["href"] if enlace_tag else None
                source_url = f"{base_url}{enlace_relativo}" if enlace_relativo else None

                # B) Extraer fecha
                fecha_tag = articulo.find("time")
                fecha_texto = fecha_tag["date"] if fecha_tag else None

                # Parsear la fecha para incluir tiempo si está presente
                if fecha_texto:
                    try:
                        # Intentar parsear con fecha y hora
                        presentation_date = datetime.strptime(fecha_texto, "%Y-%m-%d %H:%M:%S").date()
                    except ValueError:
                        # Parsear solo la fecha si no incluye hora
                        presentation_date = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
                else:
                    presentation_date = None

                # # C) Extraer descripción
                # img_tag = articulo.find("img")
                # imagen_url = img_tag["src"] if img_tag else None
                # description = f"{title}\nImagen: {imagen_url}"

                # Crear objeto en el formato esperado
                item = {
                    'title': title,
                    'description': title,
                    'source_url': source_url,
                    'source_type': "Ejecutivo",
                    'category': "Noticias",
                    'country': "México",
                    'institution': "COFEPRIS México",
                    'presentation_date': presentation_date,
                }

                items.append(item)
            except Exception as e:
                print(f"Error procesando artículo: {e}")

        await browser.close()

    return items


# if __name__ == "__main__":
#     # Ejecutar el scraper de forma asíncrona
#     items = asyncio.run(scrape_cofepris_mx())

#     # Formatear salida como JSON para visualizar los datos
#     print(json.dumps(items, indent=4, default=str, ensure_ascii=False))
