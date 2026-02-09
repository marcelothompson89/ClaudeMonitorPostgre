from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import date
import re


async def scrape_fifarma_eventos():
    """
    Scraper para la sección de Eventos de FIFARMA.
    Extrae eventos relacionados con la industria farmacéutica en América Latina.
    """
    base_url = "https://fifarma.org"
    url = "https://fifarma.org/eventos/"
    items = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9",
                "Referer": base_url
            }
        )
        page = await context.new_page()

        try:
            print(f"Navegando a: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # Esperar que se carguen los eventos
            await page.wait_for_selector(".jet-listing-grid__item", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todos los items de eventos
            event_items = soup.find_all("div", class_="jet-listing-grid__item")

            for item in event_items:
                try:
                    # A) Extraer título (h2 o h4 dentro de jet-listing-dynamic-field__content)
                    title = None
                    title_tag = item.find("h2", class_="jet-listing-dynamic-field__content")
                    if not title_tag:
                        title_tag = item.find("h4", class_="jet-listing-dynamic-field__content")
                    
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        # Limpiar prefijo "EVENTO - " si existe
                        if title.startswith("EVENTO - "):
                            title = title[9:]
                    
                    if not title:
                        continue

                    # B) Extraer descripción/resumen (p dentro de jet-listing-dynamic-field__content)
                    description = title  # Por defecto usar el título
                    desc_tag = item.find("p", class_="jet-listing-dynamic-field__content")
                    if desc_tag:
                        description = desc_tag.get_text(strip=True)

                    # C) Extraer URL del evento
                    source_url = None
                    # Buscar en overlay link
                    overlay_link = item.find("a", class_="jet-engine-listing-overlay-link")
                    if overlay_link and overlay_link.get("href"):
                        source_url = overlay_link["href"]
                    else:
                        # Buscar en dynamic link
                        dynamic_link = item.find("a", class_="jet-listing-dynamic-link__link")
                        if dynamic_link and dynamic_link.get("href"):
                            source_url = dynamic_link["href"]
                    
                    if not source_url:
                        continue

                    # D) Extraer fecha
                    presentation_date = None
                    # Buscar div con clase jet-listing-dynamic-field__content que contenga fecha
                    date_divs = item.find_all("div", class_="jet-listing-dynamic-field__content")
                    for date_div in date_divs:
                        date_text = date_div.get_text(strip=True)
                        parsed_date = _parse_date_fifarma(date_text)
                        if parsed_date:
                            presentation_date = parsed_date
                            break
                    
                    # Si no se encontró fecha, usar fecha actual
                    if not presentation_date:
                        presentation_date = date.today()

                    # Crear objeto en el formato esperado
                    event = {
                        'title': title,
                        'description': description,
                        'source_url': source_url,
                        'source_type': "Organismo Internacional",
                        'category': "Eventos",
                        'country': "Regional",
                        'institution': "FIFARMA",
                        'presentation_date': presentation_date,
                    }

                    # Evitar duplicados por URL
                    if not any(e['source_url'] == source_url for e in items):
                        items.append(event)

                except Exception as e:
                    print(f"Error procesando evento: {e}")

        except Exception as e:
            print(f"Error en la navegación: {e}")

        finally:
            await browser.close()

    return items


def _parse_date_fifarma(date_str):
    """
    Parsear una fecha en formato "9 octubre, 2024" o "26 septiembre, 2024".
    """
    if not date_str:
        return None
    
    # Diccionario de meses en español
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    try:
        # Limpiar la fecha (remover coma y espacios extra)
        date_str = date_str.replace(",", "").lower().strip()
        partes = date_str.split()
        
        if len(partes) >= 3:
            dia = int(partes[0])
            mes = meses.get(partes[1], None)
            anio = int(partes[2])
            
            if mes and 1 <= dia <= 31 and 2000 <= anio <= 2100:
                return date(anio, mes, dia)
    except (ValueError, IndexError):
        pass
    
    return None


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_fifarma_eventos())

    # Imprimir resultados
    print(f"\nTotal de eventos encontrados: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)