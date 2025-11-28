import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import json


async def scrape_diputados_noti_br():
    """
    Scraper para la página de noticias de la Câmara dos Deputados de Brasil.
    """
    url = "https://www.camara.leg.br/noticias/ultimas"
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
            noticias = soup.select("ul.l-lista-noticias > li.l-lista-noticias__item > article.g-chamada")
            if not noticias:
                print("No se encontraron noticias en la página.")
                return []

            items = []

            for noticia in noticias:
                try:
                    # Extraer título y enlace
                    titulo_tag = noticia.select_one("h3.g-chamada__titulo a")
                    titulo = titulo_tag.text.strip() if titulo_tag else "Sin título"
                    enlace = titulo_tag["href"] if titulo_tag else None
                    url_completa = f"https://www.camara.leg.br{enlace}" if enlace and not enlace.startswith("http") else enlace

                    # Extraer fecha y hora (están en elementos separados)
                    fecha_tag = noticia.select_one("span.g-chamada__data")
                    hora_tag = noticia.select_one("span.g-chamada__hora")
                    
                    fecha_texto = fecha_tag.text.strip() if fecha_tag else None
                    hora_texto = hora_tag.text.strip() if hora_tag else None
                    
                    fecha_actual = None
                    if fecha_texto and hora_texto:
                        try:
                            fecha_hora_completa = f"{fecha_texto} {hora_texto}"
                            fecha_actual = datetime.strptime(fecha_hora_completa, "%d/%m/%Y %H:%M")
                        except ValueError as e:
                            print(f"Fecha inválida: {fecha_hora_completa} - Error: {e}")
                    else:
                        print(f"Fecha u hora no encontradas. Fecha: {fecha_texto}, Hora: {hora_texto}")

                    # Extraer descripción
                    descripcion_tag = noticia.select_one("img.g-chamada__imagem")
                    descripcion = descripcion_tag["alt"].strip() if descripcion_tag else "Sin descripción"

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
                        'institution': "Câmara de Deputados Brasil"
                    }
                    items.append(item)

                except Exception as e:
                    print(f"Error procesando noticia: {e}")

            return items

        except Exception as e:
            print(f"Error general: {e}")
            return []


if __name__ == "__main__":
    # Ejecutar el scraper y mostrar los resultados
    items = asyncio.run(scrape_diputados_noti_br())

    # Formatear salida como JSON
    print(json.dumps([{
        **item,
        'presentation_date': item['presentation_date'].strftime('%Y-%m-%d %H:%M') if item['presentation_date'] else None
    } for item in items], indent=4, ensure_ascii=False))