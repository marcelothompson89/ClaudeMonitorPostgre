from playwright.async_api import async_playwright
import asyncio
import json
from datetime import datetime
import re


async def scrape_apexbrasil_eventos_br():
    """
    Scraper para extraer eventos de ApexBrasil
    (Agência Brasileira de Promoção de Exportações e Investimentos)
    de https://apexbrasil.com.br/content/apexbrasil/br/pt/eventos.html usando Playwright.
    """
    url = "https://apexbrasil.com.br/content/apexbrasil/br/pt/eventos.html"
    items = []

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Usar 'domcontentloaded' en lugar de 'networkidle' para evitar timeouts
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)

            # Esperar a que aparezca la lista de eventos
            print("Esperando a que cargue la lista de eventos...")
            await page.wait_for_selector(".cmp-eventsearch__list li.cmp-EventSearchsolution__card", timeout=45000)

            # Esperar un poco más para asegurar que todo el contenido se haya cargado
            await asyncio.sleep(2)

            # Obtener todos los eventos
            event_cards = await page.query_selector_all(".cmp-eventsearch__list li.cmp-EventSearchsolution__card")
            print(f"Se encontraron {len(event_cards)} eventos.")

            if not event_cards:
                print("No se encontraron eventos en la página.")
                return []

            for idx, card in enumerate(event_cards):
                try:
                    # Extraer el link del evento
                    link_element = await card.query_selector("a.cmp-solution__card")
                    event_url = await link_element.get_attribute("href") if link_element else url
                    # Construir URL completa si es relativa
                    if event_url.startswith("/"):
                        event_url = f"https://apexbrasil.com.br{event_url}"

                    # Extraer título
                    title_element = await card.query_selector("h4.cmp-solution__card-title")
                    title = await title_element.inner_text() if title_element else "Sin título"
                    title = title.strip()

                    # Extraer categoría/tipo de evento
                    category_element = await card.query_selector(".cmp-eventsearch__card-tag--transparent")
                    event_category = await category_element.inner_text() if category_element else "Evento"
                    event_category = event_category.strip()

                    # Extraer descripción
                    description_element = await card.query_selector(".cmp-solution__card-description")
                    description_text = await description_element.inner_text() if description_element else ""
                    description_text = description_text.strip()

                    # Extraer estado del evento (Inscrições Abertas, Encerradas, etc.)
                    status_element = await card.query_selector(".cmp-eventsearch__card-tag--border")
                    event_status = await status_element.inner_text() if status_element else ""
                    event_status = event_status.strip()

                    # Extraer fechas
                    date_items = await card.query_selector_all(".cmp-eventsearch__card-dateitem span")
                    registration_period = ""
                    event_date = ""

                    for date_item in date_items:
                        date_text = await date_item.inner_text()
                        date_text = date_text.strip()

                        if "Período de inscrição:" in date_text:
                            registration_period = date_text.replace("Período de inscrição:", "").strip()
                        elif "Data do evento:" in date_text:
                            event_date = date_text.replace("Data do evento:", "").strip()

                    print(f"Procesando evento {idx + 1}: {title}")

                    # Parsear fecha del evento para obtener presentation_date
                    presentation_date = None
                    if event_date:
                        # Formato: "dd/mm/yy a dd/mm/yy" o "dd/mm/yy"
                        # Extraer la primera fecha
                        date_match = re.search(r'(\d{2})/(\d{2})/(\d{2})', event_date)
                        if date_match:
                            try:
                                day = int(date_match.group(1))
                                month = int(date_match.group(2))
                                year = int(date_match.group(3))

                                # Convertir año de 2 dígitos a 4 dígitos
                                # Asumimos que años 00-49 son 2000-2049, y 50-99 son 1950-1999
                                if year < 50:
                                    year = 2000 + year
                                else:
                                    year = 1900 + year

                                presentation_date = datetime(year, month, day).date()
                            except ValueError as e:
                                print(f"Error al construir fecha: {e}")
                                presentation_date = None

                    # Construir descripción completa
                    description_parts = []
                    if event_category:
                        description_parts.append(f"Tipo: {event_category}")
                    if event_status:
                        description_parts.append(f"Estado: {event_status}")
                    if registration_period:
                        description_parts.append(f"Período de inscripción: {registration_period}")
                    if event_date:
                        description_parts.append(f"Fecha del evento: {event_date}")
                    if description_text:
                        # Limitar la descripción a 300 caracteres
                        if len(description_text) > 300:
                            description_text = description_text[:297] + "..."
                        description_parts.append(f"Descripción: {description_text}")

                    description = " | ".join(description_parts) if description_parts else "Evento ApexBrasil"

                    # Crear objeto en el formato esperado
                    item = {
                        'title': title,
                        'description': description,
                        'source_url': event_url,
                        'source_type': "Institucional",
                        'category': "Eventos",
                        'country': "Brasil",
                        'institution': "ApexBrasil",
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
    items = asyncio.run(scrape_apexbrasil_eventos_br())

    # Formatear salida como JSON para visualizar los datos
    print(json.dumps(items, indent=4, default=str, ensure_ascii=False))
