from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, date

async def scrape_animal_politico_salud():
    """
    Scraper para la sección de salud de Animal Político utilizando Playwright.
    """
    base_url = "https://www.animalpolitico.com"
    url = "https://www.animalpolitico.com/salud/notas"
    items = []

    async with async_playwright() as p:
        # Lanzar navegador en modo visible para depuración
        browser = await p.chromium.launch(headless=True)  # Cambiar a False para ver el navegador
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9",
                "Referer": base_url
            }
        )
        page = await context.new_page()

        # # Captura de logs para depuración
        # page.on("console", lambda msg: print(f"PAGE LOG: {msg.text}"))
        # page.on("request", lambda request: print(f"Request: {request.url}"))
        # page.on("response", lambda response: print(f"Response: {response.url} - {response.status}"))

        try:
            print(f"Navegando a: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # Esperar que se cargue el contenido
            await page.wait_for_selector(".grid .col-span-3", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar artículos dentro del contenedor principal
            contenedor = soup.find("div", class_="grid grid-cols-3 gap-4 mb-10")
            articulos = contenedor.find_all("div", class_="col-span-3") if contenedor else []

            for articulo in articulos:
                try:
                    # A) Extraer título y enlace
                    titulo_tag = articulo.find("a")
                    title = titulo_tag.get_text(strip=True) if titulo_tag else "Sin título"
                    enlace_relativo = titulo_tag["href"] if titulo_tag else None
                    source_url = f"{base_url}{enlace_relativo}" if enlace_relativo else None

                    # B) Extraer descripción
                    descripcion_tag = articulo.find("div", class_="font-Inter-Bold")
                    description = descripcion_tag.get_text(strip=True) if descripcion_tag else ""

                    # C) Extraer fecha
                    fecha_tag = articulo.find("div", class_="text-xs")
                    fecha_texto = fecha_tag.get_text(strip=True) if fecha_tag else None
                    presentation_date = _parse_date(fecha_texto)

                    # Si no se encuentra una fecha válida, usar la fecha actual
                    if not presentation_date:
                        presentation_date = date.today()

                    # Crear objeto en el formato esperado
                    item = {
                        'title': description,
                        'description': description,
                        'source_url': source_url,
                        'source_type': "Animal Político Periódico",
                        'category': "Noticias",
                        'country': "México",
                        'institution': "Animal Político",
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


def _parse_date(date_str):
    """
    Parsear una fecha en formato conocido como "06/01/2025" o similar.
    """
    if not date_str:
        return None
    try:
        # Intentar parsear con formato dd/mm/yyyy
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except ValueError:
        return None


# if __name__ == "__main__":
#     # Ejecutar el scraper de forma asíncrona
#     items = asyncio.run(scrape_animal_politico_salud())

#     # Imprimir resultados
#     for item in items:
#         print(item)
