import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os

async def scrape_minsalud_noti_gt():
    print("[MinSalud Noticias_GT] Iniciando scraping...")
    base_url = "https://www.mspas.gob.gt"
    url = f"{base_url}/noticias-mspas"

    async with async_playwright() as p:
        # Configuración del navegador con opciones adicionales
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        try:
            print(f"[MSPAS Noticias_GT] Accediendo a URL: {url}")
            # Aumentar el timeout para la navegación inicial
            await page.goto(url, timeout=90000, wait_until="domcontentloaded")
            
            print("[MSPAS Noticias_GT] Página cargada, esperando contenido...")
            
            # Esperar a que la página cargue completamente
            await page.wait_for_load_state("networkidle", timeout=90000)
            
            # Tomar una captura de pantalla para diagnóstico (opcional)
            os.makedirs("debug", exist_ok=True)
            await page.screenshot(path="debug/mspas_page.png")
            
            # Agregamos un pequeño retraso para asegurarnos de que todo el contenido dinámico se haya cargado
            await asyncio.sleep(2)
            
            # Intenta evaluar si hay elementos article.itemView directamente en el DOM
            article_count = await page.evaluate("""() => {
                const articles = document.querySelectorAll('article.itemView');
                return articles.length;
            }""")
            
            print(f"[MSPAS Noticias_GT] Detectados {article_count} artículos en la página mediante evaluación directa")
            
            # Usamos una estrategia más robusta para encontrar los elementos
            # Lista de selectores para probar en orden de preferencia
            selectors_to_try = [
                "article.itemView", 
                "div.itemList article", 
                ".itemView",
                "div.uk-article", 
                "article", 
                ".uk-grid article",
                ".item-page",
                ".blog-item",
                ".noticia",
                ".news-item"
            ]
            
            # Ahora comprobamos si ya tenemos los datos en el HTML actual directamente
            content = await page.content()
            with open("debug/page_content.html", "w", encoding="utf-8") as f:
                f.write(content)
            
            # Parsear el HTML con BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Comprobamos si encontramos artículos directamente
            direct_articles = soup.select("article.itemView")
            if direct_articles:
                print(f"[MSPAS Noticias_GT] ✅ Encontrados {len(direct_articles)} artículos directamente con BeautifulSoup")
                noticias = direct_articles
                found_selector = "article.itemView"
            else:
                # Si no encontramos directamente, probamos con los selectores alternativos
                found_selector = None
                for selector in selectors_to_try:
                    elements = soup.select(selector)
                    if elements:
                        found_selector = selector
                        print(f"[MSPAS Noticias_GT] ✅ Selector alternativo encontrado: {selector} ({len(elements)} elementos)")
                        break
                
                if not found_selector:
                    # Si aún no encontramos nada, intentamos una estrategia diferente usando el DOM de Playwright
                    print("[MSPAS Noticias_GT] ⚠️ No se encontraron selectores usando BeautifulSoup, intentando con Playwright...")
                    
                    for selector in selectors_to_try:
                        count = await page.locator(selector).count()
                        if count > 0:
                            found_selector = selector
                            print(f"[MSPAS Noticias_GT] ✅ Selector encontrado con Playwright: {selector} ({count} elementos)")
                            break
                    
                    # Si tuvimos éxito con Playwright, esperamos un momento y obtenemos el contenido nuevamente
                    if found_selector:
                        await asyncio.sleep(2)  # Esperar un poco más para asegurar que todo esté cargado
                        content = await page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                    else:
                        # Último recurso: analizar la estructura de la página
                        print("[MSPAS Noticias_GT] ⚠️ No se encontraron selectores conocidos, analizando estructura de la página...")
                        
                        # Imprimir los primeros elementos principales para diagnóstico
                        print("[MSPAS Noticias_GT] Elementos principales encontrados:")
                        for i, elem in enumerate(soup.select("body > div, body > main, body > section")):
                            print(f"{i+1}. {elem.name}.{elem.get('class', [''])[0] if elem.get('class') else ''}")
                            if i >= 5:  # Solo mostrar los primeros 5 para no saturar la consola
                                break
                        
                        # Extraer manualmente a partir de claves comunes en titulares
                        noticias = []
                        posibles_titulos = soup.select("h1, h2, h3, h4, a.title, .title a, a[href*='noticia']")
                        
                        for elem in posibles_titulos:
                            if any(palabra in elem.text.lower() for palabra in ["salud", "ministerio", "covid", "comunicado"]):
                                noticias.append({"elemento": elem, "tipo": "título"})
                        
                        if not noticias:
                            print("[MSPAS Noticias_GT] ⚠️ No se pudo identificar la estructura de noticias.")
                            return []
                
                # Si encontramos un selector, obtener las noticias
                if found_selector and 'noticias' not in locals():
                    noticias = soup.select(found_selector)
            
            if not noticias:
                print("[MSPAS Noticias_GT] ⚠️ No se encontraron noticias.")
                return []

            items = []

            for noticia in noticias:
                try:
                    # Verificar si estamos trabajando con un elemento de identificación manual
                    if isinstance(noticia, dict) and noticia["tipo"] == "título":
                        elem = noticia["elemento"]
                        
                        # Obtener título
                        title = elem.text.strip()
                        
                        # Intentar obtener URL
                        if elem.name == "a":
                            noticia_url = elem["href"]
                        else:
                            link = elem.find_parent("a") or elem.find("a")
                            noticia_url = link["href"] if link else None
                        
                        # Formatear URL
                        if noticia_url and noticia_url.startswith("/"):
                            noticia_url = f"{base_url}{noticia_url}"
                        
                        # Buscar una fecha cercana (aproximación)
                        parent = elem.find_parent("div") or elem.find_parent("article")
                        fecha_element = parent.select_one("time, .date, .itemDateCreated, .published") if parent else None
                        fecha = _parse_date(fecha_element.text.strip()) if fecha_element else datetime.now().date()
                        
                        # Buscar descripción
                        descripcion_element = parent.select_one("p, .summary, .introtext") if parent else None
                        descripcion = descripcion_element.text.strip() if descripcion_element else title
                        
                        # Buscar imagen
                        img_element = parent.select_one("img") if parent else None
                        imagen_url = img_element["src"] if img_element and "src" in img_element.attrs else None
                        
                    else:
                        # Procesar con el selector encontrado
                        # Extraer título y URL (ajustar selectores según lo que encontremos)
                        link = noticia.select_one("h2 a, h3 a, h4 a, .title a, a.title") or noticia.select_one("a")
                        if not link:
                            continue
                        
                        title = link.text.strip()
                        noticia_url = link["href"]
                        noticia_url = f"{base_url}{noticia_url}" if noticia_url.startswith("/") else noticia_url

                        # Extraer fecha
                        fecha_element = noticia.select_one("time, .date, .itemDateCreated, .published, span.itemDateCreated")
                        fecha = _parse_date(fecha_element.text.strip()) if fecha_element else datetime.now().date()

                        # Extraer descripción
                        descripcion_element = noticia.select_one("div.itemIntroText p, .summary, .introtext, p") 
                        descripcion = descripcion_element.text.strip() if descripcion_element else title

                        # Extraer imagen
                        img_element = noticia.select_one("img")
                        imagen_url = img_element["src"] if img_element and "src" in img_element.attrs else None
                    
                    # Formatear URL de imagen si es relativa
                    if imagen_url and not imagen_url.startswith("http"):
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
                    print(f"[MSPAS Noticias_GT] ✅ Noticia procesada: {title[:100]}")

                except Exception as e:
                    print(f"[MSPAS Noticias_GT] ⚠️ Error procesando noticia: {str(e)}")
                    continue

            print(f"[MSPAS Noticias_GT] 🎯 Se encontraron {len(items)} noticias")
            return items

        except Exception as e:
            print(f"[MSPAS Noticias_GT] ❌ Error: {str(e)}")
        #     # Guardar captura de pantalla en caso de error
        #     try:
        #         os.makedirs("debug", exist_ok=True)
        #         await page.screenshot(path="debug/error_page.png")
        #         content = await page.content()
        #         with open("debug/error_page.html", "w", encoding="utf-8") as f:
        #             f.write(content)
        #         print("[MSPAS Noticias_GT] Se guardaron archivos de diagnóstico en la carpeta 'debug'")
        #     except:
        #         pass
        #     return []
        # finally:
        #     await browser.close()


