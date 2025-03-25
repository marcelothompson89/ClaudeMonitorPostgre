import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_invima_noticias_co():
    """
    Scraper para la página de noticias del INVIMA.
    """
    url = "https://www.invima.gov.co/sala-de-prensa/noticias"
    items = []

    async with httpx.AsyncClient() as client:
        try:
            # Realizar la solicitud HTTP
            response = await client.get(url)
            if response.status_code != 200:
                print(f"Error: No se pudo acceder a la página. Código {response.status_code}")
                return []

            # Parsear el HTML de la página
            soup = BeautifulSoup(response.text, "html.parser")

            # Seleccionar los contenedores de noticias
            noticias = soup.select(".views-row .row.view-content-sala-prensa")

            for noticia in noticias:
                try:
                    # Extraer enlace
                    enlace_element = noticia.find("a", hreflang="es")
                    url_completa = f"https://www.invima.gov.co{enlace_element['href']}" if enlace_element else None

                    # Extraer título
                    titulo_element = noticia.select_one(".view-content-sala-prensa__title a")
                    titulo = titulo_element.get_text(strip=True) if titulo_element else "Sin Título"

                    # Extraer descripción
                    descripcion_element = noticia.select_one(".view-content-sala-prensa__body")
                    descripcion = descripcion_element.get_text(strip=True) if descripcion_element else "Sin Descripción"

                    # Extraer fecha
                    fecha_element = noticia.find("time", class_="datetime")
                    fecha_publicacion = None
                    if fecha_element and fecha_element.has_attr("datetime"):
                        fecha_publicacion = datetime.fromisoformat(fecha_element["datetime"].replace("Z", ""))

                    # Extraer imagen
                    imagen_element = noticia.find("img", class_="img-fluid")
                    imagen_url = f"https://www.invima.gov.co{imagen_element['src']}" if imagen_element else None

                    # Extraer etiqueta o categoría
                    etiqueta_element = noticia.select_one(".view-content-sala-prensa__tag")
                    etiqueta = etiqueta_element.get_text(strip=True) if etiqueta_element else "Sin Categoría"

                    # Crear el diccionario del item
                    item = {
                        'title': titulo,
                        'description': descripcion,
                        'source_type': "Ejecutivo",
                        'category': "Noticias",
                        'country': "Colombia",
                        'source_url': url_completa,
                        'presentation_date': fecha_publicacion,
                        'metadata': {
                            'image_url': imagen_url
                        },
                        'institution': "INVIMA Colombia"
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando una noticia: {e}")

        except Exception as e:
            print(f"Error al realizar la solicitud: {e}")
            return []

    return items


# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados
#     items = asyncio.run(scrape_invima_noticias())

#     # Formatear salida como JSON
#     print(json.dumps([{
#         **item,
#         'presentation_date': item['presentation_date'].strftime('%Y-%m-%d') if item['presentation_date'] else None
#     } for item in items], indent=4, ensure_ascii=False))
