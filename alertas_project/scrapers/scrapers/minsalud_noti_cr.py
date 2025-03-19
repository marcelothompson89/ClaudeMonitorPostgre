import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_ministerio_salud_cr():
    print("[Ministerio Salud_CR] Iniciando scraping...")
    base_url = "https://www.ministeriodesalud.go.cr"
    url = f"{base_url}/index.php/prensa/62-noticias-2025"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print(f"[Ministerio Salud_CR] Accediendo a URL: {url}")
            await page.goto(url, timeout=60000)

            # Esperar a que cargue la tabla de noticias
            await page.wait_for_selector("tbody tr", timeout=10000)

            # Obtener el HTML y procesarlo con BeautifulSoup
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Encontrar todas las noticias
            noticias = soup.select("tbody tr")
            if not noticias:
                print("[Ministerio Salud_CR] ⚠️ No se encontraron noticias.")
                return []

            items = []

            for noticia in noticias:
                try:
                    # Extraer título y URL
                    link = noticia.select_one("td.list-title a")
                    if not link:
                        continue
                    
                    title = link.text.strip()
                    noticia_url = link["href"]
                    noticia_url = noticia_url if noticia_url.startswith("http") else f"{base_url}{noticia_url}"

                    # Extraer fecha
                    fecha_element = noticia.select_one("td.list-date")
                    fecha = _parse_date(fecha_element.text.strip()) if fecha_element else datetime.now().date()

                    # Extraer visitas
                    visitas_element = noticia.select_one("td.list-hits span")
                    visitas = visitas_element.text.replace("Visitas:", "").strip() if visitas_element else "Desconocidas"

                    # Crear objeto de noticia
                    item = {
                        "title": title,
                        "description": title,
                        "source_url": noticia_url,
                        "source_type": "ministerio_salud_cr",
                        "country": "Costa Rica",
                        "presentation_date": fecha,
                        "category": "Noticias",
                        "institution": "Ministerio de Salud Costa Rica",
                        "metadata": json.dumps({"visitas": visitas})
                    }

                    items.append(item)
                    print(f"[Ministerio Salud_CR] ✅ Noticia procesada: {title[:100]}")

                except Exception as e:
                    print(f"[Ministerio Salud_CR] ⚠️ Error procesando noticia: {str(e)}")
                    continue

            print(f"[Ministerio Salud_CR] 🎯 Se encontraron {len(items)} noticias")
            return items

        except Exception as e:
            print(f"[Ministerio Salud_CR] ❌ Error: {str(e)}")
            return []
        finally:
            await browser.close()


def _parse_date(fecha_str):
    """
    Convierte fechas en español como "18 Febrero 2025" a formato datetime.
    Si falla, usa la fecha actual.
    """
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }

    try:
        dia, mes, anio = fecha_str.split()
        mes_num = meses[mes.lower()]
        return datetime(int(anio), mes_num, int(dia)).date()
    except Exception as e:
        print(f"[Ministerio Salud_CR] ⚠️ Error procesando fecha '{fecha_str}', se usará la fecha actual: {e}")
        return datetime.now().date()


# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados en JSON
#     noticias = asyncio.run(scrape_ministerio_salud_cr())
#     print(json.dumps([{
#         **noticia,
#         'presentation_date': noticia['presentation_date'].strftime('%Y-%m-%d') if noticia['presentation_date'] else None
#     } for noticia in noticias], indent=4, ensure_ascii=False))
