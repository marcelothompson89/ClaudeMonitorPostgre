from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
import json
from datetime import datetime


async def scrape_minsalud_comu_mx():
    """
    Scraper adaptado para la página de programas de la Secretaría de Salud de México.
    """
    base_url = "https://www.gob.mx"
    url = "https://www.gob.mx/salud#392"
    items = []

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)

        # Esperar a que los artículos se carguen
        await page.wait_for_selector(".action_programs_container article")

        # Extraer el contenido HTML renderizado
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Buscar comunicados dentro de los contenedores
        contenedores = soup.find_all("div", class_="action_programs_container")
        articulos = []
        for contenedor in contenedores:
            articulos.extend(contenedor.find_all("article", class_="post"))

        for articulo in articulos:
            try:
                # A) Extraer título y enlace
                titulo_tag = articulo.find("h4").find("a")
                title = titulo_tag.get_text(strip=True) if titulo_tag else "SIN TÍTULO"
                enlace_relativo = titulo_tag["href"] if titulo_tag else None
                source_url = f"{base_url}{enlace_relativo}" if enlace_relativo else None

                # B) Extraer fecha
                fecha_tag = articulo.find("time")
                fecha_texto = fecha_tag["datetime"] if fecha_tag else None

                # Adaptar el parseo de la fecha para incluir tiempo si está presente
                if fecha_texto:
                    try:
                        # Intentar parsear con fecha y hora
                        presentation_date = datetime.strptime(fecha_texto, "%Y-%m-%d %H:%M:%S").date()
                    except ValueError:
                        # Parsear solo la fecha si no incluye hora
                        presentation_date = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
                else:
                    presentation_date = None

                # C) Extraer descripción
                descripcion_tag = articulo.find("p").find_next("p")
                description = descripcion_tag.get_text(strip=True) if descripcion_tag else "Sin descripción"

                # Crear objeto en el formato esperado
                item = {
                    'title': title,
                    'description': description,
                    'source_url': source_url,
                    'source_type': "Ministerio de Salud México",
                    'category': "Comunicados",
                    'country': "México",
                    'institution': "Ministerio de Salud México",
                    'presentation_date': presentation_date,
                }

                items.append(item)
            except Exception as e:
                print(f"Error procesando artículo: {e}")

        await browser.close()

    return items


# if __name__ == "__main__":
#     # Ejecutar el scraper de forma asíncrona
#     items = asyncio.run(scrape_gob_mx_salud_comu())

#     # Formatear salida como JSON para visualizar los datos
#     print(json.dumps(items, indent=4, default=str, ensure_ascii=False))
