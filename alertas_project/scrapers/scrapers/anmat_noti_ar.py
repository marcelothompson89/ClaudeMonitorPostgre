import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import re
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

# Para pruebas directas
if __name__ == "__main__":
    import json
    items = asyncio.run(scrape_anmat_noti_ar())
    # Formatear salida como JSON
    print(json.dumps([{
        **item,
        'presentation_date': item['presentation_date'].strftime('%Y-%m-%d') if item['presentation_date'] else None
    } for item in items], indent=4, ensure_ascii=False))

async def scrape_anmat_noti_ar():
    """
    Scraper para la página de noticias de Argentina.
    """
    url = "https://www.argentina.gob.ar/node/28874/noticias?nodo=28874"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        try:
            # Intentar realizar la solicitud con reintentos
            for intento in range(3):
                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    break
                except httpx.RequestError as e:
                    logger.error(f"Error en el intento {intento + 1}: {e}")
            else:
                logger.error("Todos los intentos fallaron. Abortando.")
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            # Seleccionar los contenedores de noticias
            noticias = soup.select(".col-xs-12.col-sm-3")
            items = []

            for noticia in noticias:
                try:
                    # Extraer enlace
                    enlace = noticia.find("a")["href"]
                    url_completa = f"https://www.argentina.gob.ar{enlace}"

                    # Extraer título
                    titulo = noticia.find("h3").get_text(strip=True)

                    # Extraer descripción
                    descripcion = noticia.find("p").get_text(strip=True)

                    # Extraer fecha
                    fecha_element = noticia.find("time")
                    fecha_publicacion = None
                    if fecha_element and fecha_element.has_attr("datetime"):
                        fecha_naive = datetime.fromisoformat(fecha_element["datetime"])
                        fecha_publicacion = timezone.make_aware(fecha_naive)    

                    # Extraer imagen (como metadato adicional)
                    imagen_style = noticia.find("div", class_="panel-heading")["style"]
                    imagen_url = None
                    if "background-image" in imagen_style:
                        imagen_url = imagen_style.split("url(")[1].split(")")[0]

                    # Crear el diccionario del item
                    item = {
                        'title': titulo,
                        'description': descripcion,
                        'source_type': "Ejecutivo",
                        'category': "Noticias",
                        'country': "Argentina",
                        'source_url': url_completa,
                        'presentation_date': fecha_publicacion,
                        'metadata': {
                            'image_url': imagen_url
                        },
                        'institution': "ANMAT Argentina"
                    }
                    items.append(item)

                except Exception as e:
                    logger.error(f"Error procesando una noticia: {e}")

            return items

        except Exception as e:
            logger.error(f"Error general: {e}")
            return []