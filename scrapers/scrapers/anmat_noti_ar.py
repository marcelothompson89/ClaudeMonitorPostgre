import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urljoin
import re
import logging
import json


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

BASE_URL = "https://www.argentina.gob.ar"
LISTADO_URL = "https://www.argentina.gob.ar/anmat/noticias"


MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def parse_fecha_anmat(fecha_element):
    """
    Parsea fecha desde:
    - atributo datetime
    - texto tipo '29 de junio de 2026'
    """
    if not fecha_element:
        return None

    if fecha_element.has_attr("datetime"):
        fecha_str = fecha_element["datetime"]

        try:
            fecha_dt = datetime.fromisoformat(fecha_str)

            if fecha_dt.tzinfo is None:
                return fecha_dt.replace(tzinfo=timezone.utc)

            return fecha_dt

        except ValueError as e:
            logger.warning(f"Error al parsear fecha ISO: {fecha_str} - {e}")

    fecha_texto = fecha_element.get_text(" ", strip=True)

    try:
        patron = r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})"
        match = re.search(patron, fecha_texto, re.IGNORECASE)

        if match:
            dia = int(match.group(1))
            mes_texto = match.group(2).lower()
            mes = MESES.get(mes_texto)
            anio = int(match.group(3))

            if dia and mes and anio:
                return datetime(anio, mes, dia, tzinfo=timezone.utc)

    except Exception as e:
        logger.warning(f"Error al procesar fecha de texto: {fecha_texto} - {e}")

    return None


def limpiar_texto_detalle(texto):
    """
    Limpia textos repetidos, navegación y elementos no deseados.
    """
    if not texto:
        return None

    textos_a_ignorar = [
        "Compartir en Facebook",
        "Compartir en X",
        "Compartir en Linkedin",
        "Compartir en Whatsapp",
        "Compartir en Telegram",
        "Trámites",
        "Turnos",
        "Trámites a distancia",
        "Atención a la ciudadanía",
        "Acerca de la República Argentina",
        "Acerca de Argentina.gob.ar",
        "Términos y condiciones",
        "Sugerencias",
        "Mapa del Estado",
        "Nuestro país",
        "Leyes argentinas",
        "Organismos",
        "Scroll hacia arriba",
        "Presidencia de la Nación",
        "Pasar al contenido principal",
    ]

    lineas_limpias = []

    for linea in texto.splitlines():
        linea = linea.strip()

        if not linea:
            continue

        if any(t.lower() in linea.lower() for t in textos_a_ignorar):
            continue

        lineas_limpias.append(linea)

    return "\n".join(lineas_limpias).strip() or None


async def scrape_detalle_noticia_anmat(client, url, headers):
    """
    Entra a una noticia individual de ANMAT y extrae el cuerpo completo.
    """
    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remover elementos de ruido
        for tag in soup.select("script, style, nav, header, footer, aside, form"):
            tag.decompose()

        # Posibles contenedores del contenido en argentina.gob.ar
        posibles_contenedores = [
            "article",
            "main article",
            ".content_format",
            ".region-content",
            "main",
        ]

        mejor_texto = None
        mejor_largo = 0

        for selector in posibles_contenedores:
            contenedor = soup.select_one(selector)

            if not contenedor:
                continue

            bloques = []

            # En argentina.gob.ar, el contenido útil suele estar en párrafos.
            # Incluimos li por si alguna noticia tiene bullets.
            for elemento in contenedor.select("p, li"):
                texto = elemento.get_text(" ", strip=True)

                if not texto:
                    continue

                bloques.append(texto)

            texto_contenedor = "\n".join(bloques)
            texto_contenedor = limpiar_texto_detalle(texto_contenedor)

            if texto_contenedor and len(texto_contenedor) > mejor_largo:
                mejor_texto = texto_contenedor
                mejor_largo = len(texto_contenedor)

        return mejor_texto

    except Exception as e:
        logger.warning(f"Error al extraer detalle de {url}: {e}")
        return None


async def scrape_anmat_noti_ar():
    """
    Scraper para noticias de ANMAT Argentina.
    Entra al listado y luego a cada noticia para extraer la descripción completa.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0 Safari/537.36"
        )
    }

    items = []

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        follow_redirects=True
    ) as client:

        try:
            response = None

            for intento in range(3):
                try:
                    response = await client.get(LISTADO_URL, headers=headers)
                    response.raise_for_status()
                    break

                except httpx.RequestError as e:
                    logger.error(f"Error en el intento {intento + 1}: {e}")

                    if intento == 2:
                        raise

                    await asyncio.sleep(1)

            soup = BeautifulSoup(response.text, "html.parser")

            noticias = soup.select(".row.panels-row .col-xs-12.col-sm-3")

            if not noticias:
                logger.warning("No se encontraron noticias con el selector principal.")

                # Fallback más genérico por si cambia la estructura
                noticias = soup.select(".panel, article, .col-xs-12.col-sm-3")

            for noticia in noticias:
                try:
                    enlace_element = noticia.find("a")

                    if not enlace_element or not enlace_element.get("href"):
                        continue

                    enlace = enlace_element["href"]
                    url_completa = urljoin(BASE_URL, enlace)

                    titulo_element = noticia.find("h3")

                    if not titulo_element:
                        continue

                    titulo = titulo_element.get_text(" ", strip=True)

                    descripcion_element = noticia.find("p")
                    descripcion_resumen = (
                        descripcion_element.get_text(" ", strip=True)
                        if descripcion_element
                        else titulo
                    )

                    fecha_element = noticia.find("time")
                    fecha_publicacion = parse_fecha_anmat(fecha_element)

                    imagen_url = None

                    panel_heading = noticia.find("div", class_="panel-heading")

                    if panel_heading and panel_heading.has_attr("style"):
                        imagen_style = panel_heading["style"]

                        if "background-image" in imagen_style:
                            try:
                                match = re.search(r"url\((.*?)\)", imagen_style)

                                if match:
                                    imagen_url = match.group(1).strip("'\"")
                                    imagen_url = urljoin(BASE_URL, imagen_url)

                            except Exception as e:
                                logger.warning(f"Error al extraer URL de imagen: {e}")

                    # Segunda request: entrar a la noticia
                    descripcion_detalle = await scrape_detalle_noticia_anmat(
                        client=client,
                        url=url_completa,
                        headers=headers
                    )

                    descripcion = descripcion_detalle or descripcion_resumen

                    item = {
                        "title": titulo,
                        "description": descripcion,
                        "source_type": "Ejecutivo",
                        "category": "Noticias",
                        "country": "Argentina",
                        "source_url": url_completa,
                        "presentation_date": fecha_publicacion,
                        "metadata": {
                            "image_url": imagen_url,
                            "summary_from_listing": descripcion_resumen,
                        },
                        "institution": "ANMAT Argentina",
                    }

                    items.append(item)

                    # Pausa chica para no pegarle tan fuerte al sitio
                    await asyncio.sleep(0.3)

                except Exception as e:
                    logger.error(f"Error procesando una noticia: {e}")

            return items

        except Exception as e:
            logger.error(f"Error general en el scraper: {e}")
            return []


if __name__ == "__main__":
    items = asyncio.run(scrape_anmat_noti_ar())

    print(json.dumps([
        {
            **item,
            "presentation_date": (
                item["presentation_date"].isoformat()
                if item["presentation_date"]
                else None
            )
        }
        for item in items
    ], indent=4, ensure_ascii=False))