from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
import json
from datetime import datetime


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

            for aviso in avisos:
                try:
                    # A) Extraer título
                    titulo = aviso.select_one(".item").get_text(strip=True) if aviso.select_one(".item") else "Sin título"

                    # B) Extraer detalles
                    detalles = [det.get_text(strip=True) for det in aviso.select(".item-detalle")]
                    descripcion = "\n".join(detalles) if detalles else "Sin descripción"

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

                    # Crear objeto en el formato esperado
                    item = {
                        'title': titulo,
                        'description': descripcion,
                        'source_url': source_url,
                        'source_type': "Boletín Oficial Argentina",
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


# if __name__ == "__main__":
#     # Ejecutar el scraper de forma asíncrona
#     items = asyncio.run(scrape_boletin_oficial())

#     # Formatear salida como JSON para visualizar los datos
#     print(json.dumps(items, indent=4, default=str, ensure_ascii=False))
