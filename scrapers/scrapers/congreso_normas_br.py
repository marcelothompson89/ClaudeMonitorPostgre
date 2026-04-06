from playwright.async_api import async_playwright
import asyncio
import json
from datetime import datetime
import re


async def scrape_congreso_normas_br():
    """
    Scraper para extraer normas legales de la primera página de https://normas.leg.br/busca
    usando Playwright.
    """
    url = "https://normas.leg.br/busca?q=&anoInicial=1889&anoFinal=2026&pagina=0&pageSize=10"
    items = []

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)

            # Esperar explícitamente a que aparezca la tabla con datos (hasta 30 segundos)
            print("Esperando a que cargue la tabla de normas...")
            await page.wait_for_selector("tr.mat-mdc-row", timeout=30000)

            # Esperar un poco más para asegurar que todo el contenido dinámico se haya cargado
            await asyncio.sleep(2)

            # Obtener todas las filas usando Playwright directamente
            rows = await page.query_selector_all("tr.mat-mdc-row")
            print(f"Se encontraron {len(rows)} filas en la tabla.")

            if not rows:
                print("No se encontraron filas en la tabla.")
                return []

            for idx, row in enumerate(rows):
                try:
                    # Extraer título (norma) - columna nome
                    title_element = await row.query_selector("td.mat-column-nome a.norma-nome")
                    title = await title_element.inner_text() if title_element else "Sin título"
                    title = title.strip()

                    # Extraer descripción (ementa) - columna ementa
                    description_element = await row.query_selector("td.mat-column-ementa div.ementa")
                    description = await description_element.inner_text() if description_element else "Sin descripción"
                    description = description.strip()

                    print(f"Procesando norma {idx + 1}: {title}")

                    # Extraer fecha desde el título usando una expresión regular
                    date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', title)
                    presentation_date = datetime.strptime(date_match.group(1), "%d/%m/%Y").date() if date_match else None

                    # Determinar el tipo de norma y construir la URL
                    if presentation_date:
                        formatted_date = presentation_date.strftime("%Y-%m-%d")

                        # Determinar tipo de norma desde el título
                        if "Lei Complementar" in title:
                            norma_type = "lei.complementar"
                        elif "Medida Provisória" in title:
                            norma_type = "medida.provisoria"
                        elif "Decreto" in title:
                            norma_type = "decreto"
                        elif "Resolução" in title:
                            norma_type = "resolucao"
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
                        'description': description,
                        'source_url': source_url,
                        'source_type': "Legislativo",
                        'category': "Normas",
                        'country': "Brasil",
                        'institution': "Congreso Brasil",
                        'presentation_date': presentation_date
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando fila {idx + 1}: {e}")
                    continue

        except Exception as e:
            print(f"Error general en el scraper: {e}")
        finally:
            await browser.close()

    print(f"Scraper completado. Total de items extraídos: {len(items)}")
    return items


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_congreso_normas_br())

    # Formatear salida como JSON para visualizar los datos
    print(json.dumps(items, indent=4, default=str, ensure_ascii=False))
