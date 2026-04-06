from playwright.async_api import async_playwright
import asyncio
import json
from datetime import datetime
import re


async def scrape_swisscam_eventos_br():
    """
    Scraper para extraer eventos próximos de SwissCam Brasil
    de https://swisscam.com.br/ usando Playwright.
    """
    url = "https://swisscam.com.br/"
    items = []

    # Mapeo de meses en portugués a números
    meses_pt = {
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'maio': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
    }

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)

            # Esperar a que aparezca el contenedor de eventos
            print("Esperando a que cargue la lista de eventos...")
            await page.wait_for_selector(".box-lista-eventos-home a.card-date", timeout=30000)

            # Esperar un poco más para asegurar que todo el contenido se haya cargado
            await asyncio.sleep(2)

            # Obtener todos los eventos
            event_cards = await page.query_selector_all(".box-lista-eventos-home a.card-date")
            print(f"Se encontraron {len(event_cards)} eventos.")

            if not event_cards:
                print("No se encontraron eventos en la página.")
                return []

            # Obtener el año actual para construir las fechas
            current_year = datetime.now().year

            for idx, card in enumerate(event_cards):
                try:
                    # Extraer URL del evento
                    event_url = await card.get_attribute("href")

                    # Extraer día
                    day_element = await card.query_selector(".box-left .group h4")
                    day = await day_element.inner_text() if day_element else None
                    day = day.strip() if day else None

                    # Extraer mes
                    month_element = await card.query_selector(".box-left .group h5")
                    month_text = await month_element.inner_text() if month_element else None
                    month_text = month_text.strip().lower() if month_text else None

                    # Extraer hora
                    time_element = await card.query_selector(".box-left .group legend")
                    time_text = await time_element.inner_text() if time_element else None
                    time_text = time_text.strip() if time_text else None

                    # Extraer categoría/tipo
                    category_element = await card.query_selector(".box-right .group legend")
                    category = await category_element.inner_text() if category_element else "Evento"
                    category = category.strip()

                    # Extraer título
                    title_element = await card.query_selector(".box-right .group h5")
                    title = await title_element.inner_text() if title_element else "Sin título"
                    title = title.strip()

                    print(f"Procesando evento {idx + 1}: {title}")

                    # Construir fecha de presentación
                    presentation_date = None
                    if day and month_text and month_text in meses_pt:
                        try:
                            month_number = meses_pt[month_text]
                            # Si el mes es menor al mes actual, probablemente es del año siguiente
                            if month_number < datetime.now().month:
                                event_year = current_year + 1
                            else:
                                event_year = current_year

                            presentation_date = datetime(event_year, month_number, int(day)).date()
                        except ValueError as e:
                            print(f"Error al construir fecha: {e}")
                            presentation_date = None

                    # Construir descripción con la categoría y hora
                    description_parts = []
                    if category:
                        description_parts.append(f"Tipo: {category}")
                    if time_text:
                        description_parts.append(f"Horario: {time_text}")
                    if presentation_date:
                        description_parts.append(f"Fecha: {presentation_date.strftime('%d/%m/%Y')}")

                    description = " | ".join(description_parts) if description_parts else "Evento SwissCam Brasil"

                    # Crear objeto en el formato esperado
                    item = {
                        'title': title,
                        'description': description,
                        'source_url': event_url,
                        'source_type': "Institucional",
                        'category': "Eventos",
                        'country': "Brasil",
                        'institution': "SwissCam Brasil",
                        'presentation_date': presentation_date
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando evento {idx + 1}: {e}")
                    continue

        except Exception as e:
            print(f"Error general en el scraper: {e}")
        finally:
            await browser.close()

    print(f"Scraper completado. Total de items extraídos: {len(items)}")
    return items


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_swisscam_eventos_br())

    # Formatear salida como JSON para visualizar los datos
    print(json.dumps(items, indent=4, default=str, ensure_ascii=False))
