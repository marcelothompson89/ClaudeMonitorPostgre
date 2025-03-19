import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from datetime import datetime
import json

async def scrape_camara_proyectos_co():
    """
    Scraper para la página de proyectos de ley de la Cámara de Representantes de Colombia.
    """
    base_url = "https://www.camara.gov.co"
    items = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navegar a la página
            await page.goto("https://www.camara.gov.co/secretaria/proyectos-de-ley#menu", timeout=60000)

            # Esperar a que la tabla se cargue
            await page.wait_for_selector('.table.cols-9', timeout=60000)

            # Extraer el contenido HTML de la página
            html_content = await page.content()
            soup = BeautifulSoup(html_content, "html.parser")

            # Buscar filas de la tabla
            tabla = soup.find("table", class_="table cols-9")
            filas = tabla.find_all("tr", class_="tablacomispro") if tabla else []

            for fila in filas:
                try:
                    # Extraer columnas de la fila
                    columnas = fila.find_all("td")

                    if not columnas or len(columnas) < 9:
                        continue

                    # A) Datos principales
                    numero_camara = columnas[0].get_text(strip=True)
                    numero_senado = columnas[1].get_text(strip=True)
                    proyecto = columnas[2].find("a").get_text(strip=True)
                    proyecto_url_relativo = columnas[2].find("a")["href"]
                    proyecto_url = base_url + proyecto_url_relativo  # Convertir a URL absoluto
                    tipo = columnas[3].get_text(strip=True)
                    autores = columnas[4].get_text(strip=True)
                    estado = columnas[5].get_text(strip=True)
                    comision = columnas[6].get_text(strip=True)
                    origen = columnas[7].get_text(strip=True)
                    legislatura = columnas[8].get_text(strip=True)

                    # Crear el diccionario del item
                    item = {
                        'title': proyecto,
                        'description': (
                            f"Tipo: {tipo}\n"
                            f"Autores: {autores}\n"
                            f"Estado: {estado}\n"
                            f"Comisión: {comision}\n"
                            f"Origen: {origen}\n"
                            f"Legislatura: {legislatura}"
                        ),
                        'source_type': "Proyectos de Ley",
                        'category': "Legislación",
                        'country': "Colombia",
                        'source_url': proyecto_url,  # URL absoluto
                        'presentation_date': _parse_date(legislatura),
                        'metadata': {
                            'numero_camara': numero_camara,
                            'numero_senado': numero_senado
                        },
                        'institution': "Cámara de Representantes"
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando una fila: {e}")

        except Exception as e:
            print(f"Error al navegar o procesar la página: {e}")
        finally:
            await browser.close()

    return items


def _parse_date(periodo_legislativo):
    """
    Parsear el periodo legislativo (e.g., "2024 - 2025") a un objeto datetime con solo el año inicial.
    """
    if not periodo_legislativo:
        return None
    try:
        # Extraer el primer año del rango legislativo
        year = periodo_legislativo.split("-")[0].strip()
        return datetime.strptime(year, "%Y")
    except ValueError:
        return None


# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados
#     items = asyncio.run(scrape_camara_proyectos())

#     # Formatear salida como JSON
#     print(json.dumps([{
#         **item,
#         'presentation_date': item['presentation_date'].strftime('%Y-%m-%d') if item['presentation_date'] else None
#     } for item in items], indent=4, ensure_ascii=False))
