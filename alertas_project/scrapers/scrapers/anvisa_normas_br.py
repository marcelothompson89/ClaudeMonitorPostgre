import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json  # Importa el módulo json para formatear la salida


async def scrape_anvisa_normas_br():
    """
    Scraper para la página de ANVISA adaptado al estilo de la app.
    """
    url = "https://anvisalegis.datalegis.net/action/ActionDatalegis.php?acao=abrirEmentario&cod_modulo=293&cod_menu=8499"
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

            # Seleccionar todas las secciones del contenedor principal
            secciones = soup.select("#tdAtosResenha > *")
            fecha_actual = None  # Variable para almacenar la fecha vigente
            items = []

            for elemento in secciones:
                # Identificar y actualizar la fecha
                if "resenhaTitulo" in elemento.get("class", []):
                    fecha_tag = elemento.find("span")
                    if fecha_tag and "Data:" in fecha_tag.text:
                        fecha_texto = fecha_tag.text.replace("Data:", "").strip()
                        try:
                            fecha_actual = datetime.strptime(fecha_texto, "%d/%m/%Y")
                            print(f"Fecha actualizada: {fecha_actual}")
                        except ValueError:
                            print(f"Fecha inválida: {fecha_texto}")
                            fecha_actual = None

                # Procesar artículos
                elif "ato" in elemento.get("class", []):
                    if not fecha_actual:
                        print("Error: No se encontró una fecha válida antes de procesar los artículos.")
                        continue

                    try:
                        # Extraer enlace
                        link_tag = elemento.find("a", class_="link")
                        enlace = link_tag["href"] if link_tag else None
                        url_completa = f"https://anvisalegis.datalegis.net{enlace}" if enlace else None

                        # Extraer título
                        titulo_tag = link_tag.find("strong") if link_tag else None
                        titulo = titulo_tag.text.strip() if titulo_tag else "Sin título"

                        # Extraer descripción
                        descripcion_tag = link_tag.find_all("p") if link_tag else []
                        descripcion = " ".join(p.text.strip() for p in descripcion_tag)

                        # Extraer metadatos adicionales (Nota y Publicación)
                        nota_url = elemento.find("a", text=re.compile('Nota', re.I))
                        publicacion_url = elemento.find("a", text=re.compile('Publicação', re.I))

                        # Crear el diccionario del item
                        item = {
                            'title': titulo,
                            'description': descripcion,
                            'source_type': "ANVISA",
                            'category': "Normas",
                            'country': "Brasil",
                            'source_url': url_completa,
                            'presentation_date': fecha_actual,  # Pasamos el objeto datetime directamente
                            'metadata': {
                                'nota_url': nota_url.get('href') if nota_url else None,
                                'publicacion_url': publicacion_url.get('href') if publicacion_url else None
                            },
                            'institution': "ANVISA"
                        }
                        items.append(item)

                    except Exception as e:
                        print(f"Error procesando un artículo: {e}")

            return items

        except Exception as e:
            print(f"Error general: {e}")
            return []


#if __name__ == "__main__":
    # Ejecutar el scraper y mostrar los resultados
#    items = asyncio.run(scrape_anvisa())

    # Formatear salida como JSON
#    print(json.dumps([{
#        **item,
#        'presentation_date': item['presentation_date'].strftime('%Y-%m-%d') if item['presentation_date'] else None
#    } for item in items], indent=4, ensure_ascii=False))