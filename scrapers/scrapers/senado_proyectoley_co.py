import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urljoin
import logging
import json
import re

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


BASE_URL = "https://congresovisible.uniandes.edu.co"
LISTADO_URL = f"{BASE_URL}/proyectos-de-ley/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
MAX_DETALLES_CONCURRENTES = 5


async def _get_con_reintentos(client, url, params=None, intentos=3):
    """Realiza un GET con reintentos, igual que en los demás scrapers."""
    for intento in range(intentos):
        try:
            response = await client.get(url, headers=HEADERS, params=params)
            response.raise_for_status()
            return response
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error(f"Error en el intento {intento + 1} para {url}: {e}")
            if intento == intentos - 1:  # Si es el último intento, propagar el error
                raise
            await asyncio.sleep(1)  # Esperar antes de reintentar


def _parsear_fecha_iso(texto):
    """Convierte 'YYYY-MM-DD' (o ISO con hora) en datetime UTC, tomando solo la parte de la fecha."""
    if not texto:
        return None
    match = re.match(r'\s*(\d{4})-(\d{1,2})-(\d{1,2})', str(texto))
    if not match:
        return None
    try:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)), tzinfo=timezone.utc)
    except ValueError as e:
        logger.warning(f"Fecha ISO inválida: {texto} - {e}")
        return None


def _parsear_fecha_timeline(texto):
    """
    Convierte la fecha de la línea de tiempo del HTML del servidor.
    El servidor la entrega como mes/día/año (ej. '9/23/2026').
    Si el primer número es mayor a 12, se interpreta como día/mes/año.
    """
    if not texto:
        return None
    match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', texto)
    if not match:
        return None
    primero, segundo, anio = int(match.group(1)), int(match.group(2)), int(match.group(3))
    mes, dia = (segundo, primero) if primero > 12 else (primero, segundo)
    try:
        return datetime(anio, mes, dia, tzinfo=timezone.utc)
    except ValueError as e:
        logger.warning(f"Fecha de línea de tiempo inválida: {texto} - {e}")
        return None


def _html_a_texto(html):
    """Limpia etiquetas HTML y normaliza espacios."""
    if not html:
        return None
    texto = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto or None


def _extraer_datos_json(soup):
    """Extrae (fecha, sinopsis) desde el JSON __NEXT_DATA__ de Next.js."""
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return None, None

    try:
        next_data = json.loads(script.string)
    except json.JSONDecodeError as e:
        logger.warning(f"No se pudo parsear __NEXT_DATA__: {e}")
        return None, None

    data = next_data.get("props", {}).get("pageProps", {}).get("data") or {}

    # Fuente principal: fecha_radicacion
    fecha = _parsear_fecha_iso(data.get("fecha_radicacion"))

    # Respaldo: evento 'Radicado' en proyecto_ley_estado
    if not fecha:
        for estado in data.get("proyecto_ley_estado") or []:
            nombre_estado = ((estado.get("tipo_estado") or {}).get("nombre") or "").strip().lower()
            if nombre_estado == "radicado":
                fecha = _parsear_fecha_iso(estado.get("fecha"))
                if fecha:
                    break

    sinopsis = _html_a_texto(data.get("sinopsis"))
    return fecha, sinopsis


def _extraer_datos_html(soup):
    """Respaldo: extrae (fecha, sinopsis) desde el HTML renderizado por el servidor."""
    fecha_radicado = None
    fechas_timeline = []
    for evento in soup.select(".coloquial-timeline > ul > li"):
        fecha_element = evento.select_one(".rowInfo .fecha")
        estado_element = evento.select_one(".rowInfo .estado")
        if not fecha_element:
            continue

        fecha = _parsear_fecha_timeline(fecha_element.get_text(strip=True))
        if not fecha:
            continue
        fechas_timeline.append(fecha)

        estado = estado_element.get_text(" ", strip=True).lower() if estado_element else ""
        if estado.startswith("radicado") and not fecha_radicado:
            fecha_radicado = fecha

    fecha_publicacion = fecha_radicado or (min(fechas_timeline) if fechas_timeline else None)

    sinopsis = None
    sinopsis_element = soup.select_one("section .TextoFormateado")
    if sinopsis_element:
        sinopsis = re.sub(r'\s+', ' ', sinopsis_element.get_text(" ", strip=True)).strip() or None

    return fecha_publicacion, sinopsis


def _extraer_datos_detalle(html):
    """
    Extrae desde el detalle del proyecto la fecha de radicación y la sinopsis.
    Prioriza el JSON __NEXT_DATA__ y usa el HTML como respaldo.
    """
    soup = BeautifulSoup(html, "html.parser")

    fecha, sinopsis = _extraer_datos_json(soup)

    if not fecha or not sinopsis:
        fecha_html, sinopsis_html = _extraer_datos_html(soup)
        fecha = fecha or fecha_html
        sinopsis = sinopsis or sinopsis_html

    return fecha, sinopsis


