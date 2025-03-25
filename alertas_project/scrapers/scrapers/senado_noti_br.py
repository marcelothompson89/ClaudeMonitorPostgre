import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import json


async def scrape_senado_noticias_br():
    """
    Scraper para la página de noticias del Senado de Brasil.
    """
    url = "https://www12.senado.leg.br/noticias/ultimas"
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
                    print(f"Error en el intento {intento + 1}: {e}")
            else:
                print("Todos los intentos fallaron. Abortando.")
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            # Seleccionar todas las noticias del contenedor principal
            noticias = soup.select("ol.lista-resultados > li")
            if not noticias:
                print("No se encontraron noticias en la página.")
                return []

            items = []

            for noticia in noticias:
                try:
                    # Extraer título y enlace
                    titulo_tag = noticia.select_one("a > span.eta")
                    titulo = titulo_tag.text.strip() if titulo_tag else "Sin título"
                    enlace = noticia.select_one("a")["href"] if noticia.select_one("a") else None
                    url_completa = f"https://www12.senado.leg.br{enlace}" if enlace and enlace.startswith("/") else enlace

                    # Extraer fecha
                    fecha_tag = noticia.select_one(".text-muted")
                    fecha_texto = fecha_tag.text.strip() if fecha_tag else None
                    try:
                        fecha_actual = datetime.strptime(fecha_texto, "%d/%m/%Y %Hh%M") if fecha_texto else None
                    except ValueError:
                        print(f"Fecha inválida: {fecha_texto}")
                        fecha_actual = None

                    # Extraer descripción de la imagen
                    imagen_tag = noticia.select_one("img")
                    descripcion = imagen_tag["alt"].strip() if imagen_tag and "alt" in imagen_tag.attrs else "Sin descripción"

                    # Crear el diccionario del item
                    item = {
                        'title': titulo,
                        'description': titulo,
                        'source_type': "Legislativo",
                        'category': "Noticias",
                        'country': "Brasil",
                        'source_url': url_completa,
                        'presentation_date': fecha_actual,  # Se pasa el objeto datetime directamente
                        'metadata': {},
                        'institution': "Senado Brasil"
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando noticia: {e}")

            return items

        except Exception as e:
            print(f"Error general: {e}")
            return []


# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados
#     items = asyncio.run(scrape_senado_noticias_br())

#     # Formatear salida como JSON
#     print(json.dumps([{
#         **item,
#         'presentation_date': item['presentation_date'].strftime('%Y-%m-%d %H:%M') if item['presentation_date'] else None
#     } for item in items], indent=4, ensure_ascii=False))