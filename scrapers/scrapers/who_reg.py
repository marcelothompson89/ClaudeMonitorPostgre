from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, date


async def scrape_who_noticias():
    """
    Scraper para la sección de noticias de la OMS (WHO) utilizando Playwright.
    """
    base_url = "https://www.who.int"
    url = "https://www.who.int/news"
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
            await page.wait_for_selector("div.list-view--item", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todos los artículos
            articulos = soup.find_all("div", class_="list-view--item")

            for articulo in articulos:
                try:
                    # A) Extraer enlace y título
                    enlace_tag = articulo.find("a", class_="link-container")
                    source_url = enlace_tag["href"] if enlace_tag else None
                    
                    # B) Extraer título desde el párrafo con clase "heading"
                    titulo_tag = articulo.find("p", class_="heading")
                    title = titulo_tag.get_text(strip=True) if titulo_tag else "Sin título"

                    # C) Extraer fecha desde el span con clase "timestamp"
                    fecha_tag = articulo.find("span", class_="timestamp")
                    fecha_texto = fecha_tag.get_text(strip=True) if fecha_tag else None
                    presentation_date = _parse_date_who(fecha_texto)

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
                        'country': "Global",
                        'institution': "World Health Organization",
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


def _parse_date_who(date_str):
    """
    Parsear una fecha en formato "4 February 2026" o similar.
    """
    if not date_str:
        return None
    
    # Diccionario de meses en inglés
    meses = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
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
    items = asyncio.run(scrape_who_noticias())

    # Imprimir resultados
    print(f"\nTotal de noticias encontradas: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)