async def _obtener_datos_detalle(client, semaforo, url):
    """Descarga el detalle de un proyecto y devuelve (fecha, sinopsis)."""
    async with semaforo:
        try:
            response = await _get_con_reintentos(client, url)
            fecha, sinopsis = _extraer_datos_detalle(response.text)
            if not fecha:
                logger.warning(f"No se encontró fecha en el detalle: {url}")
            return fecha, sinopsis
        except Exception as e:
            logger.error(f"Error obteniendo detalle {url}: {e}")
            return None, None


def _parsear_item_listado(item_element):
    """Parsea un bloque .listadoItem del listado."""
    enlace_element = item_element.select_one(".itemHeader h4 a")
    if not enlace_element or not enlace_element.has_attr("href"):
        return None

    texto_completo = enlace_element.get_text(" ", strip=True)
    url_completa = urljoin(LISTADO_URL, enlace_element["href"])

    # Título corto entre corchetes al final: "[Seguridad hídrica y desarrollo rural]"
    titulo_corto = None
    texto_largo = texto_completo
    match = re.search(r'\[([^\]]+)\]\s*$', texto_completo)
    if match:
        titulo_corto = match.group(1).strip()
        texto_largo = texto_completo[:match.start()].strip()

    # ID interno del proyecto (último segmento numérico del link)
    match_id = re.search(r'/(\d+)/?$', enlace_element["href"])
    proyecto_id = match_id.group(1) if match_id else None

    # Sección "Información"
    informacion = {}
    for li in item_element.select(".itemSection .list-avatar li"):
        strong = li.find("strong")
        if not strong:
            continue
        etiqueta = strong.get_text(strip=True).rstrip(":").strip()
        valor = li.get_text(" ", strip=True).replace(strong.get_text(" ", strip=True), "", 1).strip()
        informacion[etiqueta] = valor

    # Sección "Autores"
    autores = []
    for seccion in item_element.select(".itemSection"):
        titulo_seccion = seccion.find("p", class_="title")
        if titulo_seccion and titulo_seccion.get_text(strip=True).lower() == "autores":
            p_autores = titulo_seccion.find_next_sibling("p")
            if p_autores:
                texto_autores = p_autores.get_text(" ", strip=True)
                autores = [a.strip() for a in texto_autores.split(",") if a.strip()]
            break

    # Footer: Estado, No. Cámara, No. Senado
    footer = {}
    for bloque in item_element.select(".itemFooter .with-pdb"):
        valor_element = bloque.find("p", recursive=False)
        etiqueta_element = bloque.select_one(".sub p")
        if etiqueta_element:
            etiqueta = etiqueta_element.get_text(strip=True)
            footer[etiqueta] = valor_element.get_text(strip=True) if valor_element else ""

    return {
        'title': titulo_corto or texto_largo,
        'description': texto_largo,  # Se reemplaza por la sinopsis del detalle si existe
        'source_type': "Legislativo",
        'category': "Proyectos de Ley",
        'country': "Colombia",
        'source_url': url_completa,
        'presentation_date': None,
        'metadata': {
            'id_proyecto': proyecto_id,
            'cuatrienio': informacion.get("Cuatrienio"),
            'legislatura': informacion.get("Legislatura"),
            'iniciativa': informacion.get("Iniciativa"),
            'tipo_proyecto': informacion.get("Tipo de proyecto"),
            'autores': autores,
            'estado': footer.get("ESTADO") or None,
            'numero_camara': footer.get("No. Cámara") or None,
            'numero_senado': footer.get("No. Senado") or None,
        },
        'institution': "Congreso Visible - Universidad de los Andes"
    }


async def scrape_congreso_visible_co():
    """
    Scraper para el listado de proyectos de ley de Congreso Visible (Colombia).
    Recorre solo la primera página y entra al detalle de cada proyecto
    para obtener la fecha de radicación y la sinopsis.
    """
    params = {'page': 1, 'rows': 15, 'search': ''}

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=True) as client:
        try:
            response = await _get_con_reintentos(client, LISTADO_URL, params=params)
            soup = BeautifulSoup(response.text, "html.parser")

            proyectos = soup.select(".listadoItem")
            if not proyectos:
                logger.warning("No se encontraron proyectos en el listado (¿contenido renderizado por JS?)")
                return []

            items = []
            for proyecto in proyectos:
                try:
                    item = _parsear_item_listado(proyecto)
                    if item:
                        items.append(item)
                except Exception as e:
                    logger.error(f"Error procesando un proyecto: {e}")

            # Obtener fecha y sinopsis desde el detalle (con concurrencia limitada)
            semaforo = asyncio.Semaphore(MAX_DETALLES_CONCURRENTES)
            detalles = await asyncio.gather(
                *[_obtener_datos_detalle(client, semaforo, item['source_url']) for item in items]
            )
            for item, (fecha, sinopsis) in zip(items, detalles):
                item['presentation_date'] = fecha
                if sinopsis:
                    item['description'] = sinopsis

            return items

        except Exception as e:
            logger.error(f"Error general en el scraper: {e}")
            return []


# Para pruebas directas
if __name__ == "__main__":
    items = asyncio.run(scrape_congreso_visible_co())
    # Formatear salida como JSON
    print(json.dumps([{
        **item,
        'presentation_date': item['presentation_date'].isoformat() if item['presentation_date'] else None
    } for item in items], indent=4, ensure_ascii=False))