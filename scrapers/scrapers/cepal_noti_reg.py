from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, date
import re


async def scrape_cepal_noticias():
    """
    Scraper para la sección de noticias de CEPAL utilizando Playwright.
    """
    base_url = "https://www.cepal.org"
    url = "https://www.cepal.org/es/busqueda?query=&type%5B0%5D=cepal_article&type%5B1%5D=cepal_pr&type%5B2%5D=cepal_speech&type%5B3%5D=cepal_note&type%5B4%5D=cepal_news&type%5B5%5D=cepal_infographic"
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
            await page.wait_for_selector("article", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todos los artículos
            articulos = soup.find_all("article", class_="py-3")

            for articulo in articulos:
                try:
                    # A) Extraer título y enlace desde h4 > a
                    titulo_tag = articulo.find("h4")
                    enlace_tag = titulo_tag.find("a") if titulo_tag else None
                    title = enlace_tag.get_text(strip=True) if enlace_tag else "Sin título"
                    enlace_relativo = enlace_tag["href"] if enlace_tag else None
                    source_url = f"{base_url}{enlace_relativo}" if enlace_relativo and not enlace_relativo.startswith("http") else enlace_relativo

                    # B) Extraer fecha desde div con data-component-id
                    fecha_div = articulo.find("div", attrs={"data-component-id": "eclacstrap_base:header-date"})
                    fecha_texto = fecha_div.get_text(strip=True) if fecha_div else None
                    presentation_date = _parse_date_cepal(fecha_texto)

                    # Si no se encuentra una fecha válida, usar la fecha actual
                    if not presentation_date:
                        presentation_date = date.today()

                    # C) Extraer descripción desde p
                    descripcion_tag = articulo.find("p", class_="pb-3")
                    description = descripcion_tag.get_text(strip=True) if descripcion_tag else title

                    # Crear objeto en el formato esperado
                    item = {
                        'title': title,
                        'description': description,
                        'source_url': source_url,
                        'source_type': "Organismo Internacional",
                        'category': "Noticias",
                        'country': "Regional",
                        'institution': "CEPAL",
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


def _parse_date_cepal(date_str):
    """
    Parsear una fecha en formato "3 Feb 2026" o similar.
    El texto puede incluir otros elementos como "| Nota informativa".
    """
    if not date_str:
        return None
    
    # Diccionario de meses en español (abreviados y completos)
    meses = {
        'ene': 1, 'enero': 1,
        'feb': 2, 'febrero': 2,
        'mar': 3, 'marzo': 3,
        'abr': 4, 'abril': 4,
        'may': 5, 'mayo': 5,
        'jun': 6, 'junio': 6,
        'jul': 7, 'julio': 7,
        'ago': 8, 'agosto': 8,
        'sep': 9, 'sept': 9, 'septiembre': 9,
        'oct': 10, 'octubre': 10,
        'nov': 11, 'noviembre': 11,
        'dic': 12, 'diciembre': 12
    }
    
    try:
        # Limpiar la fecha y convertir a minúsculas
        date_str = date_str.lower().strip()
        
        # Buscar patrón de fecha con regex: día mes año
        pattern = r'(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})'
        match = re.search(pattern, date_str)
        
        if match:
            dia = int(match.group(1))
            mes_str = match.group(2)
            anio = int(match.group(3))
            
            mes = meses.get(mes_str, None)
            
            if mes and 1 <= dia <= 31 and 2000 <= anio <= 2100:
                return date(anio, mes, dia)
    except (ValueError, IndexError):
        pass
    
    return None


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_cepal_noticias())

    # Imprimir resultados
    print(f"\nTotal de noticias encontradas: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)