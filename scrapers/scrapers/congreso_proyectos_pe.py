import asyncio
from datetime import datetime
import json
import time
import os
import platform
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

async def scrape_congreso_proyectos_pe():
    print("[Congreso Proyectos_PE] Iniciando scraping...")
    
    # Configurar opciones de Chrome
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')  # Nueva sintaxis para headless
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        # Utilizar webdriver_manager para gestionar automáticamente el ChromeDriver
        print("[Congreso Proyectos_PE] Configurando ChromeDriver automáticamente...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        driver.set_page_load_timeout(60)  # Aumentar timeout para carga de página
        
        url = "https://wb2server.congreso.gob.pe/spley-portal/#/expediente/search"
        print(f"[Congreso Proyectos_PE] Accediendo a URL: {url}")
        
        # Cargar la página con reintentos
        max_retries = 3
        for attempt in range(max_retries):
            try:
                driver.get(url)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[Congreso Proyectos_PE] Reintento {attempt+1}/{max_retries} al cargar la página: {str(e)}")
                    time.sleep(5)
                else:
                    print(f"[Congreso Proyectos_PE] Error al cargar la página después de {max_retries} intentos: {str(e)}")
                    return []
        
        wait = WebDriverWait(driver, 30)
        
        # Esperar a que se cargue la SPA
        print("[Congreso Proyectos_PE] Esperando que cargue la página...")
        time.sleep(15)  # Aumentar tiempo de espera para SPAs lentas
        
        # Capturar screenshot para debugging
        # try:
        #     screenshot_path = "debug_screenshot.png"
        #     driver.save_screenshot(screenshot_path)
        #     print(f"[Congreso Proyectos_PE] Screenshot guardado en: {os.path.abspath(screenshot_path)}")
        # except Exception as e:
        #     print(f"[Congreso Proyectos_PE] No se pudo guardar screenshot: {str(e)}")
        
        # Obtener y mostrar el HTML de la página
        print("[Congreso Proyectos_PE] Obteniendo HTML de la página...")
        page_source = driver.page_source
        print(f"[Congreso Proyectos_PE] Tamaño del HTML: {len(page_source)} caracteres")
        print(f"[Congreso Proyectos_PE] Fragmento del HTML: {page_source[:300]}...")
        
        try:
            # Intentar múltiples selectores para encontrar la tabla
            selectors = [
                "table.mat-table",
                "table",
                ".mat-table-container table",
                "[role='grid']",
                ".mat-mdc-table",
                ".mat-table"
            ]
            
            table = None
            for selector in selectors:
                try:
                    print(f"[Congreso Proyectos_PE] Intentando selector: {selector}")
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        table = elements[0]
                        print(f"[Congreso Proyectos_PE] Tabla encontrada con selector: {selector}")
                        break
                except Exception as e:
                    print(f"[Congreso Proyectos_PE] Error con selector {selector}: {str(e)}")
                    continue
            
            if not table:
                print("[Congreso Proyectos_PE] No se encontró la tabla principal")
                
                # Buscar cualquier elemento visible para verificar que la página cargó
                visible_elements = driver.find_elements(By.CSS_SELECTOR, 'body *')
                print(f"[Congreso Proyectos_PE] Total de elementos visibles en la página: {len(visible_elements)}")
                
                # Mostrar algunos elementos importantes que puedan existir
                important_selectors = ["h1", "h2", ".mat-card", ".container", "[role='main']"]
                for sel in important_selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, sel)
                    if elements:
                        print(f"[Congreso Proyectos_PE] Encontrados {len(elements)} elementos '{sel}'")
                        for i, el in enumerate(elements[:3]):
                            print(f"[Congreso Proyectos_PE] {sel} #{i+1}: {el.text[:100]}")
                
                return []
            
            # Imprimir el HTML para debug
            print("[Congreso Proyectos_PE] HTML de la tabla:")
            print(table.get_attribute('outerHTML')[:500])
            
        except Exception as e:
            print(f"[Congreso Proyectos_PE] Error buscando la tabla: {str(e)}")
            return []
        
        # Esperar a que se carguen los datos
        time.sleep(5)
        
        # Buscar filas de proyectos con múltiples selectores
        rows = []
        row_selectors = [
            "tr.mat-row",
            "tr[role='row']",
            "tr.ng-star-inserted",
            "tbody tr",
            ".mat-mdc-row"
        ]
        
        for selector in row_selectors:
            try:
                rows = driver.find_elements(By.CSS_SELECTOR, selector)
                if rows:
                    print(f"[Congreso Proyectos_PE] Encontradas {len(rows)} filas con selector {selector}")
                    break
            except Exception as e:
                print(f"[Congreso Proyectos_PE] Error con selector de filas {selector}: {str(e)}")
        
        if not rows:
            print("[Congreso Proyectos_PE] No se encontraron proyectos")
            return []
        
        items = []
        for idx, row in enumerate(rows[:20]):  # Limitar a 20 filas para pruebas
            try:
                print(f"[Congreso Proyectos_PE] Procesando fila {idx+1}/{len(rows)}")
                
                # Mostrar HTML de la fila para debugging
                row_html = row.get_attribute('outerHTML')
                print(f"[Congreso Proyectos_PE] HTML de la fila {idx+1}: {row_html[:300]}...")
                
                # Extraer datos básicos con múltiples intentos
                link = None
                link_selectors = [
                    "a.link-proyecto-acumulado",
                    "a[target='_blank']",
                    "a"
                ]
                
                for selector in link_selectors:
                    try:
                        links = row.find_elements(By.CSS_SELECTOR, selector)
                        if links:
                            link = links[0]
                            print(f"[Congreso Proyectos_PE] Link encontrado con selector {selector}: {link.text}")
                            break
                    except Exception as e:
                        print(f"[Congreso Proyectos_PE] Error buscando link con selector {selector}: {str(e)}")
                
                if not link:
                    print("[Congreso Proyectos_PE] No se encontró el link del proyecto")
                    continue
                
                numero = link.text.strip()
                href = link.get_attribute("href")
                
                # Extraer otros campos
                cells = row.find_elements(By.TAG_NAME, "td")
                print(f"[Congreso Proyectos_PE] Número de celdas encontradas: {len(cells)}")
                
                if len(cells) < 4:  # Mínimo de celdas esperadas
                    print(f"[Congreso Proyectos_PE] Fila no tiene suficientes columnas: {len(cells)}")
                    continue
                
                # Intentar extraer datos con manejo de errores para cada campo
                try:
                    fecha_str = cells[1].text.strip() if len(cells) > 1 else ""
                    print(f"[Congreso Proyectos_PE] Fecha extraída: {fecha_str}")
                except Exception as e:
                    print(f"[Congreso Proyectos_PE] Error extrayendo fecha: {str(e)}")
                    fecha_str = ""
                
                try:
                    titulo_element = cells[2].find_elements(By.CSS_SELECTOR, "span.ellipsis") if len(cells) > 2 else []
                    titulo = titulo_element[0].text.strip() if titulo_element else cells[2].text.strip() if len(cells) > 2 else "Sin título"
                    print(f"[Congreso Proyectos_PE] Título extraído: {titulo[:50]}...")
                except Exception as e:
                    print(f"[Congreso Proyectos_PE] Error extrayendo título: {str(e)}")
                    titulo = "Sin título"
                
                try:
                    estado = cells[3].text.strip() if len(cells) > 3 else "Desconocido"
                    print(f"[Congreso Proyectos_PE] Estado extraído: {estado}")
                except Exception as e:
                    print(f"[Congreso Proyectos_PE] Error extrayendo estado: {str(e)}")
                    estado = "Desconocido"
                
                try:
                    proponente = cells[4].text.strip() if len(cells) > 4 else "Desconocido"
                    print(f"[Congreso Proyectos_PE] Proponente extraído: {proponente}")
                except Exception as e:
                    print(f"[Congreso Proyectos_PE] Error extrayendo proponente: {str(e)}")
                    proponente = "Desconocido"
                
                # Extraer autores
                autores = []
                if len(cells) > 5:
                    try:
                        autores_uls = cells[5].find_elements(By.TAG_NAME, "ul")
                        if autores_uls:
                            autores_li = autores_uls[0].find_elements(By.TAG_NAME, "li")
                            for autor_li in autores_li:
                                autor_text = autor_li.text.replace("ver más...", "").strip()
                                if autor_text:
                                    autores.append(autor_text)
                        else:
                            # Si no hay lista, intentar extraer texto plano
                            autor_text = cells[5].text.strip()
                            if autor_text and autor_text != "":
                                autores.append(autor_text)
                        
                        print(f"[Congreso Proyectos_PE] Autores extraídos: {len(autores)}")
                    except Exception as e:
                        print(f"[Congreso Proyectos_PE] Error extrayendo autores: {str(e)}")
                
                # Convertir fecha
                try:
                    if fecha_str and fecha_str != "":
                        fecha = datetime.strptime(fecha_str, '%d/%m/%Y')
                    else:
                        fecha = datetime.now()
                except ValueError:
                    print(f"[Congreso Proyectos_PE] Error procesando fecha: {fecha_str}")
                    fecha = datetime.now()
                
                # Construir descripción con autores
                autores_str = ", ".join(autores[:3])
                if len(autores) > 3:
                    autores_str += f" y {len(autores)-3} más"
                elif not autores:
                    autores_str = "No especificados"
                
                item = {
                    "title": titulo,
                    "description": f"Proyecto de Ley N° {numero} - Estado: {estado} - Proponente: {proponente}\nAutores: {autores_str}",
                    "source_url": href,
                    "source_type": "Legislativo",
                    "country": "Perú",
                    "category": "Proyecto de Ley",
                    "presentation_date": fecha,
                    "institution": "Congreso Perú",
                    "metadata": json.dumps({
                        "numero_expediente": numero,
                        "estado": estado,
                        "proponente": proponente,
                        "autores": autores,
                        "periodo": "2021-2026"
                    })
                }
                items.append(item)
                print(f"[Congreso Proyectos_PE] Proyecto procesado: {numero}")
                
            except Exception as e:
                print(f"[Congreso Proyectos_PE] Error procesando proyecto: {str(e)}")
                continue
        
        print(f"[Congreso Proyectos_PE] Se encontraron {len(items)} proyectos")
        return items
        
    except Exception as e:
        print(f"[Congreso Proyectos_PE] Error general: {str(e)}")
        return []
        
    finally:
        try:
            driver.quit()
            print("[Congreso Proyectos_PE] Navegador cerrado")
        except:
            pass

# # Para ejecutar directamente
# if __name__ == "__main__":
#     items = asyncio.run(scrape_congreso_proyectos_pe())
    
#     # Imprimir resultados en formato JSON
#     if items:
#         formatted_items = [
#             {
#                 **item,
#                 'presentation_date': item['presentation_date'].strftime('%Y-%m-%d %H:%M:%S') 
#                     if isinstance(item['presentation_date'], datetime) else None
#             }
#             for item in items
#         ]
        
#         print(json.dumps(formatted_items, indent=4, ensure_ascii=False))
#     else:
#         print("No se encontraron proyectos para mostrar.")