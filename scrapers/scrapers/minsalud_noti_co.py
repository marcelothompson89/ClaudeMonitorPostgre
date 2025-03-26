from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, date

async def scrape_minsalud_noticias_co():
    """
    Scraper para las noticias del Ministerio de Salud utilizando Playwright.
    """
    base_url = "https://www.minsalud.gov.co"
    url = "https://www.minsalud.gov.co/CC/Paginas/noticias-2025.aspx"
    items = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Cambiar a False si deseas ver el navegador
        page = await browser.new_page()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"[MINSALUD NOTICIAS_CO] Intentando cargar la página (Intento {attempt + 1}/{max_retries})...")
                await page.goto(url, timeout=60000)  # Aumentar timeout a 60s
                await page.wait_for_load_state("domcontentloaded")  # Esperar que el DOM esté cargado
                print("[MINSALUD NOTICIAS_CO] Página cargada correctamente ✅")
                break
            except Exception as e:
                print(f"[MINSALUD NOTICIAS_CO] ❌ Error al cargar la página: {e}")
                if attempt == max_retries - 1:
                    print("[MINSALUD NOTICIAS_CO] ⚠ No se pudo cargar la página tras varios intentos, abortando scraper.")
                    await browser.close()
                    return []

        # Buscar el contenedor de noticias
        print("[MINSALUD NOTICIAS_CO] Buscando contenedor de noticias...")
        noticias_container = "div[class*='cbq-layout-main']"  # Se detectó que funciona correctamente

        # Extraer el contenido HTML renderizado
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Buscar noticias dentro del contenedor encontrado
        noticias_div = soup.select_one(noticias_container)
        noticias = noticias_div.find_all("div", class_="link-item") if noticias_div else []

        for noticia in noticias:
            try:
                # A) Extraer título y enlace
                titulo_a = noticia.find("a")
                title = titulo_a.get_text(strip=True) if titulo_a else "SIN TÍTULO"
                enlace_relativo = titulo_a["href"] if titulo_a else None

                # Evitar duplicación del dominio en la URL
                if enlace_relativo and not enlace_relativo.startswith("http"):
                    source_url = f"{base_url}{enlace_relativo}"
                else:
                    source_url = enlace_relativo  # Ya es una URL completa

                # B) Extraer descripción (posiblemente contiene la fecha)
                fecha_div = noticia.find("div", class_="description")
                description = fecha_div.get_text(strip=True) if fecha_div else ""

                # C) Extraer fecha de publicación
                presentation_date = _parse_date(description)

                # Si no se encuentra una fecha válida, usar la fecha actual
                if not presentation_date:
                    presentation_date = date.today()

                # Crear objeto en el formato esperado
                item = {
                    'title': title,
                    'description': description,
                    'source_url': source_url,
                    'source_type': "Ejecutivo",
                    'category': "Noticias",
                    'country': "Colombia",
                    'institution': "Ministerio de Salud Colombia",
                    'presentation_date': presentation_date,
                }

                items.append(item)
            except Exception as e:
                print(f"Error procesando noticia: {e}")

        await browser.close()

    return items

def _parse_date(date_str):
    """
    Intenta extraer la fecha en formato "06/01/2025" o similar desde un texto.
    """
    if not date_str:
        return None
    
    # Buscar fechas en formato dd/mm/yyyy dentro del texto
    match = datetime.strptime(date_str.strip(), "%Y-%m-%d") if len(date_str.strip()) == 10 else None
    if match:
        return match.date()
    
    return None

# # Ejecutar el scraper
# if __name__ == "__main__":
#     items = asyncio.run(scrape_minsalud_news())
#     print(items)
