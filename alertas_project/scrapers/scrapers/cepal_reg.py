import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re

async def scrape_cepal_noticias_reg():
    """
    Scraper para el sitio de noticias de CEPAL utilizando Playwright.
    """
    base_url = "https://www.cepal.org"
    url = "https://www.cepal.org/es/search/date/2025?query=&type%5B0%5D=cepal_pr&items_per_page=50&search_api_language=es"
    items = []  # Lista para almacenar las noticias

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navegar a la página
            await page.goto(url)
            # Esperar a que se carguen las noticias dinámicas
            await page.wait_for_selector(".mb-3 article", timeout=10000)

            # Obtener el contenido HTML de la página
            html_content = await page.content()
            soup = BeautifulSoup(html_content, "html.parser")

            # Buscar las noticias
            noticias = soup.select("div.mb-3 article")
            print(f"Noticias encontradas: {len(noticias)}")

            for noticia in noticias:
                try:
                    # A) Fecha de la noticia
                    fecha_tag = noticia.select_one("time.datetime")
                    fecha_str = fecha_tag.get("datetime") if fecha_tag else None
                    
                    if fecha_str:
                        try:
                            # Parsear la fecha en formato ISO
                            fecha_hora = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                        except ValueError:
                            # Si hay error, usamos la fecha actual
                            fecha_hora = datetime.now()
                    else:
                        fecha_hora = datetime.now()

                    # B) Título y enlace
                    titulo_tag = noticia.select_one("h4 a")
                    titulo_texto = titulo_tag.text.strip() if titulo_tag else None
                    enlace_relativo = titulo_tag["href"] if titulo_tag else None
                    enlace_url = f"{base_url}{enlace_relativo}" if enlace_relativo else None

                    if not titulo_texto:
                        print("Noticia sin título, descartada.")
                        continue

                    # C) Tipo de noticia
                    tipo_tag = noticia.select_one("div.d-flex.align-items-center")
                    tipo_texto = "No especificado"
                    if tipo_tag:
                        # Extraer el tipo después del símbolo |
                        tipo_texto_completo = tipo_tag.text.strip()
                        if "|" in tipo_texto_completo:
                            tipo_texto = tipo_texto_completo.split("|")[1].strip()

                    # D) Descripción
                    descripcion_tag = noticia.select_one("p.border-bottom")
                    descripcion = descripcion_tag.text.strip() if descripcion_tag else "Sin descripción disponible"

                    # Crear el diccionario del item
                    item = {
                        "title": titulo_texto,
                        "description": f"{descripcion}\nTipo: {tipo_texto}",
                        "source_type": "CEPAL",
                        "category": "Noticias",
                        "country": "Regional",
                        "source_url": enlace_url,
                        "institution": "CEPAL",
                        "presentation_date": fecha_hora,
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando noticia: {e}")

        except Exception as e:
            print(f"Error al procesar la página: {e}")

        finally:
            await browser.close()

    # Imprimir resultados
    print(f"Noticias procesadas: {len(items)}")
    return items


# if __name__ == "__main__":
#     # Ejecutar el scraper
#     items = asyncio.run(scrape_cepal_noticias_reg())

#     # Mostrar resultados en formato JSON
#     print(json.dumps([
#         {
#             **item,
#             'presentation_date': item['presentation_date'].strftime('%Y-%m-%d %H:%M:%S') 
#                 if isinstance(item['presentation_date'], datetime) else None
#         }
#         for item in items
#     ], indent=4, ensure_ascii=False))