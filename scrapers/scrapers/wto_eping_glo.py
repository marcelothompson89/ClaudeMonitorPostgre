import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, date
import json

async def scrape_eping_glo(fecha=None):
    today_date = fecha or datetime.now().strftime("%Y-%m-%d")
    base_url = f"https://epingalert.org/en/Search/?distributionDateFrom={today_date}&distributionDateTo={today_date}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(base_url)

        await page.wait_for_selector("table.table tbody tr")  # Esperar a que cargue la tabla

        # Intentar cambiar a 100 resultados por página para minimizar paginación
        try:
            per_page_select = page.locator("select.select").first
            if await per_page_select.count() > 0:
                await per_page_select.select_option("100")
                await page.wait_for_timeout(2000)
                await page.wait_for_selector("table.table tbody tr")
        except Exception:
            pass  # Si no se puede cambiar, continuar con el tamaño por defecto

        items = []
        page_num = 1

        while True:
            print(f"ePing: Extrayendo página {page_num}... ({len(items)} alertas hasta ahora)")

            # Esperar a que desaparezca el texto "Loading.." de la tabla
            try:
                await page.wait_for_function(
                    "() => !document.querySelector('table.table tbody').innerText.includes('Loading')",
                    timeout=10000
                )
            except Exception:
                pass  # Si no desaparece en 10s, continuar con lo que haya

            # Extraer todas las filas de la tabla en la página actual
            rows = await page.query_selector_all("table.table tbody tr")

            for row in rows:
                try:
                    notifying_member = await row.query_selector("[data-label='Notifying Member']")
                    notifying_member = await notifying_member.text_content() if notifying_member else "Unknown"

                    # Símbolo y link desde el primer <a>
                    symbol_element = await row.query_selector("[data-label='Symbol and title '] a")
                    symbol = await symbol_element.text_content() if symbol_element else ""
                    link = await symbol_element.get_attribute("href") if symbol_element else None

                    # Título desde el <span> dentro de search-text-overflow
                    title_span = await row.query_selector("[data-label='Symbol and title '] .search-text-overflow > span")
                    title_text = await title_span.text_content() if title_span else ""

                    title = f"{symbol.strip()} - {title_text.strip()}" if title_text and title_text.strip() else symbol.strip() or "SIN TÍTULO"

                    distribution_element = await row.query_selector("[data-label='Distribution/Comments']")
                    distribution_text = await distribution_element.inner_text() if distribution_element else ""

                    distribution_lines = [line.strip() for line in distribution_text.split("\n") if line.strip()]
                    distribution_date = distribution_lines[0] if len(distribution_lines) > 0 else None

                    parsed_date = parse_date(distribution_date)

                    item = {
                        'title': title.strip(),
                        'description': f"Notifying Member: {notifying_member.strip()}\nDistribution Date: {distribution_date if distribution_date else 'Unknown'}",
                        'source_type': "ePing Notifications",
                        'category': "Noticias",
                        'country': "Global",
                        'source_url': link,
                        'institution': "WTO",
                        'presentation_date': parsed_date,
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando fila: {e}")

            # Verificar si hay botón de página siguiente habilitado
            # Se usa .first porque hay múltiples .pagination-next en la página (tabla + datepickers)
            next_btn = page.locator(".b-table .pagination-next").first
            is_disabled = await next_btn.get_attribute("disabled")
            if is_disabled is None:
                await next_btn.click()
                await page.wait_for_timeout(1500)
                await page.wait_for_selector("table.table tbody tr")
                page_num += 1
            else:
                break  # No hay más páginas

        print(f"ePing: Total de alertas extraídas: {len(items)}")
        await browser.close()

    return items

def parse_date(date_str):
    """ Convierte una fecha en formato DD/MM/YYYY a un objeto datetime.date o devuelve None. """
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    except (ValueError, AttributeError):
        return None  # Si el formato es incorrecto o date_str es None, devolvemos None

if __name__ == "__main__":
    import sys
    # Uso: python wto_eping_glo.py [YYYY-MM-DD]
    # Sin argumento usa la fecha de hoy
    fecha_test = sys.argv[1] if len(sys.argv) > 1 else None
    scraped_data = asyncio.run(scrape_eping_glo(fecha_test))

    print(json.dumps(
        [{**item, "presentation_date": item["presentation_date"].strftime("%Y-%m-%d") if item["presentation_date"] else None}
         for item in scraped_data],
        indent=4, ensure_ascii=False
    ))
