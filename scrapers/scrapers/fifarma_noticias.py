from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import date
import re


async def scrape_fifarma_noticias():
    """
    Scraper para la sección de Actualidad/Blog de FIFARMA.
    Extrae noticias y artículos relacionados con la industria farmacéutica en América Latina.
    """
    base_url = "https://fifarma.org"
    url = "https://fifarma.org/actualidad/"
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

            # Esperar que se cargue el contenido
            await page.wait_for_selector(".jet-listing-dynamic-field__content", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todos los contenedores de artículos (columnas con contenido)
            columns = soup.find_all("div", class_="elementor-column")

            for column in columns:
                try:
                    # A) Extraer título (h3 con clase jet-listing-dynamic-field__content)
                    title_tag = column.find("h3", class_="jet-listing-dynamic-field__content")
                    if not title_tag:
                        continue
                    
                    title = title_tag.get_text(strip=True)
                    if not title:
                        continue

                    # B) Extraer fecha del elemento time
                    presentation_date = None
                    time_tag = column.find("time")
                    if time_tag:
                        # Intentar obtener del atributo datetime
                        datetime_attr = time_tag.get("datetime", "")
                        date_text = time_tag.get_text(strip=True)
                        
                        # Parsear fecha del texto (formato "diciembre 26, 2025")
                        presentation_date = _parse_date_fifarma_actualidad(date_text)
                        
                        # Si no funcionó, intentar con el atributo datetime
                        if not presentation_date and datetime_attr:
                            presentation_date = _parse_datetime_attr(datetime_attr)
                    
                    # Si no se encontró fecha, usar fecha actual
                    if not presentation_date:
                        presentation_date = date.today()

                    # C) Extraer URL del artículo
                    source_url = None
                    
                    # Buscar enlace en el botón "CONOCE MÁS"
                    button_link = column.find("a", class_="jet-button__instance")
                    if button_link and button_link.get("href") and button_link["href"] != "#":
                        source_url = button_link["href"]
                    
                    # Si no hay botón, buscar enlace en la imagen
                    if not source_url:
                        img_container = column.find("div", class_="jet-listing-dynamic-image")
                        if img_container:
                            img_link = img_container.find_parent("a")
                            if img_link and img_link.get("href"):
                                source_url = img_link["href"]
                    
                    # Buscar enlace en los metadatos (comentarios lleva al post)
                    if not source_url:
                        comments_link = column.find("a", href=re.compile(r'#respond$'))
                        if comments_link and comments_link.get("href"):
                            # Remover #respond del final
                            source_url = comments_link["href"].replace("#respond", "")
                    
                    # Buscar cualquier enlace que parezca un post de fifarma
                    if not source_url:
                        all_links = column.find_all("a", href=True)
                        for link in all_links:
                            href = link.get("href", "")
                            if href.startswith("https://fifarma.org/") and "/author/" not in href and href.count("/") > 3:
                                source_url = href
                                break

                    if not source_url:
                        continue

                    # Limpiar URL (remover #respond si existe)
                    source_url = source_url.replace("#respond", "")

                    # D) Descripción = título (no hay extracto visible)
                    description = title

                    # Crear objeto en el formato esperado
                    article = {
                        'title': title,
                        'description': description,
                        'source_url': source_url,
                        'source_type': "Organismo Internacional",
                        'category': "Noticias",
                        'country': "Regional",
                        'institution': "FIFARMA",
                        'presentation_date': presentation_date,
                    }

                    # Evitar duplicados por título
                    if not any(a['title'] == title for a in items):
                        items.append(article)

                except Exception as e:
                    print(f"Error procesando artículo: {e}")

        except Exception as e:
            print(f"Error en la navegación: {e}")

        finally:
            await browser.close()

    return items


def _parse_date_fifarma_actualidad(date_str):
    """
    Parsear una fecha en formato "diciembre 26, 2025" o "enero 5, 2025".
    """
    if not date_str:
        return None
    
    # Diccionario de meses en español
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    try:
        # Limpiar la fecha (remover coma y espacios extra)
        date_str = date_str.replace(",", "").lower().strip()
        partes = date_str.split()
        
        # Formato: "mes dia año" (diciembre 26 2025)
        if len(partes) >= 3:
            mes = meses.get(partes[0], None)
            dia = int(partes[1])
            anio = int(partes[2])
            
            if mes and 1 <= dia <= 31 and 2000 <= anio <= 2100:
                return date(anio, mes, dia)
    except (ValueError, IndexError):
        pass
    
    return None


def _parse_datetime_attr(datetime_str):
    """
    Parsear una fecha del atributo datetime en formato ISO "2025-12-26T09:09:03-05:00".
    """
    if not datetime_str:
        return None
    
    try:
        # Extraer solo la parte de la fecha (YYYY-MM-DD)
        match = re.match(r'(\d{4})-(\d{2})-(\d{2})', datetime_str)
        if match:
            anio = int(match.group(1))
            mes = int(match.group(2))
            dia = int(match.group(3))
            
            if 1 <= dia <= 31 and 1 <= mes <= 12 and 2000 <= anio <= 2100:
                return date(anio, mes, dia)
    except (ValueError, IndexError):
        pass
    
    return None


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    items = asyncio.run(scrape_fifarma_noticias())

    # Imprimir resultados
    print(f"\nTotal de artículos encontrados: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)