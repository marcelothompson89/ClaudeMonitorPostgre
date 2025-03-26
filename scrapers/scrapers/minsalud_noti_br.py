import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import json


async def scrape_minsalud_noticias_br():
    """
    Scraper para la página de noticias del Ministério da Saúde de Brasil.
    """
    url = "https://www.gov.br/saude/pt-br/assuntos/noticias"
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
            noticias = soup.select("article.tileItem")
            if not noticias:
                print("No se encontraron noticias en la página.")
                return []

            items = []

            for noticia in noticias:
                try:
                    # Extraer título y enlace
                    titulo_tag = noticia.select_one("h2.tileHeadline > a")
                    titulo = titulo_tag.text.strip() if titulo_tag else "Sin título"
                    enlace = titulo_tag["href"] if titulo_tag else None
                    url_completa = f"https://www.gov.br{enlace}" if enlace and not enlace.startswith("http") else enlace

                    # Extraer descripción
                    descripcion_tag = noticia.select_one("p.tileBody > span.description")
                    descripcion = descripcion_tag.text.strip() if descripcion_tag else "Sin descripción"

                    # Extraer fecha y hora
                    fecha_tag = noticia.find("i", class_="icon-day").find_next_sibling(string=True)
                    hora_tag = noticia.find("i", class_="icon-hour").find_next_sibling(string=True)

                    fecha_texto = fecha_tag.strip() if fecha_tag else None
                    hora_texto = hora_tag.strip().replace("h", ":") if hora_tag else None

                    fecha_hora = None
                    if fecha_texto and hora_texto:
                        try:
                            fecha_hora = datetime.strptime(f"{fecha_texto} {hora_texto}", "%d/%m/%Y %H:%M")
                        except ValueError:
                            print(f"Fecha inválida: {fecha_texto} {hora_texto}")
                            fecha_hora = None

                    # Extraer etiquetas
                    etiquetas = [tag.text.strip() for tag in noticia.select("div.keywords span a")]

                    # Crear el diccionario del item
                    item = {
                        'title': titulo,
                        'description': f"{descripcion} | {' | '.join(etiquetas)}",
                        'source_type': "Ejecutivo",
                        'category': "Noticias",
                        'country': "Brasil",
                        'source_url': url_completa,
                        'presentation_date': fecha_hora,  # Se pasa el objeto datetime directamente
                        'institution': "Ministério da Saúde Brasil"
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
#     items = asyncio.run(scrape_minsalud_noticias_br())

#     # Formatear salida como JSON
#     print(json.dumps([{
#         **item,
#         'presentation_date': item['presentation_date'].strftime('%Y-%m-%d %H:%M') if item['presentation_date'] else None
#     } for item in items], indent=4, ensure_ascii=False))