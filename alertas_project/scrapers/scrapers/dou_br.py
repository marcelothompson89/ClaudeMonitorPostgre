from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
from datetime import datetime, date
import asyncio


async def scrape_dou_br():
    """
    Scraper para la página del Diário Oficial da União (Ministério da Saúde) con manejo de paginación usando Playwright Async API.
    """
    base_url = "https://www.in.gov.br"
    search_url = f"{base_url}/leiturajornal?org=Minist%C3%A9rio%20da%20Sa%C3%BAde"

    items = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"Error al cargar la página: {e}")
            await browser.close()
            return []

        while True:
            try:
                await page.wait_for_selector("ul.ul-materias > li.materia-link", timeout=10000)
            except Exception as e:
                print(f"Error al esperar las noticias: {e}")
                break

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            noticias = soup.select("ul.ul-materias > li.materia-link")

            if not noticias:
                print("No se encontraron noticias en esta página.")
                break

            for noticia in noticias:
                try:
                    title_tag = noticia.select_one("h5.title-marker a")
                    title = title_tag.text.strip() if title_tag else "Sin título"
                    link = title_tag["href"] if title_tag else None
                    full_url = f"{base_url}{link}" if link and not link.startswith("http") else link

                    breadcrumb = noticia.select_one("ol.dou-hierarquia")
                    section = breadcrumb.select_one(".secao-marker").text.strip() if breadcrumb else "Sin sección"
                    org = breadcrumb.select_one(".hierarchy-item-marker").text.strip() if breadcrumb else "Sin órgano"
                    pub_info = breadcrumb.select_one(".publication-info-marker").text.strip() if breadcrumb else "Sin información"

                    date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', pub_info)
                    presentation_date = datetime.strptime(date_match.group(1), "%d/%m/%Y").date() if date_match else None

                    description = noticia.select_one("p.abstract-marker").text.strip() if noticia.select_one("p.abstract-marker") else "Sin descripción"

                    item = {
                        'title': title,
                        'description': description,
                        'source_url': full_url,
                        'source_type': "Ejecutivo",
                        'category': "Normas",
                        'country': "Brasil",
                        'institution': "Diário Oficial da União",
                        'presentation_date': presentation_date,
                        'metadata': {
                            'section': section,
                            'organization': org,
                            'publication_info': pub_info
                        }
                    }
                    items.append(item)
                except Exception as e:
                    print(f"Error procesando noticia: {e}")

            try:
                next_button = page.locator(".pagination .pagination-button", has_text="Próximo »")
                if await next_button.is_visible():
                    await next_button.click()
                    await page.wait_for_timeout(2000)
                else:
                    print("No se encontró el botón 'Próximo »'. Fin de la paginación.")
                    break
            except Exception as e:
                print(f"Error al intentar avanzar a la siguiente página: {e}")
                break

        await browser.close()

    return items


# if __name__ == "__main__":
#     items = asyncio.run(scrape_dou_br())

#     for item in items:
#         print(item)
