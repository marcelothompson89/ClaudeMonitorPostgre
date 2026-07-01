import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
import json
import re


BASE_URL = "https://www.invima.gov.co"
START_URL = "https://www.invima.gov.co/blog/sala-de-prensa-13"


def parse_fecha_invima(fecha_texto):
    if not fecha_texto:
        return None

    fecha_texto = fecha_texto.strip()

    formatos = [
        "%d/%m/%Y",
        "%d/%m/%y",
    ]

    for formato in formatos:
        try:
            return datetime.strptime(fecha_texto, formato)
        except ValueError:
            continue

    return None


def extraer_imagen_desde_style(style):
    if not style:
        return None

    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)

    if not match:
        return None

    return urljoin(BASE_URL, match.group(1))


async def scrape_detalle_noticia(client, url):
    """
    Entra a una noticia individual y extrae el cuerpo completo.
    """
    try:
        response = await client.get(url)

        if response.status_code != 200:
            print(f"Error detalle: no se pudo acceder a {url}. Código {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup.select("script, style, nav, header, footer, aside, form"):
            tag.decompose()

        posibles_contenedores = [
            "#o_wblog_post_content",
            ".o_wblog_post_content",
            "div[itemprop='articleBody']",
            "article",
            "main",
        ]

        texto = None

        for selector in posibles_contenedores:
            contenedor = soup.select_one(selector)

            if contenedor:
                bloques = []

                for elemento in contenedor.select("p, li, h2, h3, h4"):
                    contenido = elemento.get_text(" ", strip=True)

                    if contenido:
                        bloques.append(contenido)

                if bloques:
                    texto = "\n".join(bloques)
                    break

        if not texto:
            main = soup.select_one("main") or soup.body
            texto = main.get_text("\n", strip=True) if main else None

        if not texto:
            return None

        textos_a_ignorar = [
            "Todos los blogs",
            "Sala de prensa",
            "Leer siguiente",
            "Sobre nosotros",
            "Síganos",
            "Cancelar suscripción",
            "Suscribirse",
            "Sede principal",
            "Teléfono conmutador",
            "Línea anticorrupción",
            "Horario de atención",
            "Notificaciones Judiciales",
            "Transparencia Invima",
            "Redes sociales",
            "© 2026 INVIMA",
        ]

        lineas_limpias = []

        for linea in texto.splitlines():
            linea = linea.strip()

            if not linea:
                continue

            if any(t.lower() in linea.lower() for t in textos_a_ignorar):
                continue

            lineas_limpias.append(linea)

        return "\n".join(lineas_limpias).strip()

    except Exception as e:
        print(f"Error procesando detalle {url}: {e}")
        return None


async def scrape_invima_noticias_co(max_pages=1):
    """
    Scraper para la nueva página de Sala de Prensa de INVIMA.
    Entra al listado y luego a cada noticia para extraer descripción completa.
    """
    items = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(
        headers=headers,
        timeout=30,
        follow_redirects=True
    ) as client:

        for page in range(1, max_pages + 1):
            url = START_URL if page == 1 else f"{START_URL}/page/{page}"

            try:
                response = await client.get(url)

                if response.status_code != 200:
                    print(f"Error: no se pudo acceder a {url}. Código {response.status_code}")
                    continue

                soup = BeautifulSoup(response.text, "html.parser")

                noticias = soup.select('article[name="blog_post"]')

                if not noticias:
                    print(f"No se encontraron noticias en {url}")
                    continue

                for noticia in noticias:
                    try:
                        titulo_element = noticia.select_one("a.o_blog_post_title")

                        if not titulo_element:
                            continue

                        titulo = titulo_element.get_text(strip=True)

                        href = titulo_element.get("href")
                        url_completa = urljoin(BASE_URL, href) if href else None

                        descripcion_element = noticia.select_one(
                            ".card-body .mt-2.o_wblog_normalize_font"
                        )

                        descripcion_resumen = (
                            descripcion_element.get_text(" ", strip=True)
                            if descripcion_element
                            else "Sin Descripción"
                        )

                        fecha_element = noticia.select_one("time")
                        fecha_publicacion = None

                        if fecha_element:
                            fecha_texto = fecha_element.get_text(strip=True)
                            fecha_publicacion = parse_fecha_invima(fecha_texto)

                        imagen_url = None

                        cover_image = noticia.select_one(".o_record_cover_image")

                        if cover_image:
                            imagen_url = extraer_imagen_desde_style(
                                cover_image.get("style")
                            )

                        if not imagen_url:
                            imagen_element = noticia.select_one("img")

                            if imagen_element and imagen_element.get("src"):
                                imagen_url = urljoin(BASE_URL, imagen_element["src"])

                        descripcion_detalle = None

                        if url_completa:
                            descripcion_detalle = await scrape_detalle_noticia(
                                client,
                                url_completa
                            )

                        descripcion = descripcion_detalle or descripcion_resumen

                        item = {
                            "title": titulo,
                            "description": descripcion,
                            "source_type": "Ejecutivo",
                            "category": "Noticias",
                            "country": "Colombia",
                            "source_url": url_completa,
                            "presentation_date": fecha_publicacion,
                            "metadata": {
                                "image_url": imagen_url,
                                "source_page": url,
                                "summary_from_listing": descripcion_resumen,
                            },
                            "institution": "INVIMA Colombia",
                        }

                        items.append(item)

                    except Exception as e:
                        print(f"Error procesando una noticia en {url}: {e}")

            except Exception as e:
                print(f"Error al realizar la solicitud a {url}: {e}")

    items_deduplicados = []
    urls_vistas = set()

    for item in items:
        source_url = item.get("source_url")

        if source_url and source_url in urls_vistas:
            continue

        if source_url:
            urls_vistas.add(source_url)

        items_deduplicados.append(item)

    return items_deduplicados


if __name__ == "__main__":
    items = asyncio.run(scrape_invima_noticias_co(max_pages=1))

    print(json.dumps([
        {
            **item,
            "presentation_date": (
                item["presentation_date"].strftime("%Y-%m-%d")
                if item["presentation_date"]
                else None
            )
        }
        for item in items
    ], indent=4, ensure_ascii=False))