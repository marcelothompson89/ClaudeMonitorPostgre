import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_minsa_med_pa():
    print("[MINSA Alertas_PA] Iniciando scraping...")
    base_url = "https://www.minsa.gob.pa"
    url = f"{base_url}/informacion-salud/alertas-y-comunicados?title=&field_decree_date_value%5Bvalue%5D%5Byear%5D=2025"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print(f"[MINSA Alertas_PA] Accediendo a URL: {url}")
            await page.goto(url, timeout=60000)

            # Esperar a que cargue la tabla de alertas
            await page.wait_for_selector("table.views-view-grid", timeout=20000)

            # Extraer HTML y analizarlo con BeautifulSoup
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Buscar todas las filas de la tabla
            alertas = soup.select("table.views-view-grid tbody tr td")
            if not alertas:
                print("[MINSA Alertas_PA] ⚠️ No se encontraron alertas.")
                return []

            items = []

            for alerta in alertas:
                try:
                    # Extraer título y URL
                    link = alerta.select_one("div.views-field-title a")
                    if not link:
                        continue

                    title = link.text.strip()
                    alerta_url = link["href"]
                    alerta_url = f"{base_url}{alerta_url}" if alerta_url.startswith("/") else alerta_url

                    # Extraer fecha
                    fecha_element = alerta.select_one("div.views-field-field-decree-date span.date-display-single")
                    fecha = _parse_date(fecha_element.text.strip()) if fecha_element else datetime.now().date()

                    # Crear objeto de alerta
                    item = {
                        "title": title,
                        "description": title,
                        "source_url": alerta_url,
                        "source_type": "minsa_nota_medicamentos_pa",
                        "country": "Panamá",
                        "presentation_date": fecha,
                        "category": "Alertas",
                        "institution": "Ministerio de Salud Panamá",
                        "metadata": json.dumps({"tipo": "Nota de Seguridad"})
                    }

                    items.append(item)
                    print(f"[MINSA Alertas_PA] ✅ Alerta procesada: {title[:100]}")

                except Exception as e:
                    print(f"[MINSA Alertas_PA] ⚠️ Error procesando alerta: {str(e)}")
                    continue

            print(f"[MINSA Alertas_PA] 🎯 Se encontraron {len(items)} alertas")
            return items

        except Exception as e:
            print(f"[MINSA Alertas_PA] ❌ Error: {str(e)}")
            return []
        finally:
            await browser.close()


def _parse_date(fecha_str):
    """
    Convierte fechas en español como "12 de Febrero de 2025" a formato datetime.
    Si falla, usa la fecha actual.
    """
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }

    try:
        fecha_str = fecha_str.replace("de", "").strip()
        dia, mes, anio = fecha_str.split()
        mes_num = meses[mes.lower()]
        return datetime(int(anio), mes_num, int(dia)).date()
    except Exception as e:
        print(f"[MINSA Alertas_PA] ⚠️ Error procesando fecha '{fecha_str}', se usará la fecha actual: {e}")
        return datetime.now().date()


# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados en JSON
#     alertas = asyncio.run(scrape_minsa_alertas())
#     print(json.dumps([{
#         **alerta,
#         'presentation_date': alerta['presentation_date'].strftime('%Y-%m-%d') if alerta['presentation_date'] else None
#     } for alerta in alertas], indent=4, ensure_ascii=False))
