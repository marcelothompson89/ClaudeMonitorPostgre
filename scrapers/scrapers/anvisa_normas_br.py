import asyncio
from datetime import datetime
import json
import time
from urllib.parse import urlparse, parse_qs, unquote_plus
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

async def scrape_anvisa_normas_br():
    print("[ANVISA_Normas] Iniciando scraping...")
    
    # 1) Configurar Chrome en headless
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    # 2) Iniciar driver
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    driver.set_page_load_timeout(60)
    
    url = (
        "https://anvisalegis.datalegis.net/action/ActionDatalegis.php"
        "?acao=consultarAtosInicial&cod_modulo=310&cod_menu=9434"
    )
    print(f"[ANVISA_Normas] Accediendo a URL: {url}")
    
    # 3) Cargar página con reintentos
    for intento in range(3):
        try:
            driver.get(url)
            break
        except Exception as e:
            print(f"[ANVISA_Normas] Error al cargar (intento {intento+1}): {e}")
            time.sleep(5)
    else:
        print("[ANVISA_Normas] No se pudo cargar la página.")
        driver.quit()
        return []
    
    wait = WebDriverWait(driver, 30)
    
    # 4) Hacer clic en “Pesquisar”
    boton = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "button[name='pesquisar']")
    ))
    boton.click()
    
    # 5) Esperar resultados
    atos = wait.until(EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, "#divAtosLegislacao .ato")
    ))
    print(f"[ANVISA_Normas] Encontrados {len(atos)} atos.")
    
    items = []
    for idx, ato in enumerate(atos, 1):
        try:
            a_tag = ato.find_element(By.TAG_NAME, "a")
            href  = a_tag.get_attribute("href").strip()
            titulo = a_tag.find_element(By.TAG_NAME, "strong").text.strip()
            descripcion = a_tag.find_element(By.TAG_NAME, "p").text.strip()
            
            # 6) Extraer parámetros de la URL
            qs = parse_qs(urlparse(href).query)
            tipo    = qs.get("tipo", [""])[0]
            numero  = qs.get("numeroAto", [""])[0]
            seq     = qs.get("seqAto", [""])[0]
            ano     = qs.get("valorAno", [""])[0]
            orgao   = unquote_plus(qs.get("orgao", [""])[0])
            
            # 7) Parsear fecha del título (busca “de DD/MM/YYYY”)
            from re import search
            m = search(r"de (\d{2}/\d{2}/\d{4})", titulo)
            if m:
                fecha = datetime.strptime(m.group(1), "%d/%m/%Y")
            else:
                fecha = None
            
            # 8) Construir el item
            item = {
                "title": titulo,
                "description": descripcion,
                "source_url": href,
                "source_type": "Ejecutivo",
                "country": "Brasil",
                "category": "Normas",
                "presentation_date": fecha,
                "institution": "ANVISA Brasil",
                "metadata": json.dumps({
                    "tipo": tipo,
                    "numeroAto": numero,
                    "seqAto": seq,
                    "valorAno": ano,
                    "orgao": orgao
                }, ensure_ascii=False)
            }
            
            items.append(item)
            print(f"[ANVISA_Normas] {idx}. Extraído: {titulo}")
        
        except Exception as e:
            print(f"[ANVISA_Normas] Error procesando ato #{idx}: {e}")
            continue
    
    driver.quit()
    print(f"[ANVISA_Normas] Scraping completado. Total items: {len(items)}")
    return items

#Para ejecutar directamente y ver resultados:
if __name__ == "__main__":
    resultados = asyncio.run(scrape_anvisa_normas_br())
    for itm in resultados:
        fecha = itm["presentation_date"].strftime("%Y-%m-%d") if itm["presentation_date"] else "N/A"
        print(f"{fecha} - {itm['title']} → {itm['source_url']}")
