from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
import json
from datetime import datetime

async def scrape_senasica_noti_mx():
    """
    Scraper para la página de archivos de artículos de SENASICA.
    """
    base_url = "https://www.gob.mx"
    url = "https://www.gob.mx/senasica/archivo/articulos?idiom=es&&filter_origin=archive"
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

        # Buscar artículos dentro del contenedor
        contenedor = soup.find("div", id="prensa")
        articulos = contenedor.find_all("article") if contenedor else []

        for articulo in articulos:
            # A) Extraer título
            title_tag = articulo.find("h2")
            title = title_tag.get_text(strip=True) if title_tag else "Sin título"

            # B) Extraer enlace
            enlace_tag = articulo.find("a", class_="small-link")
            enlace_relativo = enlace_tag["href"] if enlace_tag else None
            source_url = f"{base_url}{enlace_relativo}" if enlace_relativo else None

            # C) Extraer imagen y descripción
            img_tag = articulo.find("img")
            image_url = img_tag["src"] if img_tag else None
            alt_text = img_tag.get("alt", "") if img_tag else ""

            # D) Extraer fecha de publicación
            fecha_tag = articulo.find("time")
            fecha_texto = fecha_tag.get("date") if fecha_tag else None
            presentation_date = None
            if fecha_texto:
                try:
                    presentation_date = datetime.strptime(fecha_texto, "%Y-%m-%d %H:%M:%S").date()
                except ValueError:
                    presentation_date = datetime.strptime(fecha_texto, "%Y-%m-%d").date()

            # Crear objeto de salida
            item = {
                "title": title,
                "description": alt_text or title,
                "image_url": image_url,
                "source_url": source_url,
                "source_type": "Ejecutivo",
                "category": "Noticias",
                "country": "México",
                "institution": "SENASICA",
                "presentation_date": presentation_date,
            }
            items.append(item)

        await browser.close()
    return items

if __name__ == "__main__":
    # Ejecutar el scraper y mostrar la salida JSON
    items = asyncio.run(scrape_senasica_noti_mx())
    print(json.dumps(items, indent=4, default=str, ensure_ascii=False))
