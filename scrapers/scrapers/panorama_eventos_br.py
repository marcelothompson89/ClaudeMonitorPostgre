from playwright.async_api import async_playwright
import asyncio
import json
from datetime import datetime
import re


async def scrape_panorama_eventos_br():
    """
    Scraper para extraer eventos de Panorama Farmacêutico
    de https://panoramafarmaceutico.com.br/eventos/lista/ usando Playwright.
    """
    url = "https://panoramafarmaceutico.com.br/eventos/lista/"
    items = []

    # Mapeo de meses en portugués a números
    meses_pt = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
    }

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)

            # Esperar a que aparezca la lista de eventos
            print("Esperando a que cargue la lista de eventos...")
            await page.wait_for_selector(".tribe-events-calendar-list li.tribe-events-calendar-list__event-row", timeout=45000)

            # Esperar un poco más para asegurar que todo el contenido se haya cargado
            await asyncio.sleep(2)

            # Hacer scroll para cargar más eventos si es lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            # Obtener todos los eventos
            event_rows = await page.query_selector_all("li.tribe-events-calendar-list__event-row")
            print(f"Se encontraron {len(event_rows)} eventos.")

            if not event_rows:
                print("No se encontraron eventos en la página.")
                return []

            # Obtener el año actual
            current_year = datetime.now().year

            for idx, row in enumerate(event_rows):
                try:
                    # Extraer título y URL
                    title_link = await row.query_selector(".tribe-events-calendar-list__event-title-link")
                    if not title_link:
                        continue

                    title = await title_link.inner_text()
                    title = title.strip()

                    event_url = await title_link.get_attribute("href")
                    if not event_url:
                        event_url = url

                    print(f"Procesando evento {idx + 1}: {title[:60]}...")

                    # Extraer datetime attribute para la fecha principal
                    datetime_element = await row.query_selector(".tribe-events-calendar-list__event-date-tag-datetime")
                    main_date = None
                    if datetime_element:
                        datetime_attr = await datetime_element.get_attribute("datetime")
                        if datetime_attr:
                            try:
                                main_date = datetime.fromisoformat(datetime_attr).date()
                            except ValueError:
                                pass

                    # Extraer el texto de fechas (puede ser rango)
                    date_text_element = await row.query_selector(".tribe-events-calendar-list__event-datetime")
                    date_text = ""
                    presentation_date = main_date  # Usar la fecha del datetime como backup
                    if date_text_element:
                        date_text = await date_text_element.inner_text()
                        date_text = date_text.strip()

                        # Intentar parsear la primera fecha del texto
                        # Formato: "1 abril" o "1 abril - 7 abril"
                        date_match = re.search(r'(\d+)\s+(\w+)', date_text)
                        if date_match and not presentation_date:
                            try:
                                day = int(date_match.group(1))
                                month_name = date_match.group(2).lower()

                                if month_name in meses_pt:
                                    month = meses_pt[month_name]
                                    # Determinar el año
                                    if month < datetime.now().month:
                                        event_year = current_year + 1
                                    else:
                                        event_year = current_year
                                    presentation_date = datetime(event_year, month, day).date()
                            except ValueError as e:
                                print(f"  Error al parsear fecha del texto: {e}")

                    # Extraer ubicación
                    venue_title_element = await row.query_selector(".tribe-events-calendar-list__event-venue-title")
                    venue_title = ""
                    if venue_title_element:
                        venue_title = await venue_title_element.inner_text()
                        venue_title = venue_title.strip()

                    venue_address_element = await row.query_selector(".tribe-events-calendar-list__event-venue-address")
                    venue_address = ""
                    if venue_address_element:
                        venue_address = await venue_address_element.inner_text()
                        venue_address = venue_address.strip()

                    # Extraer descripción
                    description_element = await row.query_selector(".tribe-events-calendar-list__event-description")
                    description_text = ""
                    if description_element:
                        description_text = await description_element.inner_text()
                        description_text = description_text.strip()

                    # Construir descripción completa
                    description_parts = []
                    if date_text:
                        description_parts.append(f"Fecha: {date_text}")
                    if venue_title:
                        description_parts.append(f"Local: {venue_title}")
                    if venue_address:
                        # Limitar la dirección a 100 caracteres
                        if len(venue_address) > 100:
                            venue_address = venue_address[:97] + "..."
                        description_parts.append(f"Dirección: {venue_address}")
                    if description_text:
                        # Limitar la descripción a 300 caracteres
                        if len(description_text) > 300:
                            description_text = description_text[:297] + "..."
                        description_parts.append(description_text)

                    description = " | ".join(description_parts) if description_parts else "Evento Panorama Farmacêutico"

                    # Determinar el país según la ubicación
                    country = "Brasil"
                    if venue_address:
                        if "Japan" in venue_address or "Tokyo" in venue_address:
                            country = "Japón"
                        elif "United States" in venue_address or "USA" in venue_address or "EUA" in venue_title:
                            country = "Estados Unidos"
                        elif "Spain" in venue_address or "Barcelona" in venue_address:
                            country = "España"
                        elif "France" in venue_address or "Paris" in venue_address:
                            country = "Francia"

                    # Crear objeto en el formato esperado
                    item = {
                        'title': title,
                        'description': description,
                        'source_url': event_url,
                        'source_type': "Portal de Noticias",
                        'category': "Eventos",
                        'country': country,
                        'institution': "Panorama Farmacêutico",
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
    items = asyncio.run(scrape_panorama_eventos_br())

    # Formatear salida como JSON para visualizar los datos
    print(json.dumps(items, indent=4, default=str, ensure_ascii=False))
