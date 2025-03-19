import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime
import random
import re

async def scrape_sica_noticias_cam():
    print("[SICA Noticias] Iniciando scraping con técnicas anti-bloqueo...")
    
    # Lista de agentes de usuario para rotar
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:99.0) Gecko/20100101 Firefox/99.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:99.0) Gecko/20100101 Firefox/99.0"
    ]
    
    async with async_playwright() as p:
        # Configuración del navegador para evadir detección
        browser = await p.chromium.launch(
            headless=True,  # Modo visible para eludir bloqueos
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # Crear contexto con características anti-fingerprinting
        context = await browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={'width': 1920, 'height': 1080},
            locale='es-ES',
            timezone_id='America/Guatemala',
            permissions=['geolocation']
        )
        
        # Añadir scripts para ocultar rasgos de automatización
        await context.add_init_script("""
        () => {
            // Ocultar WebDriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // Ocultar automatización
            window.navigator.chrome = {
                runtime: {},
            };
            
            // Modificar user-agent original
            const originalUserAgent = window.navigator.userAgent;
            Object.defineProperty(window.navigator, 'userAgent', {
                get: () => originalUserAgent,
            });
            
            // Simular canvas fingerprint aleatorio
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                if (type === 'image/png' && this.width === 16 && this.height === 16) {
                    return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACEklEQVQ4T2NkYGBgYBgFAyYB5rKyciYFBQWPJUuW/CfV3UpKSp5FRUUMzJWVlQwXrlzlvfP6NZ+ikhKDjJwcg6GhIcOzZ88Y7t+/z/Ds2TOGhQsXMty5c4fh9u3bDO/evWNgYWFhYBGXFN+6ZQsDc2lpKcODB/cZvr16zbBm926GwMBAtNDevXsZQkNDGf7+/cvw/v17hk+fPjE8evSI4cKFCwyXLl1i+PLlCwMXFxeDtJwcw+rVqxmY8/LyGC5dOM/w+/VbhoULFzFERUUxKCgoMISFhTGsWLGC4fPnzwz///9nYGRkZPj+/TvDpUuXGL5+/crw48cPhu/fvzMsXbqUgYeHh+HYsWMMzLm5uQynT51k+PbqDcOiRYsYYmJiGHJychj27NnDcOPGDQYODg4GkCaQRmZmZobHjx8znD59muHFixcMIA3r1q1j4OfnZzh06BADc15eHsOJ48cYvr18zbBw4UKGsLAwhtTUVIa9e/cy3Lp1i4GXl5fh79+/DCCnHTt2jOHw4cMMHz9+ZPj27RvDhg0bGACBzvD06VOQCxmYs7KyGM6dO8fw5eUbhoULFzKEhoYyJCQkMOzbt4/h7t27DEJCQgwgwz9//sxw8uRJhqNHjzJ8+PCB4du3bwzbt29n4OTkZLh//z7DfyYmBpAbmNPT0xmuX7/O8OHlG4aFCxcyBAQEMCQmJjLs2bOH4fr16wx8fHwMv379Yli3bh3DokWLGEZSIAMAp8ydZFVwJKgAAAAASUVORK5CYII=';
                }
                return originalToDataURL.apply(this, arguments);
            };
        }
        """)
        
        page = await context.new_page()
        
        # Establecer tiempo de espera más largo
        page.set_default_timeout(60000)
        
        # URL del sitio
        url = "https://www.sica.int/consulta/noticias_401_3_1.html"
        print(f"[SICA Noticias] Accediendo a: {url}")
        
        try:
            # Añadir delay aleatorio para simular comportamiento humano
            await asyncio.sleep(random.uniform(3, 7))
            
            # Visitar la página
            await page.goto(url, timeout=90000)
            
            # Simular comportamiento humano con movimientos de ratón
            await page.mouse.move(
                random.randint(100, 700), 
                random.randint(100, 500)
            )
            
            # Hacer scroll aleatorio
            await page.evaluate("""
            () => {
                window.scrollTo({
                    top: Math.floor(Math.random() * 100),
                    behavior: 'smooth'
                });
            }
            """)
            
            await asyncio.sleep(random.uniform(2, 5))
            
            # Esperar a que la página cargue completamente
            await page.wait_for_load_state("networkidle", timeout=30000)
            
            print("[SICA Noticias] Página cargada, buscando noticias...")
            
            # Buscar noticias en la página
            # Intentar varios selectores posibles
            selectors = [
                "tr.k-master-row", 
                "div.noticia", 
                "article.news", 
                "a[href*='noticia']"
            ]
            
            noticias_elementos = []
            for selector in selectors:
                elementos = await page.query_selector_all(selector)
                if elementos and len(elementos) > 0:
                    print(f"[SICA Noticias] ✅ Encontrados {len(elementos)} elementos con selector: {selector}")
                    noticias_elementos = elementos
                    break
            
            if not noticias_elementos:
                print("[SICA Noticias] ⚠️ No se encontraron elementos de noticias con los selectores comunes")
                # Tomar captura de pantalla para diagnóstico
                await page.screenshot(path="sica_no_elements.png")
                print("Captura de pantalla guardada como 'sica_no_elements.png'")
                return []
                
            items = []
            
            # Procesar las noticias encontradas
            for i, elemento in enumerate(noticias_elementos):
                try:
                    print(f"[SICA Noticias] Procesando noticia {i+1}/{len(noticias_elementos)}...")
                    
                    # Extraer título y URL
                    title_element = await elemento.query_selector("h4 a, h3 a, h2 a, a")
                    if not title_element:
                        print(f"[SICA Noticias] No se encontró título para el elemento {i+1}, omitiendo...")
                        continue
                        
                    title = await title_element.inner_text()
                    news_url = await title_element.get_attribute("href")
                    
                    # Normalizar URL
                    if news_url.startswith("/"):
                        news_url = f"https://www.sica.int{news_url}"
                    elif not news_url.startswith("http"):
                        news_url = f"https://www.sica.int/{news_url}"
                    
                    # Extraer fecha
                    date_element = await elemento.query_selector("time, .date, .fecha")
                    fecha = None
                    if date_element:
                        # Intentar obtener del atributo datetime
                        fecha_iso = await date_element.get_attribute("datetime")
                        if fecha_iso:
                            fecha = _parse_date(fecha_iso)
                        else:
                            # Intentar obtener del texto
                            fecha_text = await date_element.inner_text()
                            fecha = _parse_date(fecha_text)
                    
                    if not fecha:
                        # Si no se encuentra fecha, buscar patrones de fecha en el texto
                        elemento_text = await elemento.inner_text()
                        fecha = _extract_date_from_text(elemento_text)
                        
                    if not fecha:
                        fecha = datetime.now().date()
                    
                    # Extraer descripción
                    description_element = await elemento.query_selector("span, p")
                    description = await description_element.inner_text() if description_element else title
                    
                    # Extraer institución
                    institution = "SICA"
                    institution_element = await elemento.query_selector("h5")
                    if institution_element:
                        institution_text = await institution_element.inner_text()
                        if "Publicado por" in institution_text:
                            parts = institution_text.split("Publicado por")
                            if len(parts) > 1:
                                institution = parts[1].replace(":", "").strip()
                    
                    # Crear objeto de noticia
                    item = {
                        "title": title.strip(),
                        "description": description.strip(),
                        "source_url": news_url,
                        "source_type": "sica_noticias",
                        "country": "Centroamérica",
                        "presentation_date": fecha,
                        "category": "Noticias",
                        "institution": institution,
                        "metadata": json.dumps({"tipo": "Noticia SICA"})
                    }
                    
                    items.append(item)
                    print(f"[SICA Noticias] ✅ Noticia extraída: {title[:50]}")
                    
                except Exception as e:
                    print(f"[SICA Noticias] ⚠️ Error procesando noticia {i+1}: {str(e)}")
                    continue
            
            print(f"[SICA Noticias] 🎯 Se encontraron {len(items)} noticias")
            return items
            
        except Exception as e:
            print(f"[SICA Noticias] ❌ Error general: {str(e)}")
            await page.screenshot(path="sica_error.png")
            print("Captura de pantalla de error guardada como 'sica_error.png'")
            return []
        finally:
            await context.close()
            await browser.close()

