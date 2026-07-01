import asyncio
import argparse
import json
import os
import re
import html
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, date
from email.utils import parsedate_to_datetime
from urllib.parse import quote


# -----------------------------------------------------------------------------
# Configuración
# -----------------------------------------------------------------------------
# En vez de pegarle al RSS oficial de SICA (bloqueado por Cloudflare), usamos
# el RSS de Google News filtrando por el sitio. Google ya indexa sica.int
# (robots.txt: Googlebot Allow, search=yes, use=reference), así que esta vía
# es estable, gratuita y coherente con lo que SICA declara permitir.
#
# El "link" que devuelve Google News es un redirect de news.google.com que,
# al abrirlo, lleva a la noticia real en sica.int. Se guarda tal cual en
# source_url (funciona al hacer click). El dominio real queda en metadata.
# -----------------------------------------------------------------------------

GOOGLE_NEWS_BASE = "https://news.google.com/rss/search"

DEFAULT_QUERY = os.getenv("SICA_GNEWS_QUERY", "site:sica.int")
GNEWS_HL = os.getenv("SICA_GNEWS_HL", "es-419")       # idioma de la interfaz
GNEWS_GL = os.getenv("SICA_GNEWS_GL", "US")           # país
GNEWS_CEID = os.getenv("SICA_GNEWS_CEID", "US:es-419")  # país:idioma de edición


def _build_gnews_url(query, hl=GNEWS_HL, gl=GNEWS_GL, ceid=GNEWS_CEID):
    return (
        f"{GOOGLE_NEWS_BASE}"
        f"?q={quote(query)}"
        f"&hl={hl}"
        f"&gl={gl}"
        f"&ceid={ceid}"
    )


