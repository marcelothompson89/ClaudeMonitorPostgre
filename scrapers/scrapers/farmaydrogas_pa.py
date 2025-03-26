import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_farmaydrogas_pa():
    print("[MINSA Resoluciones_PA] Iniciando scraping...")
    base_url = "https://www.minsa.gob.pa"
    url = f"{base_url}/informacion-salud/resoluciones-2025-fyd"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print(f"[MINSA Resoluciones_PA] Accediendo a URL: {url}")
            await page.goto(url, timeout=60000)

            # Esperar a que la página cargue correctamente
            await page.wait_for_selector("div.field-items", timeout=20000)

            # Extraer HTML y analizarlo con BeautifulSoup
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Buscar todas las resoluciones dentro de los divs field-item
            resoluciones = soup.select("div.field-item span.file a")
            if not resoluciones:
                print("[MINSA Resoluciones_PA] ⚠️ No se encontraron resoluciones.")
                return []

            items = []

            for resol in resoluciones:
                try:
                    # Extraer título y URL
                    title = resol.text.strip()
                    pdf_url = resol["href"]
                    pdf_url = f"{base_url}{pdf_url}" if pdf_url.startswith("/") else pdf_url

                    # Intentar extraer la fecha del título
                    fecha = _extract_date_from_title(title)

                    # Crear objeto de resolución
                    item = {
                        "title": title,
                        "description": title,
                        "source_url": pdf_url,
                        "source_type": "Ejecutivo",
                        "country": "Panamá",
                        "presentation_date": fecha,
                        "category": "Resoluciones",
                        "institution": "Ministerio de Salud Panamá",
                        "metadata": json.dumps({"tipo": "Resolución"})
                    }

                    items.append(item)
                    print(f"[MINSA Resoluciones_PA] ✅ Resolución procesada: {title[:100]}")

                except Exception as e:
                    print(f"[MINSA Resoluciones_PA] ⚠️ Error procesando resolución: {str(e)}")
                    continue

            print(f"[MINSA Resoluciones_PA] 🎯 Se encontraron {len(items)} resoluciones")
            return items

        except Exception as e:
            print(f"[MINSA Resoluciones_PA] ❌ Error: {str(e)}")
            return []
        finally:
            await browser.close()


def _extract_date_from_title(title):
    """
    Extrae la fecha desde el título del documento (si es posible).
    Ejemplo de títulos:
    - "Resol. 001 - 06-01-2025 - Farmacia Colon."
    - "Resol. 004 - 13-01-2025 - Guia para la elaboración..."
    """
    try:
        parts = title.split(" - ")
        if len(parts) > 1:
            date_part = parts[1].strip()
            return datetime.strptime(date_part, "%d-%m-%Y").date()
    except Exception as e:
        print(f"[MINSA Resoluciones_PA] ⚠️ Error extrayendo fecha de '{title}': {e}")
    return datetime.now().date()  # Si falla, usar la fecha actual


# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados en JSON
#     resoluciones = asyncio.run(scrape_minsa_resoluciones())
#     print(json.dumps([{
#         **res,
#         'presentation_date': res['presentation_date'].strftime('%Y-%m-%d') if res['presentation_date'] else None
#     } for res in resoluciones], indent=4, ensure_ascii=False))
