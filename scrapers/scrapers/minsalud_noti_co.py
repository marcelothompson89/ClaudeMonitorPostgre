from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, date
import random
import time

async def scrape_minsalud_noticias_co():
    """
    Scraper para las noticias del Ministerio de Salud utilizando Playwright.
    """
    base_url = "https://www.minsalud.gov.co"
    url = "https://www.minsalud.gov.co/CC/Paginas/noticias-2025.aspx"
    items = []

    async with async_playwright() as p:
        # Configuración del navegador con evasión de detección
        browser = await p.chromium.launch(
            headless=True,  # Cambiar a False para depuración visual
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Crear un contexto con cabeceras más realistas
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        
        page = await context.new_page()
        
        # Interceptar y modificar las peticiones para parecer más humano
        await page.set_extra_http_headers({
            "Accept-Language": "es-ES,es;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
            "Referer": "https://www.minsalud.gov.co/"
        })

        max_retries = 5
        for attempt in range(max_retries):
            try:
                print(f"[MINSALUD NOTICIAS_CO] Intentando cargar la página (Intento {attempt + 1}/{max_retries})...")
                
                # Estrategia 1: Intentar con networkidle (más permisivo que load)
                if attempt == 0:
                    await page.goto(url, timeout=60000, wait_until="networkidle")
                # Estrategia 2: Intentar solo con domcontentloaded
                elif attempt == 1:
                    await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                # Estrategia 3: Intentar con URL alternativa (a veces la estructura de URLs cambia)
                elif attempt == 2:
                    alt_url = "https://www.minsalud.gov.co/Paginas/default.aspx"
                    await page.goto(alt_url, timeout=60000, wait_until="domcontentloaded")
                    # Intenta navegar a noticias desde la página principal
                    await asyncio.sleep(2)
                    menu_links = await page.query_selector_all("a[href*='noticias']")
                    if menu_links:
                        await menu_links[0].click()
                        await page.wait_for_load_state("domcontentloaded")
                # Estrategia 4: Intentar sin esperar a que termine de cargar 
                else:
                    await page.goto(url, timeout=120000)
                    # Esperar un tiempo fijo en lugar de eventos de carga
                    await asyncio.sleep(10)
                
                # Añadir comportamiento humano: scroll aleatorio
                await page.evaluate("""
                    () => {
                        window.scrollTo({
                            top: Math.floor(Math.random() * 300),
                            behavior: 'smooth'
                        });
                    }
                """)
                await asyncio.sleep(2)
                
                print("[MINSALUD NOTICIAS_CO] Página cargada correctamente ✅")
                break
            except Exception as e:
                print(f"[MINSALUD NOTICIAS_CO] ❌ Error al cargar la página: {e}")
                if attempt == max_retries - 1:
                    print("[MINSALUD NOTICIAS_CO] ⚠ No se pudo cargar la página tras varios intentos, abortando scraper.")
                    await browser.close()
                    return []
                
                # Esperar un tiempo aleatorio entre intentos para parecer más humano
                espera = random.uniform(3, 7)
                print(f"Esperando {espera:.2f} segundos antes del próximo intento...")
                await asyncio.sleep(espera)

        # Buscar el contenedor de noticias - Usando la estructura exacta del HTML
        print("[MINSALUD NOTICIAS_CO] Buscando contenedor de noticias...")
        
        # Extraer el contenido HTML renderizado
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        # Estructura específica identificada: Lista con clase dfwp-column dfwp-list
        noticias_lista = soup.select_one("ul.dfwp-column.dfwp-list")
        if noticias_lista:
            # Buscar elementos li con clase dfwp-item
            items_li = noticias_lista.find_all("li", class_="dfwp-item")
            print(f"[MINSALUD NOTICIAS_CO] Encontrados {len(items_li)} elementos de lista")
            
            # Buscar los divs con id="linkitem" y clase="item" dentro de los li
            noticias = []
            for li in items_li:
                item_div = li.find("div", id="linkitem", class_="item")
                if item_div:
                    noticias.append(item_div)
            
            print(f"[MINSALUD NOTICIAS_CO] Encontradas {len(noticias)} noticias con estructura exacta")
        else:
            # Si no encontramos la estructura exacta, intentar con selectores alternativos
            print("[MINSALUD NOTICIAS_CO] No se encontró la estructura específica, probando alternativas...")
            selectores_contenedor = [
                "div[class*='cbq-layout-main']",
                ".cbq-layout-main",
                "div.ms-webpart-zone",
                "#WebPartWPQ2",
                ".ms-webpartzone-cell"
            ]
            
            # Intentar diferentes selectores para encontrar noticias
            noticias = []
            for selector in selectores_contenedor:
                noticias_div = soup.select_one(selector)
                if noticias_div:
                    # Intentar varios tipos de estructura de noticias
                    for item_class in ["link-item", "ms-rtestate-field", "item", "noticia"]:
                        items_found = noticias_div.find_all("div", class_=item_class)
                        if items_found:
                            noticias = items_found
                            print(f"[MINSALUD NOTICIAS_CO] Encontradas {len(noticias)} noticias con selector {selector} y clase {item_class}")
                            break
                
                if noticias:
                    break
            
            # Si todavía no encontramos noticias, buscar estructura alternativa
            if not noticias:
                print("[MINSALUD NOTICIAS_CO] Intentando encontrar noticias con estructura alternativa...")
                # Buscar por patrones típicos de listas de noticias
                noticias = soup.find_all("div", class_=lambda c: c and ("item" in c.lower() or "noticia" in c.lower()))
                if not noticias:
                    # Último intento: buscar enlaces dentro de contenedores
                    noticias = [div for div in soup.find_all("div") if div.find("a") and div.find("a").text.strip()]
        
        print(f"[MINSALUD NOTICIAS_CO] Total de noticias encontradas: {len(noticias)}")
        
        # Si no encontramos noticias, guardar el HTML para análisis
        if not noticias:
            with open("minsalud_debug.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("[MINSALUD NOTICIAS_CO] No se encontraron noticias. HTML guardado como 'minsalud_debug.html'")

        for noticia in noticias:
            try:
                # A) Extraer título y enlace - Estructura específica identificada
                link_item_div = noticia.find("div", class_="link-item")
                
                if link_item_div:
                    # El título está en el primer enlace dentro del div.link-item
                    titulo_a = link_item_div.find("a")
                    if titulo_a:
                        title = titulo_a.get_text(strip=True)
                        enlace_relativo = titulo_a["href"] if titulo_a.has_attr("href") else None
                    else:
                        # Estructura alternativa
                        title = "SIN TÍTULO"
                        enlace_relativo = None
                else:
                    # Intentar con estructura alternativa
                    titulo_a = noticia.find("a")
                    if not titulo_a:
                        # Buscar en estructuras anidadas
                        for div in noticia.find_all("div"):
                            if div.find("a"):
                                titulo_a = div.find("a")
                                break
                    
                    title = titulo_a.get_text(strip=True) if titulo_a else "SIN TÍTULO"
                    enlace_relativo = titulo_a["href"] if titulo_a and titulo_a.has_attr("href") else None

                # Evitar duplicación del dominio en la URL
                if enlace_relativo:
                    if not enlace_relativo.startswith("http"):
                        source_url = f"{base_url}{enlace_relativo}"
                    else:
                        source_url = enlace_relativo  # Ya es una URL completa
                else:
                    source_url = None
                
                # B) Extraer descripción y fecha - Estructura específica identificada
                description = ""
                presentation_date = None
                
                if link_item_div:
                    # En la estructura identificada, la fecha está en un div con clase "description"
                    fecha_div = link_item_div.find("div", class_="description")
                    if fecha_div:
                        fecha_texto = fecha_div.get_text(strip=True)
                        # El formato identificado es "YYYY-MM-DD 00:00:00"
                        try:
                            presentation_date = datetime.strptime(fecha_texto, "%Y-%m-%d %H:%M:%S").date()
                            # Usamos la fecha como descripción si no hay otra
                            description = fecha_texto
                        except ValueError:
                            print(f"[MINSALUD NOTICIAS_CO] Error al parsear fecha: {fecha_texto}")
                
                # Si no encontramos descripción con la estructura específica, probar alternativas
                if not description:
                    for desc_class in ["description", "ms-rtestate-field", "summary", "descripcion"]:
                        desc_div = noticia.find("div", class_=desc_class)
                        if desc_div:
                            description = desc_div.get_text(strip=True)
                            break
                
                # Si todavía no hay descripción, buscar texto plano
                if not description:
                    # Obtener todos los textos dentro del div de noticia, excluyendo el título
                    textos = [t.strip() for t in noticia.strings if t.strip() and t.strip() != title]
                    if textos:
                        description = " ".join(textos)
                
                # Si no se encontró fecha en la estructura principal, intentar extraerla de la descripción
                if not presentation_date:
                    presentation_date = _parse_date(description)
                
                # Buscar fechas en otros elementos si aún no se encontró
                if not presentation_date:
                    fecha_div = noticia.find(["div", "span"], class_=lambda c: c and ("date" in c.lower() or "fecha" in c.lower()))
                    if fecha_div:
                        presentation_date = _parse_date(fecha_div.get_text(strip=True))
                
                # Si aún no hay fecha, usar la fecha actual
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
                print(f"[MINSALUD NOTICIAS_CO] Noticia agregada: {title}")
            except Exception as e:
                print(f"Error procesando noticia: {e}")

        # Tomar una captura de pantalla para depuración
        await page.screenshot(path="minsalud_screenshot.png")
        print("[MINSALUD NOTICIAS_CO] Captura de pantalla guardada como 'minsalud_screenshot.png'")
        
        await browser.close()

    return items

def _parse_date(date_str):
    """
    Intenta extraer la fecha en varios formatos desde un texto.
    """
    if not date_str:
        return None
    
    # Formato específico identificado en el sitio: "2025-04-12 00:00:00"
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S").date()
    except ValueError:
        pass
    
    # Lista de patrones de fecha a probar si el formato específico falla
    formatos = [
        "%Y-%m-%d",   # 2025-01-06
        "%d/%m/%Y",   # 06/01/2025
        "%d-%m-%Y",   # 06-01-2025
        "%d.%m.%Y",   # 06.01.2025
        "%d %B %Y",   # 6 Enero 2025
        "%d %b %Y"    # 6 Ene 2025
    ]
    
    # Intentar cada formato
    for formato in formatos:
        try:
            # Buscar fechas en el texto
            fecha_texto = date_str.strip()
            match = datetime.strptime(fecha_texto, formato)
            if match:
                return match.date()
        except ValueError:
            continue
    
    # Si no se pudo extraer fecha con formato específico, buscar patrones comunes
    import re
    
    # Patrón para fechas como "6 de enero de 2025" o variantes
    patron_fecha_es = r'(\d{1,2})\s+de\s+([a-zA-ZáéíóúÁÉÍÓÚ]+)\s+(?:de\s+)?(\d{4})'
    match = re.search(patron_fecha_es, date_str)
    
    if match:
        dia, mes_nombre, anio = match.groups()
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        mes = meses.get(mes_nombre.lower())
        if mes:
            return date(int(anio), mes, int(dia))
    
    return None

# Ejecutar el scraper
if __name__ == "__main__":
    items = asyncio.run(scrape_minsalud_noticias_co())
    for item in items:
        print(f"\nTítulo: {item['title']}")
        print(f"Descripción: {item['description']}")
        print(f"URL: {item['source_url']}")
        print(f"Fecha: {item['presentation_date']}")
    
    print(f"\nTotal noticias extraídas: {len(items)}")