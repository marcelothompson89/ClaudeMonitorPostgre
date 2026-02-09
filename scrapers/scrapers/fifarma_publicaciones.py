from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import date
import re


async def scrape_fifarma_publicaciones():
    """
    Scraper para la sección de Publicaciones de FIFARMA.
    Extrae publicaciones relacionadas con la industria farmacéutica en América Latina.
    """
    base_url = "https://fifarma.org"
    url = "https://fifarma.org/publicaciones/"
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
            await page.wait_for_selector(".elementor-heading-title", timeout=60000)

            # Extraer HTML renderizado
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Buscar todas las secciones de publicaciones
            # Cada publicación tiene un h4 con título, time con fecha, y texto descriptivo
            
            # Buscar todos los contenedores de columna que tienen publicaciones
            columns = soup.find_all("div", class_="elementor-column")

            for column in columns:
                try:
                    # A) Extraer título (h4 con clase elementor-heading-title)
                    title_tag = column.find("h4", class_="elementor-heading-title")
                    if not title_tag:
                        continue
                    
                    title = title_tag.get_text(strip=True)
                    if not title:
                        continue

                    # B) Extraer fecha del elemento time
                    presentation_date = None
                    time_tag = column.find("time")
                    if time_tag:
                        # Intentar obtener del atributo datetime o del texto
                        datetime_attr = time_tag.get("datetime", "")
                        date_text = time_tag.get_text(strip=True)
                        
                        # Parsear fecha del texto (formato DD/MM/YYYY)
                        presentation_date = _parse_date_fifarma_pub(date_text)
                        
                        # Si no funcionó, intentar con el atributo datetime
                        if not presentation_date and datetime_attr:
                            presentation_date = _parse_datetime_attr(datetime_attr)
                    
                    # Si no se encontró fecha, usar fecha actual
                    if not presentation_date:
                        presentation_date = date.today()

                    # C) Extraer descripción del texto
                    description = title  # Por defecto usar el título
                    text_editor = column.find("div", class_="elementor-widget-text-editor")
                    if text_editor:
                        # Obtener todos los párrafos
                        paragraphs = text_editor.find_all("p")
                        desc_parts = []
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            # Ignorar párrafos vacíos o que solo dicen "Ver documento"
                            if text and text.lower() != "ver documento":
                                desc_parts.append(text)
                        if desc_parts:
                            description = " ".join(desc_parts)

                    # D) Extraer URL de descarga
                    source_url = None
                    
                    # Buscar enlace de descarga jet-download
                    download_link = column.find("a", class_="jet-download")
                    if download_link and download_link.get("href"):
                        source_url = download_link["href"]
                    
                    # Si no hay jet-download, buscar enlace directo a PDF
                    if not source_url:
                        all_links = column.find_all("a", href=True)
                        for link in all_links:
                            href = link.get("href", "")
                            if ".pdf" in href.lower():
                                source_url = href
                                break
                    
                    # Si aún no hay URL, buscar cualquier enlace en el text-editor
                    if not source_url and text_editor:
                        link_in_text = text_editor.find("a", href=True)
                        if link_in_text:
                            source_url = link_in_text["href"]

                    if not source_url:
                        continue

                    # Crear objeto en el formato esperado
                    publication = {
                        'title': title,
                        'description': description[:500] if len(description) > 500 else description,  # Limitar descripción
                        'source_url': source_url,
                        'source_type': "Organismo Internacional",
                        'category': "Publicaciones",
                        'country': "Regional",
                        'institution': "FIFARMA",
                        'presentation_date': presentation_date,
                    }

                    # Evitar duplicados por título
                    if not any(p['title'] == title for p in items):
                        items.append(publication)

                except Exception as e:
                    print(f"Error procesando publicación: {e}")

        except Exception as e:
            print(f"Error en la navegación: {e}")

        finally:
            await browser.close()

    return items


def _parse_date_fifarma_pub(date_str):
    """
    Parsear una fecha en formato "12/01/2026" (DD/MM/YYYY).
    """
    if not date_str:
        return None
    
    try:
        # Formato DD/MM/YYYY
        match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str.strip())
        if match:
            dia = int(match.group(1))
            mes = int(match.group(2))
            anio = int(match.group(3))
            
            if 1 <= dia <= 31 and 1 <= mes <= 12 and 2000 <= anio <= 2100:
                return date(anio, mes, dia)
    except (ValueError, IndexError):
        pass
    
    return None


def _parse_datetime_attr(datetime_str):
    """
    Parsear una fecha del atributo datetime en formato ISO "2026-01-12T17:18:20-05:00".
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
    items = asyncio.run(scrape_fifarma_publicaciones())

    # Imprimir resultados
    print(f"\nTotal de publicaciones encontradas: {len(items)}\n")
    for item in items:
        print(item)
        print("-" * 80)