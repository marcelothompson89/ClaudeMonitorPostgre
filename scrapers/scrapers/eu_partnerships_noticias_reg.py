from playwright.async_api import async_playwright
import asyncio
import json
from datetime import datetime
import re


async def scrape_eu_partnerships_noticias_reg():
    """
    Scraper para extraer noticias de International Partnerships de la Comisión Europea
    de https://international-partnerships.ec.europa.eu/news-and-events/news_en?prefLang=es
    usando Playwright.
    """
    url = "https://international-partnerships.ec.europa.eu/news-and-events/news_en?prefLang=es"
    items = []

    # Mapeo de meses en inglés a números
    meses_en = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    # Mapeo de tipos de contenido
    content_types = {
        'News announcement': 'Comunicado de Prensa',
        'Statement': 'Declaración',
        'Press release': 'Comunicado de Prensa'
    }

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)

            # Esperar a que aparezcan los artículos de noticias
            print("Esperando a que cargue la lista de noticias...")
            await page.wait_for_selector("article.ecl-content-item", timeout=45000)

            # Esperar un poco más para asegurar que todo el contenido se haya cargado
            await asyncio.sleep(2)

            # Obtener todos los artículos
            articles = await page.query_selector_all("article.ecl-content-item")
            print(f"Se encontraron {len(articles)} artículos.")

            if not articles:
                print("No se encontraron artículos en la página.")
                return []

            for idx, article in enumerate(articles):
                try:
                    # Extraer tipo de contenido
                    type_element = await article.query_selector(".ecl-content-block__primary-meta-item")
                    content_type = ""
                    if type_element:
                        content_type = await type_element.inner_text()
                        content_type = content_type.strip()
                        # Traducir tipo si está en el mapeo
                        content_type = content_types.get(content_type, content_type)

                    # Extraer fecha usando el elemento time
                    time_element = await article.query_selector("time")
                    date_text = ""
                    presentation_date = None
                    if time_element:
                        # Intentar obtener el datetime attribute (formato ISO)
                        datetime_attr = await time_element.get_attribute("datetime")
                        if datetime_attr:
                            try:
                                # Formato: 2026-03-25T12:00:00Z
                                presentation_date = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00')).date()
                            except ValueError:
                                pass

                        # Obtener el texto visible de la fecha
                        date_text = await time_element.inner_text()
                        date_text = date_text.strip()

                        # Si no se pudo parsear con datetime attribute, intentar con el texto
                        if not presentation_date and date_text:
                            # Formato: "25 March 2026"
                            date_match = re.search(r'(\d+)\s+(\w+)\s+(\d{4})', date_text)
                            if date_match:
                                try:
                                    day = int(date_match.group(1))
                                    month_name = date_match.group(2).lower()
                                    year = int(date_match.group(3))

                                    if month_name in meses_en:
                                        month = meses_en[month_name]
                                        presentation_date = datetime(year, month, day).date()
                                except ValueError as e:
                                    print(f"Error al construir fecha: {e}")

                    # Extraer título y URL
                    title_link = await article.query_selector(".ecl-content-block__title a")
                    title = ""
                    article_url = url
                    if title_link:
                        title = await title_link.inner_text()
                        title = title.strip()

                        article_url = await title_link.get_attribute("href")
                        if article_url and not article_url.startswith("http"):
                            article_url = f"https://international-partnerships.ec.europa.eu{article_url}"

                    # Si el título está vacío, saltar este artículo
                    if not title:
                        continue

                    print(f"Procesando artículo {idx + 1}: {title[:60]}...")

                    # Extraer descripción
                    description_element = await article.query_selector(".ecl-content-block__description p")
                    description_text = ""
                    if description_element:
                        description_text = await description_element.inner_text()
                        description_text = description_text.strip()

                    # Construir descripción completa
                    description_parts = []
                    if content_type:
                        description_parts.append(f"Tipo: {content_type}")
                    if date_text:
                        description_parts.append(f"Fecha: {date_text}")
                    if description_text:
                        # Limitar la descripción a 400 caracteres
                        if len(description_text) > 400:
                            description_text = description_text[:397] + "..."
                        description_parts.append(description_text)

                    description = " | ".join(description_parts) if description_parts else "Noticia de la Comisión Europea"

                    # Crear objeto en el formato esperado
                    item = {
                        'title': title,
                        'description': description,
                        'source_url': article_url,
                        'source_type': "Institucional",
                        'category': "Noticias",
                        'country': "Regional",
                        'institution': "Comisión Europea - Asociaciones Internacionales",
                        'presentation_date': presentation_date
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando artículo {idx + 1}: {e}")
                    continue

        except Exception as e:
            print(f"Error general en el scraper: {e}")
        finally:
            await browser.close()

    print(f"Scraper completado. Total de items extraídos: {len(items)}")
    return items


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_eu_partnerships_noticias_reg())

    # Formatear salida como JSON para visualizar los datos
    print(json.dumps(items, indent=4, default=str, ensure_ascii=False))
