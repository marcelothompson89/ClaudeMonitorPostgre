import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_latam_regnews():
    print("[Latam ReguNews] Iniciando scraping...")
    base_url = "https://latamregunews.com"
    url = f"{base_url}/ver-todos-los-paises/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print(f"[Latam ReguNews] Accediendo a URL: {url}")
            await page.goto(url, timeout=60000)

            # Esperar a que las noticias carguen
            await page.wait_for_selector("div.uael-post-wrapper", timeout=20000)

            # Extraer HTML y analizarlo con BeautifulSoup
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Buscar todas las noticias
            noticias = soup.select("div.uael-post-wrapper")
            if not noticias:
                print("[Latam ReguNews] ⚠️ No se encontraron noticias.")
                return []

            items = []

            for noticia in noticias:
                try:
                    # Extraer título y URL
                    link = noticia.select_one("h4.uael-post__title a")
                    if not link:
                        continue

                    title = link.text.strip()
                    news_url = link["href"]
                    news_url = f"{base_url}{news_url}" if news_url.startswith("/") else news_url

                    # Extraer fecha
                    fecha_element = noticia.select_one("span.uael-post__date")
                    fecha = _parse_date(fecha_element.text.strip()) if fecha_element else datetime.now().date()

                    # Extraer categoría
                    category_element = noticia.select_one("span.uael-post__terms-meta-cat a")
                    category = category_element.text.strip() if category_element else "Sin categoría"

                    # Extraer fuente
                    source_element = noticia.select_one("div.uael-post__thumbnail img")
                    source = source_element["alt"].strip() if source_element else "Latam ReguNews"

                    # Crear objeto de noticia
                    item = {
                        "title": title,
                        "description": title,
                        "source_url": news_url,
                        "source_type": "latam_regunews",
                        "country": _extract_country_from_url(news_url),
                        "presentation_date": fecha,
                        "category": category,
                        "institution": "latam_regunews",
                        "metadata": json.dumps({"tipo": "Noticia"})
                    }

                    items.append(item)
                    print(f"[Latam ReguNews] ✅ Noticia extraída: {title[:100]}")

                except Exception as e:
                    print(f"[Latam ReguNews] ⚠️ Error procesando noticia: {str(e)}")
                    continue

            print(f"[Latam ReguNews] 🎯 Se encontraron {len(items)} noticias")
            return items

        except Exception as e:
            print(f"[Latam ReguNews] ❌ Error: {str(e)}")
            return []
        finally:
            await browser.close()


def _parse_date(fecha_str):
    """
    Convierte fechas en español como "19 de febrero de 2025" a formato datetime.
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
        print(f"[Latam ReguNews] ⚠️ Error procesando fecha '{fecha_str}', se usará la fecha actual: {e}")
        return datetime.now().date()


def _extract_country_from_url(url):
    """
    Extrae el país desde la URL si está presente.
    Ejemplo: 'https://latamregunews.com/argentina/anmat-argentina/...' -> 'Argentina'
    """
    try:
        partes = url.split("/")
        for parte in partes:
            if parte.lower() in ["argentina", "mexico", "brasil", "colombia", "chile", "ecuador", "paraguay", "dominicana", "honduras"]:
                return parte.capitalize()
    except Exception as e:
        print(f"[Latam ReguNews] ⚠️ Error extrayendo país desde '{url}': {e}")
    return "Desconocido"


# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados en JSON
#     noticias = asyncio.run(scrape_latam_regunews())
#     print(json.dumps([{
#         **noticia,
#         'presentation_date': noticia['presentation_date'].strftime('%Y-%m-%d') if noticia['presentation_date'] else None
#     } for noticia in noticias], indent=4, ensure_ascii=False))
