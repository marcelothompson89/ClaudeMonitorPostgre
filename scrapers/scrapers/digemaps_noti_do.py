import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

BASE_URL = "https://digemaps.gob.do"
LISTADO_URL = "https://digemaps.gob.do/noticias/"


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


def parse_fecha_digemaps(fecha_element):
    """
    Parsea la fecha desde:

    - El atributo datetime:
      2026-06-22T10:44:21-04:00

    - Un texto como:
      22 de junio de 2026
    """
    if not fecha_element:
        return None

    fecha_iso = fecha_element.get("datetime")

    if fecha_iso:
        try:
            fecha_dt = datetime.fromisoformat(fecha_iso.strip())

            if fecha_dt.tzinfo is None:
                return fecha_dt.replace(tzinfo=timezone.utc)

            return fecha_dt

        except ValueError as exc:
            logger.warning(
                "No se pudo interpretar la fecha ISO %s: %s",
                fecha_iso,
                exc,
            )

    fecha_texto = fecha_element.get_text(" ", strip=True)

    patron = (
        r"(\d{1,2})\s+de\s+"
        r"([a-záéíóúñ]+)\s+de\s+"
        r"(\d{4})"
    )

    match = re.search(
        patron,
        fecha_texto,
        re.IGNORECASE,
    )

    if not match:
        logger.warning(
            "Formato de fecha no reconocido: %s",
            fecha_texto,
        )
        return None

    dia = int(match.group(1))
    mes_texto = match.group(2).lower()
    anio = int(match.group(3))

    mes = MESES.get(mes_texto)

    if not mes:
        logger.warning(
            "Mes no reconocido: %s",
            mes_texto,
        )
        return None

    try:
        return datetime(
            anio,
            mes,
            dia,
            tzinfo=timezone.utc,
        )

    except ValueError as exc:
        logger.warning(
            "Fecha inválida %s: %s",
            fecha_texto,
            exc,
        )
        return None


def limpiar_texto(texto):
    """
    Normaliza los espacios, elimina bloques repetidos
    y descarta textos de navegación, redes sociales
    o comentarios.
    """
    if not texto:
        return None

    textos_a_ignorar = (
        "facebook twitter linkedin messenger whatsapp email print",
        "deja un comentario",
        "dejar un comentario",
        "cancelar la respuesta",
        "guarda mi nombre",
        "guardar mi nombre",
        "categorías",
        "saltar al contenido",
        "términos de uso",
        "políticas de privacidad",
        "preguntas frecuentes",
        "todos los derechos reservados",
        "entradas relacionadas",
        "artículos relacionados",
        "compartir en",
    )

    bloques_limpios = []
    vistos = set()

    for bloque in texto.splitlines():
        bloque = re.sub(
            r"\s+",
            " ",
            bloque,
        ).strip()

        if not bloque:
            continue

        bloque_minusculas = bloque.lower()

        if any(
            texto_ignorado in bloque_minusculas
            for texto_ignorado in textos_a_ignorar
        ):
            continue

        # Evitar párrafos repetidos.
        if bloque_minusculas in vistos:
            continue

        vistos.add(bloque_minusculas)
        bloques_limpios.append(bloque)

    if not bloques_limpios:
        return None

    return "\n\n".join(bloques_limpios).strip()


async def obtener_html(
    client,
    url,
    headers,
    intentos=3,
):
    """
    Realiza una solicitud HTTP con reintentos.
    """
    ultimo_error = None

    for intento in range(1, intentos + 1):
        try:
            response = await client.get(
                url,
                headers=headers,
            )

            response.raise_for_status()

            return response.text

        except (
            httpx.RequestError,
            httpx.HTTPStatusError,
        ) as exc:
            ultimo_error = exc

            logger.warning(
                "Error solicitando %s. Intento %s/%s: %s",
                url,
                intento,
                intentos,
                exc,
            )

            if intento < intentos:
                await asyncio.sleep(intento)

    raise RuntimeError(
        f"No se pudo descargar {url}"
    ) from ultimo_error


