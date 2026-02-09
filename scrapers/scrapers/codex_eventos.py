from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import date
from urllib.parse import urljoin, unquote


async def scrape_codex_eventos():
    """
    Scraper para la sección de Nutrition and Labelling del Codex Alimentarius (FAO-WHO).
    Extrae los estándares relacionados con nutrición y etiquetado.
    """
    base_url = "https://www.fao.org"
    url = "https://www.fao.org/fao-who-codexalimentarius/thematic-areas/nutrition-labelling/en/"
    items = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
                "Referer": base_url
            }
        )
        page = await context.new_page()

        try:
            print(f"Navegando a: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # Esperar que se cargue la tabla de estándares
            await page.wait_for_selector("table", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todas las tablas y encontrar la que contiene los estándares
            tables = soup.find_all("table")
            
            for table in tables:
                rows = table.find_all("tr")
                
                for row in rows:
                    try:
                        cells = row.find_all("td")
                        
                        # Verificar que la fila tiene suficientes celdas (Reference, Title, Committee, Year, PDFs)
                        if len(cells) >= 4:
                            # A) Extraer Reference (primera celda)
                            reference = cells[0].get_text(strip=True)
                            
                            # Validar que parece un código de estándar (CXS, CXG, CXA, etc.)
                            if not reference or not any(reference.startswith(prefix) for prefix in ['CXS', 'CXG', 'CXA', 'CXC']):
                                continue
                            
                            # B) Extraer Title (segunda celda)
                            title = cells[1].get_text(strip=True)
                            
                            # C) Extraer enlace al PDF en inglés (buscar en la celda de PDFs)
                            source_url = None
                            
                            # La celda de PDFs generalmente es la última o penúltima
                            for cell in cells:
                                links = cell.find_all("a", href=True)
                                for link in links:
                                    href = link.get("href", "")
                                    # Buscar enlaces a PDFs en inglés (terminan en 'e.pdf')
                                    if "pdf" in href.lower() and ("_e.pdf" in href.lower() or href.endswith("e.pdf")):
                                        # Construir URL completa
                                        if href.startswith("/"):
                                            source_url = urljoin(base_url, href)
                                        else:
                                            source_url = href
                                        break
                                if source_url:
                                    break
                            
                            # Si no encontramos PDF en inglés, buscar cualquier PDF
                            if not source_url:
                                for cell in cells:
                                    links = cell.find_all("a", href=True)
                                    for link in links:
                                        href = link.get("href", "")
                                        if "pdf" in href.lower():
                                            if href.startswith("/"):
                                                source_url = urljoin(base_url, href)
                                            else:
                                                source_url = href
                                            break
                                    if source_url:
                                        break

                            # D) Extraer año de la columna "Last modified" (generalmente la 4ta celda)
                            presentation_date = None
                            if len(cells) >= 4:
                                year_text = cells[3].get_text(strip=True)
                                try:
                                    year = int(year_text)
                                    # Usar el 2 de enero como primer día hábil del año
                                    # (1 de enero suele ser feriado)
                                    presentation_date = date(year, 1, 2)
                                except (ValueError, TypeError):
                                    pass
                            
                            # Si no se pudo extraer el año, usar fecha actual
                            if not presentation_date:
                                presentation_date = date.today()

                            # Crear objeto en el formato esperado
                            item = {
                                'title': title,
                                'description': reference,
                                'source_url': source_url,
                                'source_type': "Organismo Internacional",
                                'category': "Eventos",
                                'country': "Global",
                                'institution': "CODEXALIMENTARIUS FAO-WHO",
                                'presentation_date': presentation_date,
                            }

                            items.append(item)
                            
                    except Exception as e:
                        print(f"Error procesando fila: {e}")

        except Exception as e:
            print(f"Error en la navegación: {e}")

        finally:
            await browser.close()

    return items


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_codex_eventos())

    # Imprimir resultados
    print(f"\nTotal de estándares encontrados: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)