from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, date


async def scrape_gscf_noticias():
    """
    Scraper para la sección de noticias de Global Self-Care Federation utilizando Playwright.
    """
    base_url = "https://www.selfcarefederation.org"
    url = "https://www.selfcarefederation.org/news"
    items = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": base_url
            }
        )
        page = await context.new_page()

        try:
            print(f"Navegando a: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # Esperar que se carguen los artículos
            await page.wait_for_selector("article.node--type-article", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todos los artículos
            articulos = soup.find_all("article", class_="node--type-article")

            for articulo in articulos:
                try:
                    # A) Extraer enlace desde el atributo about del article
                    enlace_relativo = articulo.get("about", None)
                    source_url = f"{base_url}{enlace_relativo}" if enlace_relativo else None

                    # B) Extraer título desde h3 > span
                    titulo_tag = articulo.find("h3")
                    title_span = titulo_tag.find("span") if titulo_tag else None
                    title = title_span.get_text(strip=True) if title_span else "Sin título"

                    # C) Extraer descripción desde field--name-body
                    descripcion_tag = articulo.find("div", class_="field--name-body")
                    if descripcion_tag:
                        descripcion_p = descripcion_tag.find("p")
                        description = descripcion_p.get_text(strip=True) if descripcion_p else title
                    else:
                        description = title

                    # D) Extraer fecha desde p.date
                    fecha_tag = articulo.find("p", class_="date")
                    fecha_texto = fecha_tag.get_text(strip=True) if fecha_tag else None
                    presentation_date = _parse_date_gscf(fecha_texto)

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
                        'institution': "Global Self-Care Federation",
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


def _parse_date_gscf(date_str):
    """
    Parsear una fecha en formato "03 Feb 2026" o similar.
    """
    if not date_str:
        return None
    
    # Diccionario de meses abreviados en inglés
    meses = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
        'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    try:
        # Limpiar la fecha y convertir a minúsculas
        date_str = date_str.lower().strip()
        partes = date_str.split()
        
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
    items = asyncio.run(scrape_gscf_noticias())

    # Imprimir resultados
    print(f"\nTotal de noticias encontradas: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)