async def scrape_detalle_noticia_digemaps(
    client,
    url,
    headers,
):
    """
    Ingresa a una noticia individual de DIGEMAPS
    y extrae el texto completo.
    """
    try:
        html = await obtener_html(
            client=client,
            url=url,
            headers=headers,
        )

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        # Elementos que no forman parte del cuerpo
        # principal de la noticia.
        selectores_ruido = (
            "script",
            "style",
            "noscript",
            "nav",
            "header",
            "footer",
            "aside",
            "form",
            ".comments-area",
            ".comment-respond",
            ".post-navigation",
            ".navigation",
            ".entry-footer",
            ".sharedaddy",
            ".sd-sharing-enabled",
            ".addtoany_share_save_container",
            ".heateor_sss_sharing_container",
            ".wp-block-social-links",
            ".social-share",
            ".share-links",
            ".related-posts",
            ".yarpp-related",
        )

        for selector in selectores_ruido:
            for elemento in soup.select(selector):
                elemento.decompose()

        # Primero se prueban contenedores específicos
        # de WordPress y luego selectores más generales.
        posibles_contenedores = (
            "article .entry-content",
            ".entry-content",
            "article .post-content",
            ".post-content",
            "article .td-post-content",
            ".td-post-content",
            "main article",
            ".site-main article",
            "article",
            "main",
        )

        mejor_texto = None
        mejor_largo = 0

        for selector in posibles_contenedores:
            contenedor = soup.select_one(selector)

            if not contenedor:
                continue

            bloques = []

            # Se incluyen párrafos, listas y subtítulos.
            for elemento in contenedor.select(
                "p, li, h2, h3, h4"
            ):
                texto = elemento.get_text(
                    " ",
                    strip=True,
                )

                if texto:
                    bloques.append(texto)

            texto_contenedor = limpiar_texto(
                "\n".join(bloques)
            )

            if (
                texto_contenedor
                and len(texto_contenedor) > mejor_largo
            ):
                mejor_texto = texto_contenedor
                mejor_largo = len(texto_contenedor)

        return mejor_texto

    except Exception as exc:
        logger.warning(
            "Error al extraer el detalle de %s: %s",
            url,
            exc,
        )
        return None


