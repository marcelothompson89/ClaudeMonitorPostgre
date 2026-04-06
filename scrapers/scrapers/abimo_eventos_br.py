from playwright.async_api import async_playwright
import asyncio
import json
from datetime import datetime
import re


async def scrape_abimo_eventos_br():
    """
    Scraper para extraer eventos próximos de ABIMO Brasil
    (Associação Brasileira da Indústria de Dispositivos Médicos)
    de https://abimo.org.br/ usando Playwright.
    """
    url = "https://abimo.org.br/"
    items = []

    # Mapeo de meses en portugués a números
    meses_pt = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
    }

    # Mapeo de tipos de eventos
    tipos_evento = {
        'nacionais': 'Evento Nacional',
        'internacionais': 'Evento Internacional',
        'cursos': 'Curso/Capacitación'
    }

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)

            # Esperar a que aparezca el carrusel de eventos
            print("Esperando a que cargue el carrusel de eventos...")
            await page.wait_for_selector("#carousel .event", timeout=30000)

            # Esperar un poco más para asegurar que todo el contenido se haya cargado
            await asyncio.sleep(2)

            # Obtener todos los eventos del carrusel
            event_cards = await page.query_selector_all("#carousel .event")
            print(f"Se encontraron {len(event_cards)} eventos.")

            if not event_cards:
                print("No se encontraron eventos en la página.")
                return []

            # Obtener el año actual para construir las fechas
            current_year = datetime.now().year
            current_month = datetime.now().month

            for idx, card in enumerate(event_cards):
                try:
                    # Extraer título
                    title_element = await card.query_selector("h4")
                    title = await title_element.inner_text() if title_element else "Sin título"
                    title = title.strip()

                    # Extraer ubicación/modalidad
                    location_element = await card.query_selector("p.hour_event")
                    location = await location_element.inner_text() if location_element else ""
                    location = location.strip()

                    # Extraer día(s)
                    date_element = await card.query_selector("p.date_event")
                    date_text = await date_element.inner_text() if date_element else None
                    date_text = date_text.strip() if date_text else None

                    # Extraer mes
                    month_element = await card.query_selector("p.mounth_event")
                    month_text = await month_element.inner_text() if month_element else None
                    if month_text:
                        # Remover "de " del inicio (ej: "de abril" -> "abril")
                        month_text = month_text.strip().lower().replace('de ', '')

                    # Extraer URL del evento
                    link_element = await card.query_selector(".link_eventos a")
                    event_url = await link_element.get_attribute("href") if link_element else url
                    event_url = event_url.strip()

                    # Determinar tipo de evento por la clase del ícono
                    icon_element = await card.query_selector(".icon_event")
                    event_type = "Evento"
                    if icon_element:
                        icon_class = await icon_element.get_attribute("class")
                        if "cursos" in icon_class:
                            event_type = tipos_evento['cursos']
                        elif "internacionais" in icon_class:
                            event_type = tipos_evento['internacionais']
                        elif "nacionais" in icon_class:
                            event_type = tipos_evento['nacionais']

                    # Determinar si es un curso por la clase del div.event
                    card_class = await card.get_attribute("class")
                    if "curso" in card_class:
                        event_type = tipos_evento['cursos']

                    print(f"Procesando evento {idx + 1}: {title}")

                    # Construir fecha de presentación
                    presentation_date = None
                    if date_text and month_text and month_text in meses_pt:
                        try:
                            month_number = meses_pt[month_text]

                            # Si el mes es menor al mes actual, probablemente es del año siguiente
                            # Excepción: enero puede ser del año siguiente si estamos en diciembre
                            if month_number < current_month and month_number != 1:
                                event_year = current_year + 1
                            elif month_number == 1 and current_month == 12:
                                event_year = current_year + 1
                            else:
                                event_year = current_year

                            # Parsear el día (puede ser un rango como "08 a 10" o un solo día "07")
                            # Tomamos el primer día del rango como fecha de presentación
                            day_match = re.search(r'(\d+)', date_text)
                            if day_match:
                                day = int(day_match.group(1))
                                presentation_date = datetime(event_year, month_number, day).date()
                        except ValueError as e:
                            print(f"Error al construir fecha: {e}")
                            presentation_date = None

                    # Construir descripción con el tipo de evento, ubicación y fechas
                    description_parts = []
                    if event_type:
                        description_parts.append(f"Tipo: {event_type}")
                    if location:
                        description_parts.append(f"Ubicación: {location}")
                    if date_text and month_text:
                        # Mostrar el rango completo si existe
                        if 'a' in date_text:  # Es un rango
                            description_parts.append(f"Fechas: {date_text} de {month_text}")
                        else:
                            description_parts.append(f"Fecha: {date_text} de {month_text}")

                    description = " | ".join(description_parts) if description_parts else "Evento ABIMO"

                    # Crear objeto en el formato esperado
                    item = {
                        'title': title,
                        'description': description,
                        'source_url': event_url,
                        'source_type': "Institucional",
                        'category': "Eventos",
                        'country': "Brasil",
                        'institution': "ABIMO",
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
    items = asyncio.run(scrape_abimo_eventos_br())

    # Formatear salida como JSON para visualizar los datos
    print(json.dumps(items, indent=4, default=str, ensure_ascii=False))