def _parse_date(fecha_str):
    """
    Convierte fechas en español como "28 Enero 2025." a formato datetime.
    Si falla, usa la fecha actual.
    """
    try:
        fecha_str = fecha_str.replace(".", "").strip().lower()  # Normalizar
        
        # Convertir nombres de meses a números
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'sept': 9, 'octubre': 10, 
            'noviembre': 11, 'nov': 11, 'diciembre': 12, 'dic': 12
        }
        
        # Intentar varios formatos comunes
        # Formato: "28 Enero 2025"
        try:
            partes = fecha_str.split()
            if len(partes) >= 3:
                dia = int(''.join(filter(str.isdigit, partes[0])))
                for palabra in partes:
                    for mes_nombre, mes_num in meses.items():
                        if mes_nombre in palabra.lower():
                            mes = mes_num
                            break
                    else:
                        continue
                    break
                # Buscar el año (4 dígitos)
                anio = None
                for parte in partes:
                    numeros = ''.join(filter(str.isdigit, parte))
                    if len(numeros) == 4:
                        anio = int(numeros)
                        break
                
                # Si no encontramos un año de 4 dígitos, buscar cualquier número que pueda ser un año
                if anio is None:
                    for parte in partes:
                        numeros = ''.join(filter(str.isdigit, parte))
                        if numeros and int(numeros) > 2000:  # Asumimos años después de 2000
                            anio = int(numeros)
                            break
                
                # Si aún no tenemos año, usar el actual
                if anio is None:
                    anio = datetime.now().year
                
                return datetime(anio, mes, dia).date()
        except:
            pass
        
        # Si falla, intentar con formato ISO: "2025-01-28"
        try:
            return datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except:
            pass
        
        # Si todo falla
        print(f"[MSPAS Noticias_GT] ⚠️ No se pudo parsear la fecha '{fecha_str}', usando fecha actual.")
        return datetime.now().date()
        
    except Exception as e:
        print(f"[MSPAS Noticias_GT] ⚠️ Error procesando fecha '{fecha_str}', se usará la fecha actual: {e}")
        return datetime.now().date()


