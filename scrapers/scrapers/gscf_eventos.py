from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, date


async def scrape_gscf_eventos():
    """
    Scraper para la sección de eventos de Global Self-Care Federation utilizando Playwright.
    """
    base_url = "https://www.selfcarefederation.org"
    url = "https://www.selfcarefederation.org/events"
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

            # Esperar que se carguen los eventos
            await page.wait_for_selector("div.card-content", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todos los eventos
            eventos = soup.find_all("div", class_="card-content")

            for evento in eventos:
                try:
                    # A) Extraer título desde h3 > span
                    titulo_tag = evento.find("h3")
                    title_span = titulo_tag.find("span") if titulo_tag else None
                    title = title_span.get_text(strip=True) if title_span else "Sin título"

                    # B) Buscar enlace en el contenedor padre
                    parent = evento.find_parent("a")
                    if parent and parent.get("href"):
                        enlace_relativo = parent["href"]
                        source_url = f"{base_url}{enlace_relativo}" if not enlace_relativo.startswith("http") else enlace_relativo
                    else:
                        # Buscar enlace alternativo en el article padre
                        article_parent = evento.find_parent("article")
                        if article_parent and article_parent.get("about"):
                            source_url = f"{base_url}{article_parent['about']}"
                        else:
                            source_url = None

                    # C) Extraer descripción desde field--name-body
                    descripcion_tag = evento.find("div", class_="field--name-body")
                    if descripcion_tag:
                        descripcion_p = descripcion_tag.find("p")
                        description = descripcion_p.get_text(strip=True) if descripcion_p else title
                    else:
                        description = title

                    # D) Extraer fecha desde p.event--datetime
                    fecha_tag = evento.find("p", class_="event--datetime")
                    if fecha_tag:
                        # Tomar el primer span que contiene la fecha
                        fecha_span = fecha_tag.find("span")
                        fecha_texto = fecha_span.get_text(strip=True) if fecha_span else None
                    else:
                        fecha_texto = None
                    
                    presentation_date = _parse_date_gscf_eventos(fecha_texto)

                    # Si no se encuentra una fecha válida, usar la fecha actual
                    if not presentation_date:
                        presentation_date = date.today()

                    # Crear objeto en el formato esperado
                    item = {
                        'title': title,
                        'description': description,
                        'source_url': source_url,
                        'source_type': "Organismo Internacional",
                        'category': "Eventos",
                        'country': "Global",
                        'institution': "Global Self-Care Federation",
                        'presentation_date': presentation_date,
                    }

                    items.append(item)
                except Exception as e:
                    print(f"Error procesando evento: {e}")

        except Exception as e:
            print(f"Error en la navegación: {e}")

        finally:
            await browser.close()

    return items


def _parse_date_gscf_eventos(date_str):
    """
    Parsear una fecha en formato "27 May 2025 | 13:00 |" o similar.
    Toma solo la parte de la fecha.
    """
    if not date_str:
        return None
    
    # Diccionario de meses en inglés
    meses = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }
    
    try:
        # Tomar solo la parte antes del primer "|"
        fecha_parte = date_str.split("|")[0].strip()
        partes = fecha_parte.lower().split()
        
        if len(partes) >= 3:
            dia = int(partes[0])
            mes = meses.get(partes[1].lower(), None)
            anio = int(partes[2])
            
            if mes:
                return date(anio, mes, dia)
    except (ValueError, IndexError):
        pass
    
    return None


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_gscf_eventos())

    # Imprimir resultados
    print(f"\nTotal de eventos encontrados: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)