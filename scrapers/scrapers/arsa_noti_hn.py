import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURACIÓN
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

BASE_URL = "https://arsa.gob.hn"
LISTADO_URL = "https://arsa.gob.hn/categoria/noticias/"

# El sitio de ARSA presenta problemas con la cadena
# de certificados SSL.
#
# Se desactiva la validación únicamente para este scraper.
VERIFY_SSL = False

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


# ============================================================
# FUNCIONES DE FECHA
# ============================================================

def parse_fecha_texto(fecha_texto):
    """
    Convierte textos como:

    29 de junio de 2026
    Tegucigalpa, 29 de junio de 2026

    en un objeto datetime.
    """
    if not fecha_texto:
        return None

    fecha_texto = re.sub(
        r"\s+",
        " ",
        fecha_texto,
    ).strip()

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
            "Fecha inválida '%s': %s",
            fecha_texto,
            exc,
        )
        return None


def parse_fecha_iso(fecha_iso):
    """
    Convierte una fecha ISO como:

    2026-06-29T10:30:00-06:00
    2026-06-29T16:30:00Z
    """
    if not fecha_iso:
        return None

    fecha_iso = fecha_iso.strip()

    if fecha_iso.endswith("Z"):
        fecha_iso = fecha_iso[:-1] + "+00:00"

    try:
        fecha = datetime.fromisoformat(fecha_iso)

        if fecha.tzinfo is None:
            fecha = fecha.replace(
                tzinfo=timezone.utc
            )

        return fecha

    except ValueError:
        return None


def extraer_fecha_pagina(soup, texto_noticia=None):
    """
    Intenta extraer la fecha desde:

    1. Meta tags de WordPress/Open Graph.
    2. Etiquetas <time>.
    3. Texto completo de la noticia.
    """

    selectores_meta = (
        'meta[property="article:published_time"]',
        'meta[itemprop="datePublished"]',
        'meta[name="date"]',
        'meta[name="publish_date"]',
    )

    for selector in selectores_meta:
        elemento = soup.select_one(selector)

        if not elemento:
            continue

        fecha = parse_fecha_iso(
            elemento.get("content")
        )

        if fecha:
            return fecha

    selectores_fecha = (
        "time[datetime]",
        ".entry-date[datetime]",
        ".posted-on time[datetime]",
        ".date-posted time[datetime]",
    )

    for selector in selectores_fecha:
        elemento = soup.select_one(selector)

        if not elemento:
            continue

        fecha = parse_fecha_iso(
            elemento.get("datetime")
        )

        if fecha:
            return fecha

        fecha = parse_fecha_texto(
            elemento.get_text(" ", strip=True)
        )

        if fecha:
            return fecha

    if texto_noticia:
        fecha = parse_fecha_texto(
            texto_noticia
        )

        if fecha:
            return fecha

    return parse_fecha_texto(
        soup.get_text(" ", strip=True)
    )


# ============================================================
# FUNCIONES DE LIMPIEZA
# ============================================================

def limpiar_texto(texto, titulo=None):
    """
    Limpia el contenido completo de la noticia.

    Elimina:

    - Textos de navegación.
    - Redes sociales.
    - Comentarios.
    - Párrafos repetidos.
    - El título repetido dentro del cuerpo.
    """
    if not texto:
        return None

    textos_a_ignorar = (
        "compartir en facebook",
        "compartir en twitter",
        "compartir en x",
        "compartir en linkedin",
        "compartir en whatsapp",
        "deja un comentario",
        "dejar un comentario",
        "cancelar la respuesta",
        "guardar mi nombre",
        "guarda mi nombre",
        "correo electrónico",
        "sitio web en este navegador",
        "entradas relacionadas",
        "artículos relacionados",
        "todos los derechos reservados",
        "política de privacidad",
        "términos y condiciones",
        "anterior anterior",
        "siguiente siguiente",
        "navegación de entradas",
    )

    titulo_normalizado = None

    if titulo:
        titulo_normalizado = re.sub(
            r"\s+",
            " ",
            titulo,
        ).strip().lower()

    bloques_limpios = []
    bloques_vistos = set()

    for bloque in texto.splitlines():
        bloque = re.sub(
            r"\s+",
            " ",
            bloque,
        ).strip()

        if not bloque:
            continue

        bloque_minusculas = bloque.lower()

        if (
            titulo_normalizado
            and bloque_minusculas == titulo_normalizado
        ):
            continue

        if any(
            texto_ignorado in bloque_minusculas
            for texto_ignorado in textos_a_ignorar
        ):
            continue

        if bloque_minusculas in bloques_vistos:
            continue

        bloques_vistos.add(
            bloque_minusculas
        )

        bloques_limpios.append(
            bloque
        )

    if not bloques_limpios:
        return None

    return "\n\n".join(
        bloques_limpios
    ).strip()


# ============================================================
# FUNCIÓN DE IMÁGENES
# ============================================================

