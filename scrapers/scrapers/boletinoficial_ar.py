from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
import json
from datetime import datetime


async def obtener_detalle_aviso(page, url):
    """
    Función para obtener el detalle completo de un aviso específico.
    
    Args:
        page: Instancia de página de Playwright
        url: URL del aviso a extraer
        
    Returns:
        str: Texto del detalle del aviso
    """
    try:
        # Navegar a la URL del aviso
        await page.goto(url, timeout=60000)
        
        # Esperar a que se cargue el contenedor con el detalle
        await page.wait_for_selector('#cuerpoDetalleAviso', timeout=60000)
        
        # Extraer el contenido HTML del detalle
        html_content = await page.content()
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extraer título y cuerpo del aviso
        titulo_element = soup.select_one("#tituloDetalleAviso h1")
        cuerpo_element = soup.select_one("#cuerpoDetalleAviso")
        
        titulo = titulo_element.get_text(strip=True) if titulo_element else "Sin título"
        
        # Extraer texto completo del cuerpo, preservando algunos elementos HTML básicos como párrafos
        if cuerpo_element:
            # Obtener todo el texto plano, eliminando scripts y estilos
            for script in cuerpo_element.find_all(["script", "style"]):
                script.decompose()
                
            # Obtener el texto preservando saltos de párrafo
            parrafos = cuerpo_element.find_all('p')
            if parrafos:
                texto_cuerpo = "\n".join([p.get_text(strip=True) for p in parrafos if p.get_text(strip=True)])
            else:
                texto_cuerpo = cuerpo_element.get_text(strip=True)
        else:
            texto_cuerpo = "Sin contenido"
            
        return f"{titulo}\n\n{texto_cuerpo}"
    
    except Exception as e:
        print(f"Error obteniendo detalle del aviso {url}: {e}")
        return "Error obteniendo detalle"


async def scrape_boletin_oficial_ar():
    """
    Scraper para el Boletín Oficial de Argentina utilizando Playwright.
    """
    url = "https://www.boletinoficial.gob.ar/busquedaAvanzada/primera"
    items = []

    async with async_playwright() as p:
        # Lanzar navegador en modo headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navegar a la página
            await page.goto(url)

            # Completar el campo "Fecha Desde"
            fecha_actual = datetime.now().strftime("%d/%m/%Y")
            await page.fill('#fechaDesdeInput', fecha_actual)

            # Intentar cerrar elementos superpuestos (por ejemplo, selectores de fecha)
            await page.evaluate("""
                () => {
                    const datepickerModal = document.querySelector('.datepicker-switch');
                    if (datepickerModal) {
                        datepickerModal.click();
                    }
                }
            """)

            # Forzar el clic en el botón de búsqueda
            print("Haciendo clic en el botón de búsqueda...")
            await page.evaluate("""
                (selector) => {
                    const element = document.querySelector(selector);
                    if (element) {
                        element.click();
                    }
                }
            """, "#btnBusquedaAvanzada")

            # Esperar a que se cargue el contenedor con los resultados
            await page.wait_for_selector('#avisosSeccionDiv .linea-aviso', timeout=60000)

            # Extraer el contenido HTML de los resultados
            html_content = await page.content()
            soup = BeautifulSoup(html_content, "html.parser")

            # Extraer información de los avisos
            avisos = soup.select("#avisosSeccionDiv .linea-aviso")
            
            print(f"Se encontraron {len(avisos)} avisos.")

            for i, aviso in enumerate(avisos):
                try:
                    # A) Extraer título
                    titulo = aviso.select_one(".item").get_text(strip=True) if aviso.select_one(".item") else "Sin título"

                    # B) Extraer detalles básicos (se mantendrán como metadatos)
                    detalles = [det.get_text(strip=True) for det in aviso.select(".item-detalle")]
                    metadatos = "\n".join(detalles) if detalles else "Sin metadatos"

                    # C) Extraer URL del documento
                    enlace = aviso.find_parent("a")["href"] if aviso.find_parent("a") else None
                    source_url = f"https://www.boletinoficial.gob.ar{enlace}" if enlace else None

                    # D) Extraer fecha de publicación
                    fecha_publicacion = None
                    for detalle in detalles:
                        if "Fecha de Publicacion:" in detalle:
                            try:
                                fecha_publicacion = datetime.strptime(detalle.split(":")[1].strip(), "%d/%m/%Y").date()
                            except ValueError:
                                fecha_publicacion = None
                            break
                    
                    # E) NUEVO: Obtener detalle completo del aviso
                    descripcion = "Sin descripción"
                    if source_url:
                        print(f"Obteniendo detalle del aviso {i+1}/{len(avisos)}: {source_url}")
                        descripcion = await obtener_detalle_aviso(page, source_url)

                    # Crear objeto en el formato esperado
                    item = {
                        'title': titulo,
                        'description': descripcion,  # Ahora contiene el detalle completo
                        'metadata': metadatos,  # Guardamos los metadatos originales
                        'source_url': source_url,
                        'source_type': "Ejecutivo",
                        'category': "Normas",
                        'country': "Argentina",
                        'institution': "Boletín Oficial Argentina",
                        'presentation_date': fecha_publicacion,
                    }

                    items.append(item)

                except Exception as e:
                    print(f"Error procesando aviso: {e}")

        except Exception as e:
            print(f"Error durante la ejecución del scraper: {e}")

        finally:
            await browser.close()

    return items


async def main():
    """Función principal para ejecutar el scraper y mostrar el resultado."""
    print("Iniciando scraper del Boletín Oficial de Argentina...")
    items = await scrape_boletin_oficial_ar()
    
    # Formatear salida como JSON para visualizar los datos
    print(f"Se obtuvieron {len(items)} avisos.")
    print(json.dumps(items, indent=4, default=str, ensure_ascii=False))


if __name__ == "__main__":
    # Ejecutar el scraper de forma asíncrona
    asyncio.run(main())