def _parse_date(date_str):
    """
    Intenta parsear una fecha de string usando varios formatos comunes.
    """
    try:
        # Limpiar el string
        date_str = date_str.strip()
        
        # Para fechas en formato de día de semana + mes + día + año como "Thu Mar 06 2025..."
        if re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)', date_str):
            match = re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\w+)\s+(\d+)\s+(\d{4})', date_str)
            if match:
                _, month, day, year = match.groups()
                months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, 
                         "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
                if month in months:
                    return datetime(int(year), months[month], int(day)).date()
        
        # Para fechas en español como "6 de marzo de 2025" o "jueves, 6 de marzo de 2025"
        match = re.search(r'(\d+)\s+de\s+(\w+)\s+de\s+(\d{4})', date_str, re.IGNORECASE)
        if match:
            day, month_name, year = match.groups()
            month_map = {
                'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
                'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
            }
            if month_name.lower() in month_map:
                return datetime(int(year), month_map[month_name.lower()], int(day)).date()
        
        # Para fechas como dd/mm/yyyy o dd-mm-yyyy
        match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_str)
        if match:
            day, month, year = match.groups()
            return datetime(int(year), int(month), int(day)).date()
        
        # Para fechas en formato ISO YYYY-MM-DD
        match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
        if match:
            year, month, day = match.groups()
            return datetime(int(year), int(month), int(day)).date()
        
    except Exception as e:
        print(f"[SICA Noticias] ⚠️ Error parseando fecha '{date_str}': {e}")
    
    return None

def _extract_date_from_text(text):
    """
    Busca patrones de fecha en un texto y extrae la fecha si la encuentra.
    """
    # Patrón para fechas como "6 de marzo de 2025"
    pattern1 = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})'
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        day, month_name, year = match.groups()
        month_map = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        if month_name.lower() in month_map:
            return datetime(int(year), month_map[month_name.lower()], int(day)).date()
    
    # Patrón para fechas como "06/03/2025" o "06-03-2025"
    pattern2 = r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})'
    match = re.search(pattern2, text)
    if match:
        day, month, year = match.groups()
        return datetime(int(year), int(month), int(day)).date()
    
    return None

# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados en JSON
#     noticias = asyncio.run(scrape_sica_noticias_cam())
#     print(json.dumps([{
#         **noticia,
#         'presentation_date': noticia['presentation_date'].strftime('%Y-%m-%d') if noticia['presentation_date'] else None
#     } for noticia in noticias], indent=4, ensure_ascii=False))