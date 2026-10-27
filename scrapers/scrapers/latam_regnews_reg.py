import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re

async def scrape_latam_regnews():
    print("[Latam ReguNews] Iniciando scraping...")
    base_url = "https://latamregunews.com"
    url = f"{base_url}/categoria/noticias/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print(f"[Latam ReguNews] Accediendo a URL: {url}")
            await page.goto(url, timeout=60000)

            # Esperar a que las noticias carguen
            await page.wait_for_selector("a.card", timeout=20000)

            # Extraer HTML y analizarlo con BeautifulSoup
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Buscar todas las noticias
            noticias = soup.select("a.card")
            if not noticias:
                print("[Latam ReguNews] ⚠️ No se encontraron noticias.")
                return []

            items = []

            for noticia in noticias:
                try:
                    # Extraer título y URL
                    title_element = noticia.select_one("div.card-title")
                    news_url = noticia.get("href")
                    if not title_element or not news_url:
                        continue

                    title = title_element.get_text(strip=True)
                    news_url = f"{base_url}{news_url}" if news_url.startswith("/") else news_url

                    # Extraer descripción
                    excerpt_element = noticia.select_one("p.card-excerpt")
                    description = excerpt_element.get_text(strip=True) if excerpt_element else title

                    # Extraer fecha
                    fecha_element = noticia.select_one("span.card-date")
                    fecha = _parse_date(fecha_element.get_text(strip=True)) if fecha_element else datetime.now().date()

                    # Extraer país (badge con bandera)
                    country_element = noticia.select_one("div.card-flag-badge")
                    country = country_element.get_text(strip=True) if country_element else ""
                    if not country:
                        country = _extract_country_from_url(news_url)

                    # Extraer categoría
                    category_element = noticia.select_one("div.card-tags span.tag")
                    category = category_element.get_text(strip=True) if category_element else "Noticias"

                    # Crear objeto de noticia
                    item = {
                        "title": title,
                        "description": description,
                        "source_url": news_url,
                        "source_type": "RegNews",
                        "country": country,
                        "presentation_date": fecha,
                        "category": "Noticias",
                        "institution": "Latam ReguNews",
                        "metadata": json.dumps({"tipo": "Noticia", "categoria_origen": category}, ensure_ascii=False)
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
    Convierte fechas en español como "2 oct. 2026" o "19 de febrero de 2025" a date.
    Si falla, usa la fecha actual.
    """
    meses = {
        'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'sep': 9, 'set': 9, 'oct': 10, 'nov': 11, 'dic': 12
    }

    try:
        partes = [t for t in re.split(r"[\s.,]+", fecha_str.lower()) if t and t != "de"]
        dia, mes, anio = partes[:3]
        mes_num = meses[mes[:3]]
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


if __name__ == "__main__":
    # Ejecutar el scraper y mostrar los resultados en JSON
    noticias = asyncio.run(scrape_latam_regnews())
    print(json.dumps([{
        **noticia,
        'presentation_date': noticia['presentation_date'].strftime('%Y-%m-%d') if noticia['presentation_date'] else None
    } for noticia in noticias], indent=4, ensure_ascii=False))
