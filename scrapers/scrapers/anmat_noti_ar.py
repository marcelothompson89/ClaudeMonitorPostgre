import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import re
import logging

# Configuración básica de logging si se ejecuta como script independiente
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def scrape_anmat_noti_ar():
    """
    Scraper para la página de noticias de ANMAT Argentina.
    """
    url = "https://www.argentina.gob.ar/anmat/noticias"
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
                    if intento == 2:  # Si es el último intento, propagar el error
                        raise
                    await asyncio.sleep(1)  # Esperar antes de reintentar
            
            soup = BeautifulSoup(response.text, "html.parser")

            # Seleccionar los contenedores de noticias
            # Similar a la estructura de alertas
            noticias = soup.select(".row.panels-row .col-xs-12.col-sm-3")
            items = []

            for noticia in noticias:
                try:
                    # Extraer enlace
                    enlace_element = noticia.find("a")
                    if not enlace_element:
                        continue
                        
                    enlace = enlace_element["href"]
                    # Normalizar la URL
                    url_completa = f"https://www.argentina.gob.ar{enlace}" if enlace.startswith('/') else enlace

                    # Extraer título
                    titulo_element = noticia.find("h3")
                    if not titulo_element:
                        continue
                    titulo = titulo_element.get_text(strip=True)

                    # Extraer descripción
                    descripcion_element = noticia.find("p")
                    descripcion = descripcion_element.get_text(strip=True) if descripcion_element else titulo

                    # Extraer fecha
                    fecha_element = noticia.find("time")
                    fecha_publicacion = None
                    
                    if fecha_element and fecha_element.has_attr("datetime"):
                        # Método 1: Usar el atributo datetime
                        fecha_str = fecha_element["datetime"]
                        try:
                            # Parsear la fecha ISO
                            fecha_dt = datetime.fromisoformat(fecha_str)
                            # Si la fecha no tiene timezone, asignar UTC
                            if fecha_dt.tzinfo is None:
                                fecha_publicacion = fecha_dt.replace(tzinfo=timezone.utc)
                            else:
                                fecha_publicacion = fecha_dt
                        except ValueError as e:
                            logger.warning(f"Error al parsear fecha ISO: {fecha_str} - {e}")
                    
                    # Si no se pudo obtener la fecha del atributo datetime, intentar del texto
                    if not fecha_publicacion and fecha_element:
                        fecha_texto = fecha_element.get_text(strip=True)
                        try:
                            # Formato esperado: "16 de abril de 2025"
                            meses = {
                                'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 
                                'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8, 
                                'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
                            }
                            
                            # Regex para extraer día, mes y año
                            patron = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})'
                            match = re.search(patron, fecha_texto, re.IGNORECASE)
                            
                            if match:
                                dia = int(match.group(1))
                                mes_texto = match.group(2).lower()
                                mes = meses.get(mes_texto)
                                anio = int(match.group(3))
                                
                                if dia and mes and anio:
                                    # Crear fecha con timezone UTC
                                    fecha_publicacion = datetime(anio, mes, dia, tzinfo=timezone.utc)
                            else:
                                logger.warning(f"No se pudo extraer la fecha del texto: {fecha_texto}")
                        except Exception as e:
                            logger.warning(f"Error al procesar fecha de texto: {fecha_texto} - {e}")

                    # Extraer imagen (como metadato adicional)
                    imagen_url = None
                    panel_heading = noticia.find("div", class_="panel-heading")
                    if panel_heading and panel_heading.has_attr("style"):
                        imagen_style = panel_heading["style"]
                        if "background-image" in imagen_style:
                            try:
                                imagen_url = re.search(r'url\((.*?)\)', imagen_style).group(1)
                                # Limpiar posibles comillas
                                imagen_url = imagen_url.strip("'\"")
                            except Exception as e:
                                logger.warning(f"Error al extraer URL de imagen: {e}")

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
            logger.error(f"Error general en el scraper: {e}")
            return []

# Para pruebas directas
if __name__ == "__main__":
    import json
    items = asyncio.run(scrape_anmat_noti_ar())
    # Formatear salida como JSON
    print(json.dumps([{
        **item,
        'presentation_date': item['presentation_date'].isoformat() if item['presentation_date'] else None
    } for item in items], indent=4, ensure_ascii=False))