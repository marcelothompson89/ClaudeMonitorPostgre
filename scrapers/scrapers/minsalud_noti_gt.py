import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_minsalud_noti_gt():
    """Scraper optimizado para noticias del MSPAS Guatemala"""
    print("[MinSalud Noticias_GT] Iniciando scraping...")
    base_url = "https://www.mspas.gob.gt"
    url = f"{base_url}/noticias-mspas"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        try:
            print(f"[MSPAS Noticias_GT] Accediendo a URL: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle", timeout=60000)
            
            # Obtener contenido HTML
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Buscar artículos con el selector principal
            noticias = soup.select("article.itemView")
            
            if not noticias:
                print("[MSPAS Noticias_GT] ⚠️ No se encontraron noticias.")
                return []

            print(f"[MSPAS Noticias_GT] Encontrados {len(noticias)} artículos")
            items = []

            for noticia in noticias:
                try:
                    # Extraer título y URL
                    link = noticia.select_one("h2.uk-article-title a")
                    if not link:
                        continue
                    
                    title = link.text.strip()
                    noticia_url = link.get("href", "")
                    if noticia_url.startswith("/"):
                        noticia_url = f"{base_url}{noticia_url}"

                    # Extraer fecha
                    fecha_element = noticia.select_one("span.itemDateCreated")
                    fecha = _parse_date(fecha_element.text.strip()) if fecha_element else datetime.now().date()

                    # Extraer descripción
                    descripcion_element = noticia.select_one("div.itemIntroText p")
                    descripcion = descripcion_element.text.strip() if descripcion_element else title

                    # Extraer imagen
                    img_element = noticia.select_one("img")
                    imagen_url = None
                    if img_element and img_element.get("src"):
                        imagen_url = img_element["src"]
                        if not imagen_url.startswith("http"):
                            imagen_url = f"{base_url}{imagen_url}"

                    # Crear objeto de noticia
                    item = {
                        "title": title,
                        "description": descripcion,
                        "source_url": noticia_url,
                        "source_type": "Ejecutivo",
                        "country": "Guatemala",
                        "presentation_date": fecha,
                        "category": "Noticias",
                        "institution": "Ministerio de Salud Guatemala",
                        "metadata": json.dumps({"imagen": imagen_url})
                    }

                    items.append(item)
                    print(f"[MSPAS Noticias_GT] ✅ Procesada: {title[:80]}...")

                except Exception as e:
                    print(f"[MSPAS Noticias_GT] ⚠️ Error procesando noticia: {str(e)}")
                    continue

            print(f"[MSPAS Noticias_GT] 🎯 Total procesadas: {len(items)} noticias")
            return items

        except Exception as e:
            print(f"[MSPAS Noticias_GT] ❌ Error: {str(e)}")
            return []
        finally:
            await browser.close()


def _parse_date(fecha_str):
    """Convierte fechas en español a formato datetime"""
    try:
        fecha_str = fecha_str.replace(".", "").strip().lower()
        
        # Diccionario de meses en español
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'sept': 9, 'octubre': 10,
            'nov': 11, 'noviembre': 11, 'diciembre': 12, 'dic': 12, 'october': 10,
            'august': 8, 'june': 6
        }
        
        partes = fecha_str.split()
        if len(partes) < 2:
            return datetime.now().date()
        
        # Extraer día
        dia = int(''.join(filter(str.isdigit, partes[0])))
        
        # Extraer mes
        mes = None
        for parte in partes:
            parte_limpia = parte.lower()
            for mes_nombre, mes_num in meses.items():
                if mes_nombre in parte_limpia:
                    mes = mes_num
                    break
            if mes:
                break
        
        if not mes:
            return datetime.now().date()
        
        # Extraer año
        anio = datetime.now().year
        for parte in partes:
            numeros = ''.join(filter(str.isdigit, parte))
            if len(numeros) == 4 and numeros.isdigit():
                anio = int(numeros)
                break
        
        return datetime(anio, mes, dia).date()
        
    except Exception as e:
        print(f"[MSPAS Noticias_GT] ⚠️ Error parseando fecha '{fecha_str}': {e}")
        return datetime.now().date()


if __name__ == "__main__":
    noticias = asyncio.run(scrape_minsalud_noti_gt())
    print(json.dumps([{
        **noticia,
        'presentation_date': noticia['presentation_date'].strftime('%Y-%m-%d')
    } for noticia in noticias], indent=4, ensure_ascii=False))