from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import date
from urllib.parse import urljoin


async def scrape_andi_noticias():
    """
    Scraper para la sección de Noticias de ANDI Colombia.
    Extrae noticias relacionadas con la industria y el sector empresarial colombiano.
    """
    base_url = "https://www.andi.com.co"
    url = "https://www.andi.com.co/Home/Noticias"
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

            # Esperar que se carguen las noticias
            await page.wait_for_selector(".noticia-extra1", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todos los contenedores de noticias
            news_items = soup.find_all("div", class_="noticia-extra1")

            for item in news_items:
                try:
                    # A) Extraer título
                    title = None
                    title_span = item.find("span", class_="title_noticia")
                    if title_span:
                        title_link = title_span.find("a")
                        if title_link:
                            # Obtener texto del strong o directamente del enlace
                            strong_tag = title_link.find("strong")
                            if strong_tag:
                                title = strong_tag.get_text(strip=True)
                            else:
                                title = title_link.get_text(strip=True)
                    
                    if not title:
                        continue
                    
                    # Limpiar título (remover "..." al final si existe)
                    title = title.rstrip('.')

                    # B) Extraer URL
                    source_url = None
                    if title_span:
                        title_link = title_span.find("a")
                        if title_link and title_link.get("href"):
                            href = title_link["href"]
                            # Construir URL completa
                            source_url = urljoin(base_url, href)
                    
                    if not source_url:
                        continue

                    # C) Extraer descripción
                    description = title  # Por defecto usar el título
                    body_span = item.find("span", class_="body_noticia")
                    if body_span:
                        # Obtener texto sin el "Ver más"
                        body_text = body_span.get_text(strip=True)
                        # Remover "Ver más" del final
                        body_text = body_text.replace("Ver más", "").strip()
                        if body_text:
                            description = body_text

                    # D) Fecha de scrapeo (no hay fecha visible en el HTML)
                    presentation_date = date.today()

                    # Crear objeto en el formato esperado
                    news = {
                        'title': title,
                        'description': description,
                        'source_url': source_url,
                        'source_type': "Gremio Empresarial",
                        'category': "Noticias",
                        'country': "Colombia",
                        'institution': "ANDI",
                        'presentation_date': presentation_date,
                    }

                    # Evitar duplicados por URL
                    if not any(n['source_url'] == source_url for n in items):
                        items.append(news)

                except Exception as e:
                    print(f"Error procesando noticia: {e}")

        except Exception as e:
            print(f"Error en la navegación: {e}")

        finally:
            await browser.close()

    return items


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_andi_noticias())

    # Imprimir resultados
    print(f"\nTotal de noticias encontradas: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)