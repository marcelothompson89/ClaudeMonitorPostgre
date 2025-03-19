import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json


async def scrape_anvisa_noti_br():
    """
    Scraper para extraer noticias desde el sitio web de ANVISA adaptado al estilo del scraper base.
    """
    url = "https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa"
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

            # Seleccionar todas las noticias
            lista_noticias = soup.select("ul.noticias.listagem-noticias-com-foto > li")
            items = []

            for noticia in lista_noticias:
                try:
                    # Extraer título
                    titulo_tag = noticia.select_one("h2.titulo a")
                    titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Sin título"

                    # Extraer enlace
                    enlace = titulo_tag["href"] if titulo_tag else None
                    url_completa = enlace if enlace.startswith("http") else f"https://www.gov.br{enlace}"

                    # Extraer subtítulo
                    subtitulo_tag = noticia.select_one("div.subtitulo-noticia")
                    subtitulo = subtitulo_tag.get_text(strip=True) if subtitulo_tag else "Sin subtítulo"

                    # Extraer fecha
                    fecha_tag = noticia.select_one("span.data")
                    fecha_texto = fecha_tag.get_text(strip=True) if fecha_tag else None
                    try:
                        fecha_actual = datetime.strptime(fecha_texto, "%d/%m/%Y") if fecha_texto else None
                        #print(f"Fecha actualizada: {fecha_actual}")
                    except ValueError:
                        print(f"Fecha inválida: {fecha_texto}")
                        fecha_actual = None

                    # Extraer descripción
                    descripcion_tag = noticia.select_one("span.descricao")
                    descripcion = (
                        descripcion_tag.get_text(strip=True).replace(fecha_texto, "").strip()
                        if descripcion_tag and fecha_texto
                        else "Sin descripción"
                    )

                    # Extraer etiquetas/tags
                    tags = [
                        tag.get_text(strip=True)
                        for tag in noticia.select("div.subject-noticia a.link-category")
                    ]
                    etiquetas = ", ".join(tags) if tags else "Sin etiquetas"

                    # Crear el diccionario del item
                    item = {
                        'title': titulo,
                        'description':subtitulo + "|" + descripcion,
                        'source_type': "ANVISA Noticias",
                        'category': "Noticias",
                        'country': "Brasil",
                        'source_url': url_completa,
                        'presentation_date': fecha_actual,  # Pasamos el objeto datetime directamente
                        'metadata': {
                            'tags': etiquetas
                        },
                        'institution': "ANVISA"
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
#     items = asyncio.run(scrape_anvisa_noticias())

#     # Formatear salida como JSON
#     print(json.dumps([{
#         **item,
#         'presentation_date': item['presentation_date'].strftime('%Y-%m-%d') if item['presentation_date'] else None
#     } for item in items], indent=4, ensure_ascii=False))