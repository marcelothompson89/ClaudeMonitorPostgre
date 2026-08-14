"""
Scraper de Normatividad Interna del INVIMA (Colombia).

Extrae SOLO las sub-secciones "Medicamentos" y "Medicamentos oficiales" que
están DENTRO del menú padre "Resoluciones".

IMPORTANTE sobre la estructura del sitio (Odoo):
El acordeón anidado reutiliza los MISMOS id en varias secciones (Acuerdos,
Circulares, Decretos, Leyes, Resoluciones...): p. ej. "Medicamentos" suele ser
"accordion-global-nested-item-8" en más de una. Por eso el cuerpo de cada
cabecera NO se resuelve por id global (soup.find(id=...) devolvería la primera
coincidencia, de otra sección), sino por su hermano directo (find_next_sibling).

Uso:
    python scraper_invima_normatividad_interna.py                 # sitio en vivo
    python scraper_invima_normatividad_interna.py archivo.html    # HTML local
"""

import asyncio
import json
import logging
import re
import sys
import unicodedata
from datetime import datetime

import httpx
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("scraper_invima_ni")

BASE_URL = "https://www.invima.gov.co"
PAGE_URL = f"{BASE_URL}/normatividad/normatividad-interna"

# Constantes de salida (mismo contrato que el scraper de proyectos normativos)
SOURCE_TYPE = "Ejecutivo"
CATEGORY = "Normatividad Interna"
COUNTRY = "Colombia"
INSTITUTION = "INVIMA Colombia"

# Sub-secciones a extraer (normalizadas: minúsculas, sin acentos).
# Se incluye "oficinales" por tolerancia; quitar si solo se quiere "oficiales".
TARGET_SECTIONS = {
    "medicamentos",
    "medicamentos oficiales",
    "medicamentos oficinales",
}

# Menú padre que contiene a las sub-secciones objetivo.
PARENT_SECTION = "resoluciones"

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

DATE_TEXT_RE = re.compile(r"(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})", re.IGNORECASE)
DATE_NUM_RE = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)")
# Año suelto (no dentro de un número más largo como un radicado 2010038231).
YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def clean_ws(text: str) -> str:
    """Normaliza espacios (incluye &nbsp;) y colapsa saltos de línea."""
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def norm(text: str) -> str:
    """Minúsculas y sin acentos, para comparar títulos de sección."""
    s = clean_ws(text).lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def abs_url(href: str) -> str | None:
    href = (href or "").strip()
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return None


def parse_first_date(text: str) -> datetime | None:
    """Devuelve la primera fecha completa (textual o DD/MM/YYYY) del texto."""
    dates: list[tuple[int, datetime]] = []
    for m in DATE_TEXT_RE.finditer(text):
        mon = MESES.get(m.group(2).lower())
        if mon:
            try:
                dates.append((m.start(), datetime(int(m.group(3)), mon, int(m.group(1)))))
            except ValueError:
                pass
    for m in DATE_NUM_RE.finditer(text):
        try:
            dates.append((m.start(), datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))))
        except ValueError:
            pass
    if not dates:
        return None
    return min(dates, key=lambda x: x[0])[1]


def resolve_date(text: str) -> datetime:
    """
    Devuelve SIEMPRE una fecha (la columna es NOT NULL):
    fecha completa -> año (1 de enero) -> fecha de extracción.
    """
    dt = parse_first_date(text)
    if dt:
        return dt
    m = YEAR_RE.search(text)
    if m:
        return datetime(int(m.group(1)), 1, 1)
    return datetime.now()


def strip_quotes(text: str) -> str:
    return clean_ws(text).strip('“”"\'' + " .,-")


# --------------------------------------------------------------------------- #
# Localización de secciones
# --------------------------------------------------------------------------- #
def find_section_headers(root) -> list[Tag]:
    """Cabeceras de acordeón candidatas dentro de un nodo (o del documento)."""
    headers = root.select("a.card-header, a[data-bs-toggle='collapse']")
    seen, out = set(), []
    for h in headers:
        if id(h) not in seen:
            seen.add(id(h))
            out.append(h)
    return out


def get_section_body(header: Tag) -> Tag | None:
    """
    Cuerpo colapsable de una cabecera, resuelto por su HERMANO directo.
    No se usa id global porque el sitio duplica los id entre secciones.
    """
    sib = header.find_next_sibling("div")
    if sib is not None:
        return sib
    card = header.find_parent(class_="card")
    if card is not None:
        return card.find("div", class_="collapse")
    return None


# --------------------------------------------------------------------------- #
# Parseo principal
# --------------------------------------------------------------------------- #
def parse_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    items: list[dict] = []
    seen_urls: set[str] = set()

    # Acotar al cuerpo del menú padre "Resoluciones".
    scope: Tag | None = None
    for header in find_section_headers(soup):
        if norm(header.get_text()) == PARENT_SECTION:
            scope = get_section_body(header)
            break
    if scope is None:
        logger.warning(
            "No se encontró la sección padre '%s'; no se extrae nada.", PARENT_SECTION
        )
        return []

    for header in find_section_headers(scope):
        section_name = clean_ws(header.get_text())
        if norm(section_name) not in TARGET_SECTIONS:
            continue

        body = get_section_body(header)
        if body is None:
            logger.warning("Sub-sección '%s' sin cuerpo asociado", section_name)
            continue

        logger.info("Procesando sub-sección: %s", section_name)

        for a in body.find_all("a", href=True):
            url = abs_url(a["href"])
            if not url or url in seen_urls:
                continue

            anchor_text = clean_ws(a.get_text())
            if not anchor_text:
                continue

            # Descripción = texto del <li> que sigue al enlace (el "Por la cual…")
            li = a.find_parent("li")
            description = ""
            if li:
                full = clean_ws(li.get_text())
                if full.startswith(anchor_text):
                    description = strip_quotes(full[len(anchor_text):])
                else:
                    description = strip_quotes(full)
            if not description:
                description = anchor_text

            seen_urls.add(url)
            items.append({
                # --- claves originales del contrato ---
                "title": anchor_text,
                "description": description,
                "source_type": SOURCE_TYPE,
                "category": CATEGORY,
                "country": COUNTRY,
                "source_url": url,
                "presentation_date": resolve_date(f"{anchor_text} {description}"),
                "institution": INSTITUTION,
                # --- extras (descartables si el esquema es fijo) ---
                "section": section_name,
                "extracted_at": datetime.now(),
            })

    logger.info("Normas extraídas: %d", len(items))
    return items


async def scrape_invima_resoluciones_co() -> list[dict]:
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
    for field in ("presentation_date", "extracted_at"):
        if isinstance(out.get(field), datetime):
            out[field] = out[field].strftime("%Y-%m-%d")
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if len(sys.argv) > 1:  # modo prueba con HTML local
        with open(sys.argv[1], encoding="utf-8") as fh:
            items = parse_html(fh.read())
    else:
        items = asyncio.run(scrape_invima_resoluciones_co())

    print(json.dumps([_serialize(i) for i in items], indent=2, ensure_ascii=False))