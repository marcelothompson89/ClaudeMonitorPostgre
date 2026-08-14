"""
Scraper de Proyectos Normativos del INVIMA (Colombia).

El sitio corre sobre Odoo. La página de proyectos normativos es un único bloque
de contenido plano (una secuencia de <p>, <h2>, <ul>, <ol>) donde cada proyecto
está separado por:
  - un separador <hr> envuelto en <div class="s_hr"> , o
  - un párrafo formado solo por guiones bajos ("______...").

Además, los slugs de /biblioteca/ vienen SIN punto antes de la extensión
(p. ej. "...-publicacionpdf", "...-revisadodocx"), por eso no se filtra por
extensión: se toma cualquier enlace a /biblioteca/.

Uso:
    python scraper_invima.py                 # scrapea el sitio en vivo
    python scraper_invima.py archivo.html    # parsea un HTML local (para pruebas)
"""

import asyncio
import json
import logging
import re
import sys
from datetime import datetime

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger("scraper_invima")

BASE_URL = "https://www.invima.gov.co"
PAGE_URL = f"{BASE_URL}/normatividad/proyectos-normativos"

# Constantes de salida (iguales a tu contrato original)
SOURCE_TYPE = "Ejecutivo"
CATEGORY = "Proyectos Normativos"
COUNTRY = "Colombia"
INSTITUTION = "INVIMA Colombia"

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

DATE_TEXT_RE = re.compile(r"(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})", re.IGNORECASE)
DATE_NUM_RE = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Palabras clave para clasificar fechas como inicio / fin de consulta
START_KW = ("inicio", "inicia", "publicaci", "desde", "apertura", "publicar")
END_KW = ("finaliz", "cierre", "hasta", "plazo", "vence", "final ")

# Detecta el comienzo de un proyecto (para el corte secundario dentro de un bloque)
PROJECT_START_RE = re.compile(
    r"^\s*(?:proyecto\s+de\s+resoluci[oó]n"
    r"|proyecto\s+resoluci[oó]n"
    r"|proyecto\s+de\s+circular"
    r"|publicaci[oó]n\s+para\s+comentarios"
    r"|se\s+publican?\s+el\s+proyecto"
    r"|por\s+medio\s+de\s+la\s+cual"
    r"|en\s+cumplimiento\s+de\s+lo\s+dispuesto)",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def clean_ws(text: str) -> str:
    """Normaliza espacios (incluye &nbsp;) y colapsa saltos de línea."""
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def abs_url(href: str) -> str | None:
    href = (href or "").strip()
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return None


def parse_date_token(day: str, month_token: str, year: str) -> datetime | None:
    try:
        mon = MESES.get(month_token.lower())
        if not mon:
            return None
        return datetime(int(year), mon, int(day))
    except (ValueError, TypeError):
        return None


def find_dates(text: str) -> list[tuple[int, datetime]]:
    """Devuelve [(posición, fecha)] para fechas textuales y numéricas."""
    results: list[tuple[int, datetime]] = []
    for m in DATE_TEXT_RE.finditer(text):
        dt = parse_date_token(m.group(1), m.group(2), m.group(3))
        if dt:
            results.append((m.start(), dt))
    for m in DATE_NUM_RE.finditer(text):
        try:
            results.append((m.start(), datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))))
        except ValueError:
            pass  # p. ej. 31/13/2026
    results.sort(key=lambda x: x[0])
    return results


def extract_period(text: str) -> tuple[datetime | None, datetime | None]:
    """Extrae (inicio, fin) de consulta según palabras clave cercanas."""
    dates = find_dates(text)
    if not dates:
        return None, None

    start = end = None
    for pos, dt in dates:
        window = text[max(0, pos - 45):pos].lower()
        if any(k in window for k in END_KW):
            if end is None:
                end = dt
        elif any(k in window for k in START_KW):
            if start is None:
                start = dt

    # Fallback: si no se pudo clasificar, usar orden de aparición
    ordered = [dt for _, dt in dates]
    if start is None:
        start = ordered[0]
    if end is None and len(ordered) > 1:
        end = ordered[-1]
    return start, end