async def scrape_digemaps_noti_do():
    """
    Scraper de noticias de DIGEMAPS,
    República Dominicana.

    Del listado extrae:

    - título
    - resumen
    - fecha
    - categoría de origen
    - autor
    - imagen
    - enlace

    Luego ingresa a cada noticia para obtener
    el texto completo.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/126.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,"
            "application/xhtml+xml,"
            "application/xml;q=0.9,"
            "image/avif,"
            "image/webp,"
            "*/*;q=0.8"
        ),
        "Accept-Language": (
            "es-ES,es;q=0.9,en;q=0.8"
        ),
    }

    items = []

    limits = httpx.Limits(
        max_connections=5,
        max_keepalive_connections=5,
    )

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
        limits=limits,
    ) as client:
        try:
            html = await obtener_html(
                client=client,
                url=LISTADO_URL,
                headers=headers,
            )

            soup = BeautifulSoup(
                html,
                "html.parser",
            )

            noticias = soup.select(
                ".pt-cv-content-item"
            )

            if not noticias:
                logger.warning(
                    "No se encontraron noticias con "
                    ".pt-cv-content-item. "
                    "Se utilizará un selector alternativo."
                )

                noticias = soup.select(
                    "article, .post, .type-post"
                )

            logger.info(
                "Se encontraron %s noticias.",
                len(noticias),
            )

            for numero, noticia in enumerate(
                noticias,
                start=1,
            ):
                try:
                    # Título y enlace
                    titulo_link = noticia.select_one(
                        ".pt-cv-title a"
                    )

                    if not titulo_link:
                        titulo_link = noticia.select_one(
                            "h2 a, h3 a, h4 a"
                        )

                    if (
                        not titulo_link
                        or not titulo_link.get("href")
                    ):
                        logger.warning(
                            "La noticia %s no contiene "
                            "título o enlace.",
                            numero,
                        )
                        continue

                    titulo = titulo_link.get_text(
                        " ",
                        strip=True,
                    )

                    url_completa = urljoin(
                        BASE_URL,
                        titulo_link["href"],
                    )

                    # Resumen mostrado en el listado
                    resumen_element = noticia.select_one(
                        ".pt-cv-content"
                    )

                    descripcion_resumen = (
                        resumen_element.get_text(
                            " ",
                            strip=True,
                        )
                        if resumen_element
                        else titulo
                    )

                    # Fecha
                    fecha_element = noticia.select_one(
                        ".entry-date time, time"
                    )

                    fecha_publicacion = (
                        parse_fecha_digemaps(
                            fecha_element
                        )
                    )

                    # Categoría original
                    categoria_element = noticia.select_one(
                        ".pt-cv-taxoterm a, .category a"
                    )

                    categoria_origen = (
                        categoria_element.get_text(
                            " ",
                            strip=True,
                        )
                        if categoria_element
                        else None
                    )

                    # Autor
                    autor_element = noticia.select_one(
                        ".author a, [rel='author']"
                    )

                    autor = (
                        autor_element.get_text(
                            " ",
                            strip=True,
                        )
                        if autor_element
                        else None
                    )

                    # Imagen
                    imagen_element = noticia.select_one(
                        "img.pt-cv-thumbnail, "
                        ".pt-cv-thumb-wrapper img, "
                        "img"
                    )

                    imagen_url = None

                    if imagen_element:
                        imagen_src = (
                            imagen_element.get("src")
                            or imagen_element.get("data-src")
                            or imagen_element.get(
                                "data-lazy-src"
                            )
                        )

                        if imagen_src:
                            imagen_url = urljoin(
                                BASE_URL,
                                imagen_src,
                            )

                    logger.info(
                        "Procesando noticia %s/%s: %s",
                        numero,
                        len(noticias),
                        titulo,
                    )

                    # Segunda solicitud:
                    # ingresar a la noticia y obtener
                    # el contenido completo.
                    descripcion_completa = (
                        await scrape_detalle_noticia_digemaps(
                            client=client,
                            url=url_completa,
                            headers=headers,
                        )
                    )

                    item = {
                        "title": titulo,
                        "description": (
                            descripcion_completa
                            or descripcion_resumen
                        ),
                        "source_type": "Ejecutivo",
                        "category": "Noticias",
                        "country": "República Dominicana",
                        "source_url": url_completa,
                        "presentation_date": fecha_publicacion,
                        "metadata": {
                            "image_url": imagen_url,
                            "summary_from_listing": (
                                descripcion_resumen
                            ),
                            "category_from_source": (
                                categoria_origen
                            ),
                            "author": autor,
                        },
                        "institution": (
                            "DIGEMAPS República Dominicana"
                        ),
                    }

                    items.append(item)

                    # Pausa breve para no sobrecargar
                    # el servidor.
                    await asyncio.sleep(0.3)

                except Exception as exc:
                    logger.exception(
                        "Error procesando la noticia %s: %s",
                        numero,
                        exc,
                    )

            return items

        except Exception as exc:
            logger.exception(
                "Error general en el scraper "
                "de DIGEMAPS: %s",
                exc,
            )
            return []


if __name__ == "__main__":
    resultados = asyncio.run(
        scrape_digemaps_noti_do()
    )

    # Se transforma datetime a texto únicamente
    # para poder imprimir el resultado como JSON.
    salida_json = [
        {
            **item,
            "presentation_date": (
                item["presentation_date"].isoformat()
                if item["presentation_date"]
                else None
            ),
        }
        for item in resultados
    ]

    print(
        json.dumps(
            salida_json,
            indent=4,
            ensure_ascii=False,
        )
    )