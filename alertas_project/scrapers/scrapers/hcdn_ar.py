import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_hcdn_ar():
    """
    Scraper para proyectos de la página de Diputados usando Playwright.
    """
    url = "https://www.diputados.gov.ar/proyectos/"
    items = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Navegar a la página
            await page.goto(url, timeout=60000)

            # Ejecutar el JavaScript necesario para simular el clic en el botón de búsqueda
            await page.click('input[type="submit"][value="Buscar"]')

            # Esperar hasta que los elementos relevantes se carguen
            await page.wait_for_selector('h4', timeout=60000)

            # Extraer el contenido de la página
            html_content = await page.content()
            soup = BeautifulSoup(html_content, "html.parser")

            # Buscar bloques (por ejemplo, <div class="dp-metadata">)
            proyectos_metadata = soup.find_all("div", class_="dp-metadata")

            for md in proyectos_metadata:
                try:
                    # A) Título
                    titulo_h4 = md.find_previous("h4")
                    titulo_texto = titulo_h4.get_text(strip=True) if titulo_h4 else "SIN TÍTULO"

                    # B) Buscar spans con la info "Expediente Diputados: 7489-D-2024", "Fecha: 30/12/2024", etc.
                    spans = md.find_all("span")
                    meta_dict = {}
                    for sp in spans:
                        text_sp = sp.get_text(strip=True)
                        if ':' in text_sp:
                            key, val = text_sp.split(':', 1)
                            key = key.strip()
                            val = val.strip()
                            meta_dict[key] = val

                    # C) El texto principal en <div class="dp-texto"> (descripción)
                    dp_texto_div = md.find_next("div", class_="dp-texto")
                    description_text = dp_texto_div.get_text(" ", strip=True) if dp_texto_div else ""

                    # D) Unimos el texto principal con la información de meta_dict
                    meta_data_str = "\n".join(f"{k}: {v}" for k, v in meta_dict.items())
                    final_description = (description_text + "\n\n" + meta_data_str).strip()

                    # E) "Ver documento original"
                    ver_original_a = md.find_next("a", text="Ver documento original")
                    pdf_url = ver_original_a.get("href") if ver_original_a else None

                    # F) Crear el diccionario del item
                    item = {
                        'title': titulo_texto,
                        'description': final_description,
                        'source_type': "Diputados",
                        'category': "Proyectos",
                        'country': "Argentina",
                        'source_url': pdf_url,
                        'presentation_date': _parse_date(meta_dict.get("Fecha")),
                        'metadata': {
                            'expediente': meta_dict.get("Expediente Diputados"),
                            'image_url': None,  # Si hubiera una imagen relacionada
                        },
                        'institution': "HCDN"
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando un proyecto: {e}")

        except Exception as e:
            print(f"Error navegando o procesando la página: {e}")
        finally:
            await browser.close()

    return items


def _parse_date(date_str):
    """
    Parsear "30/12/2024" u otro formato a un datetime de Python.
    Ajusta según tu caso. Si 'date_str' es None o no parseable, regresa None.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        return None


# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados
#     items = asyncio.run(scrape_diputados_proyectos())

#     # Formatear salida como JSON
#     print(json.dumps([{
#         **item,
#         'presentation_date': item['presentation_date'].strftime('%Y-%m-%d') if item['presentation_date'] else None
#     } for item in items], indent=4, ensure_ascii=False))
