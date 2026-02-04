from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, date


async def scrape_onu_noticias():
    """
    Scraper para la sección de noticias de la ONU utilizando Playwright.
    """
    base_url = "https://news.un.org"
    url = "https://news.un.org/es/news"
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
            await page.wait_for_selector("div.row", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todos los artículos (contenedores div.row que tienen h2.node__title)
            articulos = soup.find_all("div", class_="row")

            for articulo in articulos:
                try:
                    # Verificar que es un artículo de noticias (tiene título)
                    titulo_tag = articulo.find("h2", class_="node__title")
                    if not titulo_tag:
                        continue

                    # A) Extraer título y enlace
                    enlace_tag = titulo_tag.find("a")
                    title_span = enlace_tag.find("span") if enlace_tag else None
                    title = title_span.get_text(strip=True) if title_span else "Sin título"
                    enlace_relativo = enlace_tag["href"] if enlace_tag else None
                    source_url = f"{base_url}{enlace_relativo}" if enlace_relativo else None

                    # B) Extraer descripción desde field--name-field-news-story-lead
                    descripcion_tag = articulo.find("div", class_="field--name-field-news-story-lead")
                    if descripcion_tag:
                        descripcion_p = descripcion_tag.find("p")
                        description = descripcion_p.get_text(strip=True) if descripcion_p else title
                    else:
                        description = title

                    # C) Extraer fecha desde el elemento time
                    fecha_tag = articulo.find("time")
                    fecha_texto = fecha_tag.get_text(strip=True) if fecha_tag else None
                    presentation_date = _parse_date_onu(fecha_texto)

                    # Si no se encuentra una fecha válida, usar la fecha actual
                    if not presentation_date:
                        presentation_date = date.today()

                    # Crear objeto en el formato esperado
                    item = {
                        'title': title,
                        'description': description,
                        'source_url': source_url,
                        'source_type': "Organismo Internacional",
                        'category': "Noticias",
                        'country': "Global",
                        'institution': "Naciones Unidas",
                        'presentation_date': presentation_date,
                    }

                    items.append(item)
                except Exception as e:
                    print(f"Error procesando artículo: {e}")

        except Exception as e:
            print(f"Error en la navegación: {e}")

        finally:
            await browser.close()

    return items


def _parse_date_onu(date_str):
    """
    Parsear una fecha en formato "4 Febrero 2026" o similar.
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
        # Limpiar la fecha y convertir a minúsculas
        date_str = date_str.lower().strip()
        partes = date_str.split()
        
        if len(partes) >= 3:
            dia = int(partes[0])
            mes = meses.get(partes[1], None)
            anio = int(partes[2])
            
            if mes:
                return date(anio, mes, dia)
    except (ValueError, IndexError):
        pass
    
    return None


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_onu_noticias())

    # Imprimir resultados
    print(f"\nTotal de noticias encontradas: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)