# async def debug_page_structure():
#     """Función auxiliar para analizar la estructura de la página"""
#     base_url = "https://www.mspas.gob.gt"
#     url = f"{base_url}/noticias-mspas"
    
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         context = await browser.new_context(
#             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
#         )
#         page = await context.new_page()
        
#         try:
#             await page.goto(url, timeout=90000)
#             await page.wait_for_load_state("networkidle", timeout=60000)
            
#             # Tomar una captura de pantalla
#             os.makedirs("debug", exist_ok=True)
#             await page.screenshot(path="debug/mspas_debug.png")
            
#             # Guardar HTML para análisis
#             content = await page.content()
#             with open("debug/mspas_debug.html", "w", encoding="utf-8") as f:
#                 f.write(content)
            
#             # Extraer y mostrar estructura básica
#             soup = BeautifulSoup(content, 'html.parser')
#             print("Estructura de la página:")
            
#             # Imprimir todos los elementos article
#             print("\nElementos article:")
#             for i, article in enumerate(soup.find_all("article")):
#                 class_attr = article.get("class", [])
#                 class_str = " ".join(class_attr) if class_attr else "sin clase"
#                 print(f"{i+1}. article.{class_str}")
            
#             # Imprimir todos los div que podrían contener noticias
#             print("\nPosibles contenedores de noticias:")
#             news_containers = soup.select("div.itemList, div.blog, div.news, div.noticias")
#             for i, container in enumerate(news_containers):
#                 class_attr = container.get("class", [])
#                 class_str = " ".join(class_attr) if class_attr else "sin clase"
#                 print(f"{i+1}. {container.name}.{class_str}")
            
#             # Imprimir elementos h2 y h3 (posibles títulos)
#             print("\nPosibles titulares:")
#             headings = soup.select("h1, h2, h3")
#             for i, heading in enumerate(headings[:10]):  # Limitamos a 10 para no saturar
#                 print(f"{i+1}. {heading.name}: {heading.text.strip()[:50]}")
                
#         except Exception as e:
#             print(f"Error en debug: {str(e)}")
#         finally:
#             await browser.close()


if __name__ == "__main__":
    # Primero ejecutamos el depurador para ver la estructura
    # asyncio.run(debug_page_structure())
    
    # Luego ejecutamos el scraper mejorado
    noticias = asyncio.run(scrape_minsalud_noti_gt())
    print(json.dumps([{
        **noticia,
        'presentation_date': noticia['presentation_date'].strftime('%Y-%m-%d') if noticia['presentation_date'] else None
    } for noticia in noticias], indent=4, ensure_ascii=False))