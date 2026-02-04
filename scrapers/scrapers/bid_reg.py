from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, date


async def scrape_bid_noticias():
    """
    Scraper para la sección de noticias del BID utilizando Playwright.
    """
    base_url = "https://www.iadb.org"
    url = "https://www.iadb.org/es/noticias/buscador-de-noticias"
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

            # Esperar que se carguen los artículos (componentes web personalizados)
            await page.wait_for_selector("idb-news-card", timeout=60000)
            
            # Dar tiempo extra para que se renderice el contenido dinámico
            await page.wait_for_timeout(3000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todos los artículos (idb-news-card)
            articulos = soup.find_all("idb-news-card")

            for articulo in articulos:
                try:
                    # A) Extraer enlace desde el atributo url del componente
                    enlace_relativo = articulo.get("url", None)
                    source_url = f"{base_url}{enlace_relativo}" if enlace_relativo else None

                    # B) Extraer título desde el span dentro de idb-heading
                    titulo_tag = articulo.find("div", slot="title")
                    span_titulo = titulo_tag.find("span") if titulo_tag else None
                    title = span_titulo.get_text(strip=True) if span_titulo else "Sin título"

                    # C) Extraer fecha desde el elemento time
                    fecha_tag = articulo.find("time")
                    fecha_texto = fecha_tag.get_text(strip=True) if fecha_tag else None
                    presentation_date = _parse_date_bid(fecha_texto)

                    # Si no se encuentra una fecha válida, usar la fecha actual
                    if not presentation_date:
                        presentation_date = date.today()

                    # Crear objeto en el formato esperado
                    item = {
                        'title': title,
                        'description': title,
                        'source_url': source_url,
                        'source_type': "Organismo Internacional",
                        'category': "Noticias",
                        'country': "Regional",
                        'institution': "BID",
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


def _parse_date_bid(date_str):
    """
    Parsear una fecha en formato "Enero 30, 2026" o similar.
    """
    if not date_str:
        return None
    
    # Diccionario de meses en español (con mayúscula inicial)
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
            mes = meses.get(partes[0], None)
            dia = int(partes[1])
            anio = int(partes[2])
            
            if mes:
                return date(anio, mes, dia)
    except (ValueError, IndexError):
        pass
    
    return None


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_bid_noticias())

    # Imprimir resultados
    print(f"\nTotal de noticias encontradas: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)