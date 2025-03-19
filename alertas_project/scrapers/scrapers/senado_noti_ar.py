import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_senado_noti_ar():
    """
    Scraper para la página de eventos del Senado de la Nación Argentina.
    """
    url = "https://www.senado.gob.ar/prensa/eventos"
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

            # Seleccionar los contenedores de eventos
            eventos = soup.select(".row")

            for evento in eventos:
                try:
                    # Extraer enlace
                    enlace = evento.find("a")["href"]
                    url_completa = f"https://www.senado.gob.ar{enlace}"

                    # Extraer título
                    titulo_element = evento.find("h1")
                    titulo = titulo_element.get_text(strip=True) if titulo_element else "Sin Título"

                    # Extraer fecha
                    fecha_element = evento.find("span", class_="meta-data")
                    fecha_publicacion = None
                    if fecha_element:
                        fecha_publicacion = datetime.strptime(fecha_element.get_text(strip=True), "%d/%m/%Y")

                    # Extraer imagen
                    imagen_element = evento.find("img")
                    imagen_url = None
                    if imagen_element and "src" in imagen_element.attrs:
                        imagen_url = f"https://www.senado.gob.ar{imagen_element['src']}"

                    # Crear el diccionario del item
                    item = {
                        'title': titulo,
                        'description': titulo,  # En este caso la descripción es el mismo título
                        'source_type': "Senado de la Nación Argentina",
                        'category': "Noticias",
                        'country': "Argentina",
                        'source_url': url_completa,
                        'presentation_date': fecha_publicacion,
                        'metadata': {
                            'image_url': imagen_url
                        },
                        'institution': "Senado de la Nación Argentina"
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando un evento: {e}")

        except Exception as e:
            print(f"Error al realizar la solicitud: {e}")
            return []

    return items


# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados
#     items = asyncio.run(scrape_senado_eventos())

#     # Formatear salida como JSON
#     print(json.dumps([{
#         **item,
#         'presentation_date': item['presentation_date'].strftime('%Y-%m-%d') if item['presentation_date'] else None
#     } for item in items], indent=4, ensure_ascii=False))
