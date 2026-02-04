from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, date


async def scrape_codex_noticias():
    """
    Scraper para la sección de noticias de Codex Alimentarius utilizando Playwright.
    """
    base_url = "https://www.fao.org"
    url = "https://www.fao.org/fao-who-codexalimentarius/news-and-events/en/"
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

            # Esperar que se carguen las noticias
            await page.wait_for_selector("div.listWrapper", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todas las noticias
            noticias = soup.find_all("div", class_="listWrapper")

            for noticia in noticias:
                try:
                    # A) Extraer título y enlace desde h3.list-title > a
                    titulo_tag = noticia.find("h3", class_="list-title")
                    enlace_tag = titulo_tag.find("a") if titulo_tag else None
                    title = enlace_tag.get_text(strip=True) if enlace_tag else "Sin título"
                    enlace_relativo = enlace_tag["href"] if enlace_tag else None
                    source_url = f"{base_url}{enlace_relativo}" if enlace_relativo else None

                    # B) Extraer descripción desde div.list-text
                    descripcion_tag = noticia.find("div", class_="list-text")
                    description = descripcion_tag.get_text(strip=True) if descripcion_tag else title

                    # C) Extraer fecha desde div.list-date
                    fecha_tag = noticia.find("div", class_="list-date")
                    fecha_texto = fecha_tag.get_text(strip=True) if fecha_tag else None
                    presentation_date = _parse_date_codex(fecha_texto)

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
                        'institution': "Codex Alimentarius",
                        'presentation_date': presentation_date,
                    }

                    items.append(item)
                except Exception as e:
                    print(f"Error procesando noticia: {e}")

        except Exception as e:
            print(f"Error en la navegación: {e}")

        finally:
            await browser.close()

    return items


def _parse_date_codex(date_str):
    """
    Parsear una fecha en formato "03 February 2026" o similar.
    Puede incluir icono de calendario al inicio.
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
        
        # Buscar el patrón día mes año en las partes
        for i in range(len(partes) - 2):
            try:
                dia = int(partes[i])
                mes = meses.get(partes[i + 1], None)
                anio = int(partes[i + 2])
                
                if mes and 1 <= dia <= 31 and 2000 <= anio <= 2100:
                    return date(anio, mes, dia)
            except ValueError:
                continue
    except (ValueError, IndexError):
        pass
    
    return None


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_codex_noticias())

    # Imprimir resultados
    print(f"\nTotal de noticias encontradas: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)