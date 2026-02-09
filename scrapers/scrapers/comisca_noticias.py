from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import date
from urllib.parse import urljoin


async def scrape_comisca_noticias():
    """
    Scraper para el sistema de conocimiento de COMISCA.
    Extrae publicaciones relacionadas con salud de Centroamérica y República Dominicana.
    """
    base_url = "https://www.comisca.org"
    url = "https://www.comisca.org/knowsystem"
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
            await page.wait_for_selector(".knowsystem-website-box", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todos los contenedores de artículos
            articles = soup.find_all("div", class_="knowsystem-website-box")

            for article in articles:
                try:
                    # A) Extraer título y URL
                    title = None
                    source_url = None
                    
                    title_tag = article.find("h4")
                    if title_tag:
                        link_tag = title_tag.find("a")
                        if link_tag:
                            title = link_tag.get_text(strip=True)
                            href = link_tag.get("href", "")
                            if href:
                                source_url = urljoin(base_url, href)
                    
                    if not title or not source_url:
                        continue

                    # B) Extraer descripción
                    description = title  # Por defecto usar el título
                    desc_div = article.find("div", class_="css_editable_mode_hidden")
                    if desc_div:
                        inner_div = desc_div.find("div")
                        if inner_div:
                            desc_text = inner_div.get_text(strip=True)
                            if desc_text:
                                # Limitar a 500 caracteres
                                description = desc_text[:500] if len(desc_text) > 500 else desc_text

                    # C) Fecha de scrapeo (no hay fecha visible en el HTML)
                    presentation_date = date.today()

                    # Crear objeto en el formato esperado
                    pub = {
                        'title': title,
                        'description': description,
                        'source_url': source_url,
                        'source_type': "Organismo Internacional",
                        'category': "Publicaciones",
                        'country': "Regional",
                        'institution': "COMISCA",
                        'presentation_date': presentation_date,
                    }

                    # Evitar duplicados por URL
                    if not any(p['source_url'] == source_url for p in items):
                        items.append(pub)

                except Exception as e:
                    print(f"Error procesando artículo: {e}")

        except Exception as e:
            print(f"Error en la navegación: {e}")

        finally:
            await browser.close()

    return items


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_comisca_noticias())

    # Imprimir resultados
    print(f"\nTotal de publicaciones encontradas: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)