def _descargar_rss(url):
    """
    Descarga el XML del RSS de Google News. Google News no está detrás de
    Cloudflare, así que un request simple con headers de navegador alcanza.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
            return content.decode("utf-8", errors="replace")

    except urllib.error.HTTPError as e:
        print(f"[SICA GNews] ❌ Error HTTP descargando RSS: {e.code} - {e.reason}")
        print(f"[SICA GNews] URL usada: {url}")
        return None

    except urllib.error.URLError as e:
        print(f"[SICA GNews] ❌ Error de conexión descargando RSS: {e.reason}")
        return None

    except Exception as e:
        print(f"[SICA GNews] ❌ Error inesperado descargando RSS: {e}")
        return None


def _clean_html(raw_html):
    if not raw_html:
        return ""

    text = html.unescape(raw_html)
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_child(parent, tag_name):
    """Devuelve el primer sub-elemento cuyo tag (sin namespace) coincida."""
    for child in list(parent):
        clean_tag = child.tag.split("}")[-1].lower()
        if clean_tag == tag_name.lower():
            return child
    return None


def _get_child_text(parent, tag_name):
    child = _get_child(parent, tag_name)
    if child is None:
        return ""
    return (child.text or "").strip()


def _parse_date(date_value):
    if not date_value:
        return None

    value = date_value.strip()

    try:
        return parsedate_to_datetime(value).date()
    except Exception:
        pass

    try:
        clean_value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_value).date()
    except Exception:
        pass

    for formato in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, formato).date()
        except Exception:
            continue

    print(f"[SICA GNews] ⚠️ No se pudo parsear la fecha: {date_value}")
    return None


def _parse_fecha_param(fecha):
    if fecha is None:
        return None
    if isinstance(fecha, date):
        return fecha
    if isinstance(fecha, str):
        return datetime.strptime(fecha, "%Y-%m-%d").date()
    raise ValueError(f"Formato de fecha no soportado: {fecha}")


def _limpiar_titulo(title, source_name):
    """
    Google News suele agregar ' - Nombre del medio' al final del título.
    Si el sufijo coincide con la fuente, se lo saca.
    """
    if not title:
        return ""

    title = title.strip()

    if source_name:
        sufijo = f" - {source_name.strip()}"
        if title.endswith(sufijo):
            return title[: -len(sufijo)].strip()

    # Fallback genérico: cortar el último ' - X' si parece ser el medio.
    match = re.match(r"^(.*)\s+-\s+[^-]{2,60}$", title)
    if match:
        return match.group(1).strip()

    return title


def _parsear_items_rss(xml_text):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"[SICA GNews] ❌ Error parseando XML: {e}")
        return []

    return [
        elem for elem in root.iter()
        if elem.tag.split("}")[-1].lower() == "item"
    ]


async def scrape_sica_noticias_cam(
    fecha_objetivo=None,
    fecha_desde=None,
    fecha_hasta=None,
    query=DEFAULT_QUERY,
    hl=GNEWS_HL,
    gl=GNEWS_GL,
    ceid=GNEWS_CEID,
):
    print("[SICA GNews] Iniciando scraping vía Google News RSS...")

    fecha_objetivo = _parse_fecha_param(fecha_objetivo)
    fecha_desde = _parse_fecha_param(fecha_desde)
    fecha_hasta = _parse_fecha_param(fecha_hasta)

    if fecha_objetivo:
        fecha_desde = fecha_objetivo
        fecha_hasta = fecha_objetivo

    url = _build_gnews_url(query, hl=hl, gl=gl, ceid=ceid)
    print(f"[SICA GNews] Query: {query}")
    print(f"[SICA GNews] URL: {url}")

    xml_text = _descargar_rss(url)
    if not xml_text:
        print("[SICA GNews] No se pudo descargar el RSS.")
        return []

    if "<rss" not in xml_text.lower() and "<feed" not in xml_text.lower():
        print("[SICA GNews] ⚠️ La respuesta no parece un RSS/XML válido.")
        print(xml_text[:500])
        return []

    rss_items = _parsear_items_rss(xml_text)
    if not rss_items:
        print("[SICA GNews] ⚠️ No se encontraron items. Probá ampliar la query "
              "(ej. 'SICA Centroamérica' en vez de 'site:sica.int').")
        return []

    print(f"[SICA GNews] Items encontrados en el feed: {len(rss_items)}")

    items = []
    vistos = set()

    for i, entry in enumerate(rss_items, start=1):
        try:
            title_raw = _get_child_text(entry, "title")
            link = _get_child_text(entry, "link")
            guid = _get_child_text(entry, "guid")
            pub_date_raw = _get_child_text(entry, "pubDate")
            description_raw = _get_child_text(entry, "description")

            # <source url="https://www.sica.int">SICA</source>
            source_el = _get_child(entry, "source")
            source_name = (source_el.text or "").strip() if source_el is not None else ""
            source_domain = ""
            if source_el is not None:
                source_domain = (source_el.get("url") or "").strip()

            pub_date = _parse_date(pub_date_raw)

            if fecha_desde and pub_date and pub_date < fecha_desde:
                continue
            if fecha_hasta and pub_date and pub_date > fecha_hasta:
                continue

            title = _limpiar_titulo(title_raw, source_name)
            if not title:
                print(f"[SICA GNews] ⚠️ Item {i} sin título. Se omite.")
                continue

            # Dedup por título normalizado
            clave = title.lower()
            if clave in vistos:
                continue
            vistos.add(clave)

            description = _clean_html(description_raw) or title

            item = {
                "title": title,
                "description": description,
                "source_url": link or guid,
                "source_type": "SICA",
                "country": "Centroamérica",
                "presentation_date": pub_date,
                "category": "Noticias",
                "institution": "Sistema de la Integración Centroamericana",
                "metadata": json.dumps({
                    "tipo": "Noticia SICA (vía Google News RSS)",
                    "publisher": source_name,
                    "publisher_domain": source_domain,
                    "google_news_link": link,
                    "guid": guid,
                    "published_raw": pub_date_raw,
                    "query": query,
                }, ensure_ascii=False),
            }

            items.append(item)
            print(f"[SICA GNews] ✅ Noticia extraída: {title[:80]}")

        except Exception as e:
            print(f"[SICA GNews] ⚠️ Error procesando item {i}: {e}")
            continue

    print(f"[SICA GNews] 🎯 Se encontraron {len(items)} noticias luego del filtro.")
    return items


def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.strftime("%Y-%m-%d")
    return str(obj)


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Scraper SICA Noticias vía Google News RSS"
    )
    parser.add_argument("--fecha", default=None,
                        help="Fecha exacta YYYY-MM-DD. Ej: --fecha 2026-06-25")
    parser.add_argument("--desde", default=None,
                        help="Desde fecha YYYY-MM-DD. Ej: --desde 2026-06-20")
    parser.add_argument("--hasta", default=None,
                        help="Hasta fecha YYYY-MM-DD. Ej: --hasta 2026-06-25")
    parser.add_argument("--query", default=DEFAULT_QUERY,
                        help="Query de Google News. Default: site:sica.int")
    parser.add_argument("--hl", default=GNEWS_HL, help="Idioma (default es-419)")
    parser.add_argument("--gl", default=GNEWS_GL, help="País (default US)")
    parser.add_argument("--ceid", default=GNEWS_CEID,
                        help="País:idioma de edición (default US:es-419)")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    noticias = asyncio.run(
        scrape_sica_noticias_cam(
            fecha_objetivo=args.fecha,
            fecha_desde=args.desde,
            fecha_hasta=args.hasta,
            query=args.query,
            hl=args.hl,
            gl=args.gl,
            ceid=args.ceid,
        )
    )

    print(json.dumps(noticias, indent=4, ensure_ascii=False, default=_json_default))