def obtener_mejor_imagen(imagen_element):
    """
    Obtiene la imagen de mayor resolución.

    Si existe el atributo srcset, selecciona
    la imagen con mayor ancho disponible.
    """
    if not imagen_element:
        return None

    srcset = (
        imagen_element.get("srcset")
        or imagen_element.get("data-srcset")
    )

    if srcset:
        candidatos = []

        for parte in srcset.split(","):
            fragmentos = parte.strip().split()

            if not fragmentos:
                continue

            imagen_url = fragmentos[0]
            ancho = 0

            if len(fragmentos) > 1:
                match = re.search(
                    r"(\d+)w",
                    fragmentos[1],
                )

                if match:
                    ancho = int(
                        match.group(1)
                    )

            candidatos.append(
                (ancho, imagen_url)
            )

        if candidatos:
            _, mejor_url = max(
                candidatos,
                key=lambda candidato: candidato[0],
            )

            return urljoin(
                BASE_URL,
                mejor_url,
            )

    imagen_src = (
        imagen_element.get("data-src")
        or imagen_element.get("data-lazy-src")
        or imagen_element.get("src")
    )

    if not imagen_src:
        return None

    return urljoin(
        BASE_URL,
        imagen_src,
    )


# ============================================================
# SOLICITUDES HTTP
# ============================================================