def extract_email(text: str, tags: list[Tag]) -> str | None:
    # 1) enlaces mailto:
    for tag in tags:
        for a in tag.find_all("a", href=True):
            href = a["href"].lower()
            if href.startswith("mailto:"):
                return href.split(":", 1)[1].split("?")[0].strip()
    # 2) email cercano a "observaciones/correo/comentarios"
    for m in EMAIL_RE.finditer(text):
        window = text[max(0, m.start() - 60):m.start()].lower()
        if any(k in window for k in ("observ", "correo", "comentario", "remitir")):
            return m.group(0)
    # 3) cualquier email de invima
    for m in EMAIL_RE.finditer(text):
        if "invima" in m.group(0).lower():
            return m.group(0)
    # 4) el primero que aparezca
    m = EMAIL_RE.search(text)
    return m.group(0) if m else None


def extract_documents(tags: list[Tag]) -> list[dict]:
    docs: list[dict] = []
    seen: set[str] = set()
    for tag in tags:
        for a in tag.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().startswith("mailto:"):
                continue
            # descartar hrefs con email mal formados (http://correo@dominio)
            if "@" in href and "/biblioteca/" not in href:
                continue
            url = abs_url(href)
            if not url or url in seen:
                continue
            seen.add(url)
            docs.append({"text": clean_ws(a.get_text()), "url": url})
    return docs


def pick_main_url(docs: list[dict]) -> str | None:
    prefixes = ("proyecto de resoluci", "proyecto de circular", "proyecto resoluci")
    for d in docs:
        if d["text"].lower().startswith(prefixes):
            return d["url"]
    for d in docs:
        if "proyecto" in d["text"].lower():
            return d["url"]
    return docs[0]["url"] if docs else None


def detect_kind(text: str) -> str:
    t = text.lower()
    if "proyecto de circular" in t or "proyecto de acto administrativo" in t:
        return "Proyecto de Circular"
    if "proyecto de resoluci" in t or "proyecto resoluci" in t:
        return "Proyecto de Resolución"
    if "circular" in t:
        return "Proyecto de Circular"
    if "resoluci" in t:
        return "Proyecto de Resolución"
    return "Proyecto Normativo"


def extract_title(block_text: str, tags: list[Tag]) -> str:
    # 1) primer texto entrecomillado (con comillas tipográficas o rectas)
    m = re.search(r'[“"]([^”"]{15,400})[”"]', block_text)
    if m:
        title = clean_ws(m.group(1))
        kind = detect_kind(block_text)
        if kind.split()[-1].lower() not in title.lower():
            return f"{kind}: {title}"
        return title
    # 2) primer encabezado h1/h2/h3 del bloque
    for tag in tags:
        heading = tag if tag.name in ("h1", "h2", "h3") else tag.find(["h1", "h2", "h3"])
        if heading and heading.get_text(strip=True):
            return clean_ws(heading.get_text())
    # 3) primera oración significativa
    first = clean_ws(block_text)
    return (first[:200] + "…") if len(first) > 200 else first


# --------------------------------------------------------------------------- #
# Segmentación en bloques
# --------------------------------------------------------------------------- #
def find_content_container(soup: BeautifulSoup) -> Tag:
    node = soup.select_one("div.s_allow_columns")
    if node:
        return node
    # Fallback: el contenedor con más enlaces a /biblioteca/
    best, best_count = None, 0
    for div in soup.find_all(["div", "section", "article"]):
        count = len(div.select('a[href*="/biblioteca/"]'))
        if count > best_count:
            best, best_count = div, count
    return best or soup.body or soup


def is_separator(node) -> bool:
    if not isinstance(node, Tag):
        return False
    if node.name == "hr":
        return True
    # <div class="s_hr"> ... <hr> ... </div>
    if node.find("hr") is not None and clean_ws(node.get_text()) == "":
        return True
    # párrafo de guiones bajos
    text = clean_ws(node.get_text())
    if text and set(text) <= {"_"} and len(text) >= 8:
        return True
    return False


