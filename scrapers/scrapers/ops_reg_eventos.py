from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, date


async def scrape_ops_eventos():
    """
    Scraper para la sección de eventos de la OPS (PAHO) utilizando Playwright.
    """
    base_url = "https://www.paho.org"
    url = "https://www.paho.org/es/eventos"
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

            # Esperar que se carguen los artículos
            await page.wait_for_selector("div.col-1", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todos los eventos
            eventos = soup.find_all("div", class_="col-1")

            for evento in eventos:
                try:
                    # A) Extraer título y enlace
                    titulo_tag = evento.find("h2", class_="event-title")
                    enlace_tag = titulo_tag.find("a") if titulo_tag else None
                    title = enlace_tag.get_text(strip=True) if enlace_tag else "Sin título"
                    enlace_relativo = enlace_tag["href"] if enlace_tag else None
                    source_url = f"{base_url}{enlace_relativo}" if enlace_relativo else None

                    # B) Extraer fecha desde el campo de fecha
                    fecha_tag = evento.find("div", class_="views-field-field-start-date")
                    fecha_content = fecha_tag.find("div", class_="field-content") if fecha_tag else None
                    fecha_texto = fecha_content.get_text(strip=True) if fecha_content else None
                    presentation_date = _parse_date_ops(fecha_texto)

                    # Si no se encuentra una fecha válida, usar la fecha actual
                    if not presentation_date:
                        presentation_date = date.today()

                    # Crear objeto en el formato esperado
                    item = {
                        'title': title,
                        'description': title,
                        'source_url': source_url,
                        'source_type': "Organismo Internacional",
                        'category': "Eventos",
                        'country': "Regional",
                        'institution': "OPS",
                        'presentation_date': presentation_date,
                    }

                    items.append(item)
                except Exception as e:
                    print(f"Error procesando evento: {e}")

        except Exception as e:
            print(f"Error en la navegación: {e}")

        finally:
            await browser.close()

    return items


def _parse_date_ops(date_str):
    """
    Parsear una fecha en formato "19 Feb 2026 - 19 Feb 2026" o similar.
    Toma la primera fecha del rango.
    """
    if not date_str:
        return None
    
    # Diccionario de meses abreviados en inglés/español
    meses = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'ene': 1, 'abr': 4, 'ago': 8, 'dic': 12
    }
    
    try:
        # Tomar solo la primera fecha (antes del guion)
        primera_fecha = date_str.split("-")[0].strip()
        partes = primera_fecha.lower().split()
        
        if len(partes) >= 3:
            dia = int(partes[0])
            mes = meses.get(partes[1][:3], None)
            anio = int(partes[2])
            
            if mes:
                return date(anio, mes, dia)
    except (ValueError, IndexError):
        pass
    
    return None


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_ops_eventos())

    # Imprimir resultados
    print(f"\nTotal de eventos encontrados: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)