async def obtener_html(
    client,
    url,
    headers,
    intentos=3,
):
    """
    Descarga una página con reintentos.
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
                await asyncio.sleep(
                    intento
                )

    raise RuntimeError(
        f"No se pudo descargar {url}"
    ) from ultimo_error


# ============================================================
# EXTRACCIÓN DE LA NOTICIA COMPLETA
# ============================================================

async def scrape_detalle_noticia_arsa(
    client,
    url,
    headers,
    titulo=None,
):
    """
    Ingresa en una noticia individual de ARSA y extrae:

    - Texto completo.
    - Fecha de publicación.
    - Imagen principal.
    """
    resultado_vacio = {
        "description": None,
        "presentation_date": None,
        "image_url": None,
    }

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

        # Extraer metadatos antes de eliminar
        # elementos del HTML.
        fecha_publicacion = extraer_fecha_pagina(
            soup
        )

        imagen_url = None

        meta_imagen = soup.select_one(
            'meta[property="og:image"]'
        )

        if meta_imagen:
            imagen_url = meta_imagen.get(
                "content"
            )

            if imagen_url:
                imagen_url = urljoin(
                    BASE_URL,
                    imagen_url,
                )

        if not imagen_url:
            imagen_element = soup.select_one(
                "article img.wp-post-image, "
                ".entry-content img, "
                ".article-inner img, "
                "article img"
            )

            imagen_url = obtener_mejor_imagen(
                imagen_element
            )

        # Eliminar contenido que no corresponde
        # al cuerpo de la noticia.
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
            ".navigation-post",
            ".blog-share",
            ".social-icons",
            ".share-icons",
            ".entry-meta",
            ".author-box",
            ".related-posts",
            ".badge",
            ".absolute-footer",
            ".footer-wrapper",
            ".header-wrapper",
            ".breadcrumbs",
        )

        for selector in selectores_ruido:
            for elemento in soup.select(selector):
                elemento.decompose()

        posibles_contenedores = (
            "article .entry-content.single-page",
            "article .entry-content",
            ".entry-content.single-page",
            ".entry-content",
            ".blog-single .entry-content",
            ".article-inner",
            ".post-content",
            "main article",
            "article",
            "main",
        )

        mejor_texto = None
        mejor_largo = 0

        for selector in posibles_contenedores:
            contenedor = soup.select_one(
                selector
            )

            if not contenedor:
                continue

            bloques = []

            for elemento in contenedor.select(
                "p, li, h2, h3, h4, blockquote"
            ):
                texto = elemento.get_text(
                    " ",
                    strip=True,
                )

                if texto:
                    bloques.append(
                        texto
                    )

            texto_contenedor = limpiar_texto(
                "\n".join(bloques),
                titulo=titulo,
            )

            if (
                texto_contenedor
                and len(texto_contenedor) > mejor_largo
            ):
                mejor_texto = texto_contenedor
                mejor_largo = len(
                    texto_contenedor
                )

        # Si no se encontró la fecha en los metadatos,
        # buscarla en el contenido completo.
        if not fecha_publicacion:
            fecha_publicacion = parse_fecha_texto(
                mejor_texto
            )

        return {
            "description": mejor_texto,
            "presentation_date": fecha_publicacion,
            "image_url": imagen_url,
        }

    except Exception as exc:
        logger.warning(
            "Error al extraer el detalle de %s: %s",
            url,
            exc,
        )

        return resultado_vacio


# ============================================================
# SCRAPER PRINCIPAL
# ============================================================

async def scrape_arsa_noti_hn():
    """
    Scraper de noticias de ARSA Honduras.

    Extrae del listado:

    - Título.
    - Resumen.
    - Enlace.
    - Imagen.
    - Fecha.

    Luego ingresa en cada noticia para obtener
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
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    items = []

    limits = httpx.Limits(
        max_connections=5,
        max_keepalive_connections=5,
    )

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=30.0,
            read=30.0,
            write=30.0,
            pool=30.0,
        ),
        follow_redirects=True,
        limits=limits,

        # Necesario por el problema de certificado
        # del servidor de ARSA.
        verify=VERIFY_SSL,
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
                ".box.box-text-bottom.box-blog-post"
            )

            if not noticias:
                logger.warning(
                    "No se encontraron noticias con "
                    "el selector principal. "
                    "Se utilizarán selectores alternativos."
                )

                noticias = soup.select(
                    ".box-blog-post, article.post"
                )

            logger.info(
                "Se encontraron %s noticias.",
                len(noticias),
            )

            urls_procesadas = set()

            for numero, noticia in enumerate(
                noticias,
                start=1,
            ):
                try:
                    titulo_link = noticia.select_one(
                        ".post-title a"
                    )

                    if not titulo_link:
                        titulo_link = noticia.select_one(
                            ".box-image a, "
                            "h2 a, "
                            "h3 a, "
                            "h4 a, "
                            "h5 a"
                        )

                    if (
                        not titulo_link
                        or not titulo_link.get("href")
                    ):
                        logger.warning(
                            "La noticia %s no contiene enlace.",
                            numero,
                        )
                        continue

                    titulo = titulo_link.get_text(
                        " ",
                        strip=True,
                    )

                    if not titulo:
                        titulo = titulo_link.get(
                            "aria-label",
                            "",
                        ).strip()

                    if not titulo:
                        logger.warning(
                            "La noticia %s no contiene título.",
                            numero,
                        )
                        continue

                    url_completa = urljoin(
                        BASE_URL,
                        titulo_link["href"],
                    )

                    # Evitar publicaciones duplicadas.
                    if url_completa in urls_procesadas:
                        continue

                    urls_procesadas.add(
                        url_completa
                    )

                    resumen_element = noticia.select_one(
                        ".from_the_blog_excerpt"
                    )

                    descripcion_resumen = (
                        resumen_element.get_text(
                            " ",
                            strip=True,
                        )
                        if resumen_element
                        else titulo
                    )

                    # Eliminar el [...] del final.
                    descripcion_resumen = re.sub(
                        r"\s*\[\s*\.\.\.\s*\]\s*$",
                        "",
                        descripcion_resumen,
                    ).strip()

                    imagen_element = noticia.select_one(
                        ".box-image img.wp-post-image, "
                        ".box-image img, "
                        "img"
                    )

                    imagen_listado = obtener_mejor_imagen(
                        imagen_element
                    )

                    fecha_listado = None

                    fecha_element = noticia.select_one(
                        "time[datetime], "
                        ".entry-date[datetime]"
                    )

                    if fecha_element:
                        fecha_listado = parse_fecha_iso(
                            fecha_element.get(
                                "datetime"
                            )
                        )

                    # En ARSA muchas veces la fecha aparece
                    # dentro del resumen.
                    if not fecha_listado:
                        fecha_listado = parse_fecha_texto(
                            descripcion_resumen
                        )

                    logger.info(
                        "Procesando noticia %s/%s: %s",
                        numero,
                        len(noticias),
                        titulo,
                    )

                    detalle = await scrape_detalle_noticia_arsa(
                        client=client,
                        url=url_completa,
                        headers=headers,
                        titulo=titulo,
                    )

                    descripcion = (
                        detalle["description"]
                        or descripcion_resumen
                    )

                    fecha_publicacion = (
                        detalle["presentation_date"]
                        or fecha_listado
                    )

                    imagen_url = (
                        detalle["image_url"]
                        or imagen_listado
                    )

                    item = {
                        "title": titulo,
                        "description": descripcion,
                        "source_type": "Ejecutivo",
                        "category": "Noticias",
                        "country": "Honduras",
                        "source_url": url_completa,
                        "presentation_date": fecha_publicacion,
                        "metadata": {
                            "image_url": imagen_url,
                            "summary_from_listing": (
                                descripcion_resumen
                            ),
                        },
                        "institution": "ARSA Honduras",
                    }

                    items.append(
                        item
                    )

                    # Pausa breve para evitar realizar
                    # demasiadas solicitudes seguidas.
                    await asyncio.sleep(0.3)

                except Exception as exc:
                    logger.exception(
                        "Error procesando la noticia %s: %s",
                        numero,
                        exc,
                    )

            logger.info(
                "Scraping finalizado. "
                "Se obtuvieron %s noticias.",
                len(items),
            )

            return items

        except Exception as exc:
            logger.exception(
                "Error general en el scraper "
                "de ARSA Honduras: %s",
                exc,
            )

            return []


# ============================================================
# EJECUCIÓN DE PRUEBA
# ============================================================

if __name__ == "__main__":
    resultados = asyncio.run(
        scrape_arsa_noti_hn()
    )

    # Convertir los datetime a texto para poder
    # imprimir el resultado como JSON.
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