def split_top_level(container: Tag) -> list[list[Tag]]:
    """Corte primario por separadores (<hr> y párrafos de guiones bajos)."""
    blocks: list[list[Tag]] = []
    current: list[Tag] = []
    for child in container.children:
        if isinstance(child, NavigableString):
            continue
        if not isinstance(child, Tag):
            continue
        if is_separator(child):
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(child)
    if current:
        blocks.append(current)
    return blocks


def split_projects_within(block: list[Tag]) -> list[list[Tag]]:
    """
    Corte secundario: dentro de un bloque, inicia un proyecto nuevo cuando un
    párrafo arranca con un patrón de proyecto Y el sub-bloque actual ya tiene al
    menos un documento (evita partir el propio título antes de sus enlaces).
    """
    subblocks: list[list[Tag]] = []
    current: list[Tag] = []
    current_has_doc = False

    for tag in block:
        tag_text = clean_ws(tag.get_text())
        # Un inicio de proyecto real es una frase, no una etiqueta corta de enlace
        # (evita partir en anclas como "Proyecto de Circular").
        starts_project = bool(PROJECT_START_RE.match(tag_text)) and len(tag_text) > 40
        if starts_project and current and current_has_doc:
            subblocks.append(current)
            current = []
            current_has_doc = False
        current.append(tag)
        if not current_has_doc and tag.select('a[href*="/biblioteca/"]'):
            current_has_doc = True

    if current:
        subblocks.append(current)
    return subblocks


# --------------------------------------------------------------------------- #
# Parseo principal
# --------------------------------------------------------------------------- #
def parse_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    container = find_content_container(soup)
    logger.info("Contenedor: <%s class=%s>", container.name, container.get("class"))

    primary = split_top_level(container)
    logger.info("Bloques primarios: %d", len(primary))

    items: list[dict] = []
    seen: set[tuple[str, str | None]] = set()

    for block in primary:
        for sub in split_projects_within(block):
            docs = extract_documents(sub)
            if not docs:
                continue  # sin documentos => no es un proyecto publicable

            # get_text() por tag (sin separador) preserva números partidos por
            # etiquetas inline como "3<b>1 de julio…"; el espacio va entre tags.
            block_text = clean_ws(" ".join(t.get_text() for t in sub))
            title = extract_title(block_text, sub)
            main_url = pick_main_url(docs) or PAGE_URL
            start, end = extract_period(block_text)
            email = extract_email(block_text, sub)

            key = (title, main_url)
            if key in seen:
                continue
            seen.add(key)

            # Descripción: texto del bloque recortado + documentos
            description = block_text[:600] + ("…" if len(block_text) > 600 else "")
            if email:
                description += f" | Correo observaciones: {email}"

            item = {
                # --- claves originales de tu contrato ---
                "title": title,
                "description": description,
                "source_type": SOURCE_TYPE,
                "category": CATEGORY,
                "country": COUNTRY,
                # source_url apunta al documento principal (antes: página)
                "source_url": main_url,
                # presentation_date = inicio de consulta (antes: datetime.now())
                "presentation_date": start,
                "institution": INSTITUTION,
                # --- extras (descartables si tu esquema es fijo) ---
                "consultation_start": start,
                "consultation_end": end,
                "contact_email": email,
                "documents": docs,
                "extracted_at": datetime.now(),
            }
            items.append(item)

    logger.info("Proyectos extraídos: %d", len(items))
    return items


async def scrape_invima_proyectos_normativos_co() -> list[dict]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
        try:
            resp = await client.get(PAGE_URL)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("Error al obtener la página: %s", e)
            return []
    return parse_html(resp.text)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _serialize(item: dict) -> dict:
    out = dict(item)
    for field in ("presentation_date", "consultation_start", "consultation_end", "extracted_at"):
        if isinstance(out.get(field), datetime):
            out[field] = out[field].strftime("%Y-%m-%d")
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if len(sys.argv) > 1:  # modo prueba con HTML local
        with open(sys.argv[1], encoding="utf-8") as fh:
            items = parse_html(fh.read())
    else:
        items = asyncio.run(scrape_invima_proyectos_normativos_co())

    print(json.dumps([_serialize(i) for i in items], indent=2, ensure_ascii=False))