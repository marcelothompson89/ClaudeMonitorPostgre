from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
import json
from datetime import datetime
import re


async def scrape_congreso_normas_br():
    """
    Scraper para extraer normas legales de la primera página de https://normas.leg.br/busca
    usando Playwright.
    """
    url = "https://normas.leg.br/busca?q=&anoInicial=1889&anoFinal=2025&pagina=0&pageSize=10"
    items = []

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)

        # Esperar a que la página cargue completamente
        await page.wait_for_load_state("networkidle")

        # Verificar si la tabla realmente existe
        table_exists = await page.query_selector("tbody.mdc-data-table__content tr")
        if not table_exists:
            print("No se encontraron datos en la tabla.")
            html_content = await page.content()
            print("Contenido de la página para depuración:", html_content[:1000])  # Imprimir parte del HTML
            return []

        # Extraer el contenido HTML de la página
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Seleccionar filas de la tabla
        rows = soup.select("tbody.mdc-data-table__content tr")
        if not rows:
            print("No se encontraron filas en esta página.")
            return []

        for row in rows:
            try:
                # Extraer título (norma)
                title_tag = row.select_one("td.mat-column-nome a.norma-nome")
                title = title_tag.get_text(strip=True) if title_tag else "Sin título"

                # Extraer descripción (ementa)
                description_tag = row.select_one("td.mat-column-ementa div.ementa")
                description = description_tag.get_text(strip=True) if description_tag else "Sin descripción"

                # Extraer la columna de origen de la norma
                origin_tag = row.select_one("td.mat-column-ementa div.nombre-processo")
                origin = origin_tag.get_text(strip=True) if origin_tag else "Sin origen"

                # Extraer fecha desde el título usando una expresión regular
                date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', title)
                presentation_date = datetime.strptime(date_match.group(1), "%d/%m/%Y").date() if date_match else None

                # Determinar el tipo de norma y construir la URL
                if presentation_date:
                    year = presentation_date.strftime("%Y")
                    formatted_date = presentation_date.strftime("%Y-%m-%d")

                    # Determinar tipo de norma desde el título
                    if "Lei Complementar" in title:
                        norma_type = "lei.complementar"
                    elif "Medida Provisória" in title:
                        norma_type = "medida.provisoria"
                    else:
                        norma_type = "lei"

                    # Extraer número completo de la norma (permitir números con punto)
                    number_match = re.search(r"[nN][ºo]?\s*([\d\.]+)", title)
                    norma_number = number_match.group(1).replace(".", "") if number_match else "sin-numero"

                    # Construir URL con el número completo
                    source_url = f"https://normas.leg.br/?urn=urn:lex:br:federal:{norma_type}:{formatted_date};{norma_number}"
                else:
                    source_url = url

                # Crear objeto en el formato esperado
                item = {
                    'title': title,
                    'description': f"{description}\nOrigen: {origin}",
                    'source_url': source_url,
                    'source_type': "Congreso Brasil",
                    'category': "Normas",
                    'country': "Brasil",
                    'institution': "Congreso Brasil",
                    'presentation_date': presentation_date  # Mantener como datetime.date
                }
                items.append(item)
            except Exception as e:
                print(f"Error procesando fila: {e}")

        await browser.close()

    return items


# if __name__ == "__main__":
#     # Ejecutar el scraper de forma asíncrona
#     items = asyncio.run(scrape_congreso_normas_br())

#     # Formatear salida como JSON para visualizar los datos
#     print(json.dumps(items, indent=4, default=str, ensure_ascii=False))
