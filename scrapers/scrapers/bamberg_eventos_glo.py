from playwright.async_api import async_playwright
import asyncio
import json
from datetime import datetime
import re


async def scrape_bamberg_eventos_glo():
    """
    Scraper para extraer eventos de Bamberg Health
    de https://bamberghealth.com/?lang=es_es usando Playwright.
    """
    url = "https://bamberghealth.com/?lang=es_es"
    items = []

    # Mapeo de meses en español a números
    meses_es = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)

            # Esperar a que aparezcan los eventos
            print("Esperando a que cargue la lista de eventos...")
            # El selector puede variar, buscaremos contenedores de eventos
            await page.wait_for_selector(".bubble-element.CustomElement", timeout=45000)

            # Esperar un poco más para asegurar que todo el contenido se haya cargado
            await asyncio.sleep(3)

            # Hacer scroll para cargar contenido lazy-loaded
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            # Obtener todos los contenedores de eventos
            # Buscaremos los elementos que tienen el título y la información del evento
            event_containers = await page.query_selector_all(".bubble-element.CustomElement")
            print(f"Se encontraron {len(event_containers)} contenedores potenciales.")

            for idx, container in enumerate(event_containers):
                try:
                    # Verificar si este contenedor tiene un título de evento
                    title_element = await container.query_selector("h2.bubble-element.Text")
                    if not title_element:
                        continue

                    title = await title_element.inner_text()
                    title = title.strip()

                    # Si el título está vacío o es muy corto, no es un evento válido
                    if not title or len(title) < 10:
                        continue

                    print(f"Procesando evento {idx + 1}: {title}")

                    # Extraer ubicación
                    location_element = await container.query_selector(".bubble-element.Text.baTaTtn")
                    location = ""
                    if location_element:
                        location = await location_element.inner_text()
                        location = location.strip()

                    # Extraer tipo de evento (In-person, Virtual, etc.)
                    event_type_element = await container.query_selector("h2.bubble-element.Text.baTaTth")
                    event_type = ""
                    if event_type_element:
                        event_type = await event_type_element.inner_text()
                        event_type = event_type.strip()

                    # Extraer enlace del evento
                    link_element = await container.query_selector("a.bubble-element.Link")
                    event_url = url
                    if link_element:
                        event_url = await link_element.get_attribute("href")
                        if event_url and not event_url.startswith("http"):
                            event_url = f"https://bamberghealth.com{event_url}"

                    # Extraer fecha
                    date_element = await container.query_selector(".bubble-element.Text.baTaTut")
                    date_text = ""
                    presentation_date = None
                    if date_element:
                        date_text = await date_element.inner_text()
                        date_text = date_text.strip()

                        # Formato: "abril 14, 2026 | 8:00 am (local time)"
                        # Parsear la fecha
                        date_match = re.search(r'(\w+)\s+(\d+),\s+(\d{4})', date_text)
                        if date_match:
                            try:
                                month_name = date_match.group(1).lower()
                                day = int(date_match.group(2))
                                year = int(date_match.group(3))

                                if month_name in meses_es:
                                    month = meses_es[month_name]
                                    presentation_date = datetime(year, month, day).date()
                            except ValueError as e:
                                print(f"Error al construir fecha: {e}")

                    # Extraer descripción truncada
                    description_element = await container.query_selector("h3.bubble-element.Text")
                    description_text = ""
                    if description_element:
                        description_text = await description_element.inner_text()
                        description_text = description_text.strip()

                    # Construir descripción completa
                    description_parts = []
                    if event_type:
                        description_parts.append(f"Tipo: {event_type}")
                    if location:
                        description_parts.append(f"Ubicación: {location}")
                    if date_text:
                        description_parts.append(f"Fecha: {date_text}")
                    if description_text:
                        description_parts.append(f"Temática: {description_text}")

                    description = " | ".join(description_parts) if description_parts else "Evento Bamberg Health"

                    # Filtrar elementos que no son eventos reales
                    # Los eventos reales deben tener fecha Y un enlace específico (no la URL principal)
                    if not presentation_date:
                        print(f"  -> Descartado: sin fecha válida")
                        continue

                    if event_url == url or "/event/" not in event_url:
                        print(f"  -> Descartado: URL no es de un evento específico")
                        continue

                    # Determinar el país según la ubicación
                    country = "Global"
                    if location:
                        if "Canada" in location or "Vancouver" in location or "Toronto" in location:
                            country = "Canadá"
                        elif "USA" in location or "United States" in location:
                            country = "Estados Unidos"
                        elif "UK" in location or "London" in location:
                            country = "Reino Unido"
                        elif "Spain" in location or "España" in location:
                            country = "España"
                        elif "Chile" in location or "Santiago" in location:
                            country = "Chile"
                        elif "Mexico" in location:
                            country = "México"
                        elif "Portugal" in location or "Lisbon" in location:
                            country = "Portugal"
                        # Agregar más países según sea necesario

                    # Crear objeto en el formato esperado
                    item = {
                        'title': title,
                        'description': description,
                        'source_url': event_url,
                        'source_type': "Eventos",
                        'category': "Eventos",
                        'country': country,
                        'institution': "Bamberg Health",
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
    items = asyncio.run(scrape_bamberg_eventos_glo())

    # Formatear salida como JSON para visualizar los datos
    print(json.dumps(items, indent=4, default=str, ensure_ascii=False))
