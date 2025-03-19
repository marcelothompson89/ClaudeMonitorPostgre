import asyncio
import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager  # Importar webdriver-manager

def extract_date_from_text(date_text, year="2025"):
    """ Convierte una fecha tipo '8 de enero' en un objeto datetime.date. """
    meses = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
    }

    match = re.search(r"(\d{1,2}) de (\w+)", date_text, re.IGNORECASE)
    if match:
        day, month_text = match.groups()
        month = meses.get(month_text.lower())
        if month:
            try:
                return datetime.strptime(f"{year}-{month}-{int(day):02d}", "%Y-%m-%d").date()
            except ValueError:
                return None
    
    return None  # Retorna None si no encuentra una fecha válida

async def scrape_minsalud_resoluciones_co():
    """Scraper para extraer resoluciones de 2025 de la web de Minsalud Colombia."""
    print("[Minsalud_Resoluciones_CO] Iniciando scraping...")

    # Configuración de Selenium con Chrome
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # Usar WebDriver Manager para obtener la versión correcta de ChromeDriver
    service = Service(ChromeDriverManager().install())

    driver = None  # Inicializar driver antes del try para evitar errores

    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)

        url = "https://www.minsalud.gov.co/Paginas/Norm_Resoluciones.aspx"
        print(f"[Minsalud_Resoluciones_CO] Accediendo a URL: {url}")

        driver.get(url)
        wait = WebDriverWait(driver, 30)

        print("[Minsalud_Resoluciones_CO] Esperando que cargue la página...")
        time.sleep(5)

        # Buscar todos los botones de expandir
        expand_buttons = driver.find_elements(By.CSS_SELECTOR, "img[alt='expandir']")
        
        if not expand_buttons:
            print("[Minsalud_Resoluciones_CO] No se encontraron botones de expansión.")
            return []

        print(f"[Minsalud_Resoluciones_CO] Se encontraron {len(expand_buttons)} botones de expansión.")

        expand_button = None
        for button in expand_buttons:
            try:
                parent_row = button.find_element(By.XPATH, "./ancestor::tr")
                if "2025" in parent_row.text:
                    expand_button = button
                    break
            except:
                continue

        if not expand_button:
            print("[Minsalud_Resoluciones_CO] No se encontró el botón de expansión para 2025.")
            return []

        print("[Minsalud_Resoluciones_CO] Desplazando al botón y haciendo clic para expandir 2025...")
        driver.execute_script("arguments[0].scrollIntoView(true);", expand_button)
        time.sleep(1)

        try:
            driver.execute_script("arguments[0].click();", expand_button)
            wait.until(lambda driver: expand_button.get_attribute("alt") == "contraer")
            print("[Minsalud_Resoluciones_CO] Sección 2025 expandida correctamente.")
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", expand_button)
            time.sleep(2)

        # Esperar hasta que el tbody se cargue
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody[isloaded='true']")))
            time.sleep(2)
        except TimeoutException:
            print("[Minsalud_Resoluciones_CO] Timeout esperando que el tbody cargue.")

        tbody_2025 = None
        tbodies = driver.find_elements(By.CSS_SELECTOR, "tbody[isloaded='true']")
        for tbody in tbodies:
            rows = tbody.find_elements(By.TAG_NAME, "tr")
            if rows and "2025" in rows[0].text:
                tbody_2025 = tbody
                break

        if not tbody_2025:
            print("[Minsalud_Resoluciones_CO] No se encontró el tbody de 2025.")
            return []

        # Extraer datos
        items = []
        rows = tbody_2025.find_elements(By.TAG_NAME, "tr")

        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 6:
                    continue

                year = cells[1].text.strip()
                title = cells[2].text.strip()
                link_element = cells[2].find_element(By.TAG_NAME, "a") if cells[2].find_elements(By.TAG_NAME, "a") else None
                url = link_element.get_attribute("href") if link_element else None
                description = cells[3].text.strip()
                category = cells[4].text.strip()
                date_text = cells[5].text.strip()

                extracted_date = extract_date_from_text(date_text)

                item = {
                    "title": title,
                    "description": f"Resolución {year} - {description}",
                    "source_url": url,
                    "source_type": "Ministerio Salud Resoluciones Colombia",
                    "country": "Colombia",
                    "category": "Resoluciones",
                    "presentation_date": extracted_date,
                    "institution": "Ministerio Salud Colombia",
                    "metadata": json.dumps({"año": year, "categoría": category})
                }

                items.append(item)

            except Exception as e:
                print(f"[Minsalud_Resoluciones_CO] Error procesando resolución: {str(e)}")
                continue

        print(f"[Minsalud_Resoluciones_CO] Se encontraron {len(items)} resoluciones")
        return items

    finally:
        if driver:
            driver.quit()
            print("[Minsalud_Resoluciones_CO] Navegador cerrado")

# if __name__ == "__main__":
#     items = asyncio.run(scrape_minsalud_resoluciones())
    
#     # Convertir objetos date a string en formato "YYYY-MM-DD"
#     json_output = json.dumps(
#         [{**item, "presentation_date": item["presentation_date"].strftime("%Y-%m-%d") if item["presentation_date"] else None}
#          for item in items], 
#         indent=4, 
#         ensure_ascii=False
#     )
    
#     print(json_output)

