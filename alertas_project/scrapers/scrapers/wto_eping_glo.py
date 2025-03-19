import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, date
import json

async def scrape_eping_glo():
    today_date = datetime.now().strftime("%Y-%m-%d")
    base_url = f"https://epingalert.org/en/Search/?distributionDateFrom={today_date}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(base_url)

        await page.wait_for_selector("table.table tbody tr")  # Esperar a que cargue la tabla

        items = []

        # Extraer todas las filas de la tabla
        rows = await page.query_selector_all("table.table tbody tr")

        for row in rows:
            try:
                # Extraer los datos con query_selector
                notifying_member = await row.query_selector("[data-label='Notifying Member']")
                notifying_member = await notifying_member.text_content() if notifying_member else "Unknown"

                title_element = await row.query_selector("[data-label='Symbol and title '] a")
                title = await title_element.text_content() if title_element else "SIN TÍTULO"
                link = await title_element.get_attribute("href") if title_element else None

                # Extraer la fecha de distribución
                distribution_element = await row.query_selector("[data-label='Distribution/Comments']")
                distribution_text = await distribution_element.inner_text() if distribution_element else ""

                # Limpiar texto y extraer fechas
                distribution_lines = [line.strip() for line in distribution_text.split("\n") if line.strip()]
                distribution_date = distribution_lines[0] if len(distribution_lines) > 0 else None

                # Convertir a datetime.date
                parsed_date = parse_date(distribution_date)

                # Crear estructura JSON
                item = {
                    'title': title.strip(),
                    'description': f"Notifying Member: {notifying_member.strip()}\nDistribution Date: {distribution_date if distribution_date else 'Unknown'}",
                    'source_type': "ePing Notifications",
                    'category': "Noticias",
                    'country': "Global",
                    'source_url': link,
                    'institution': "WTO",
                    'presentation_date': parsed_date,  # Ahora es un objeto datetime.date
                }
                items.append(item)

            except Exception as e:
                print(f"Error procesando fila: {e}")

        await browser.close()
    
    return items

def parse_date(date_str):
    """ Convierte una fecha en formato DD/MM/YYYY a un objeto datetime.date o devuelve None. """
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    except (ValueError, AttributeError):
        return None  # Si el formato es incorrecto o date_str es None, devolvemos None

# if __name__ == "__main__":
#     # Ejecutar el scraping y mostrar los datos extraídos
#     scraped_data = asyncio.run(scrape_eping())

#     print(json.dumps(
#         [{**item, "presentation_date": item["presentation_date"].strftime("%Y-%m-%d") if item["presentation_date"] else None}
#          for item in scraped_data], 
#         indent=4, ensure_ascii=False
#     ))
