import asyncio
import httpx
from datetime import datetime
import json


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

BASE = "https://www.gov.br"
# Endpoint real que usa el frontend Volto (Plone REST API vía traversal ++api++)
API_URL = f"{BASE}/anvisa/++api++/pt-br/assuntos/noticias-anvisa/@querystring-search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Cantidad de noticias a traer (una sola página)
B_SIZE = 30

# Cuerpo de @querystring-search: filtra por "News Item", ordena por fecha
# efectiva descendente y pide los metadatos que necesitamos.
QUERY_BODY = {
    "query": [
        {
            "i": "portal_type",
            "o": "plone.app.querystring.operation.selection.any",
            "v": ["News Item"],
        }
    ],
    "b_size": B_SIZE,
    "sort_on": "effective",
    "sort_order": "descending",
    "metadata_fields": ["effective", "Description", "Subject", "subtitle"],
    "fullobjects": False,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_iso(value):
    """Parsea una fecha ISO (con o sin zona) a datetime naive."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None


def _to_public_url(api_id):
    """
    Convierte la URL de la API en la URL pública navegable.
    (El @id de este endpoint ya viene sin ++api++, pero lo dejamos robusto.)
    """
    if not api_id:
        return ""
    url = api_id.replace("/++api++", "")
    if not url.startswith("http"):
        url = f"{BASE}{url}"
    return url


def _build_item(result):
    """Mapea un resultado de la API al esquema del pipeline."""
    titulo = result.get("title") or "Sin título"

    # description = subtitle + "|" + description (formato del scraper original)
    subtitulo = (result.get("subtitle") or "").strip()
    descripcion = (result.get("description") or result.get("Description") or "").strip()
    if not subtitulo:
        subtitulo = "Sin subtítulo"
    if not descripcion:
        descripcion = "Sin descripción"
    description = f"{subtitulo}|{descripcion}"

    source_url = _to_public_url(result.get("@id") or result.get("getURL"))
    fecha = _parse_iso(result.get("effective"))

    subjects = result.get("Subject") or []
    if isinstance(subjects, list) and subjects:
        etiquetas = ", ".join(str(s) for s in subjects)
    else:
        etiquetas = "Sin etiquetas"

    return {
        "title": titulo,
        "description": description,
        "source_type": "Ejecutivo",
        "category": "Noticias",
        "country": "Brasil",
        "source_url": source_url,
        "presentation_date": fecha,  # objeto datetime o None
        "metadata": {"tags": etiquetas},
        "institution": "ANVISA Brasil",
    }


# ---------------------------------------------------------------------------
# Scraper principal
# ---------------------------------------------------------------------------

async def scrape_anvisa_noti_br():
    """
    Extrae noticias de ANVISA desde el endpoint @querystring-search de la
    Plone REST API (POST, formato plone.app.querystring).
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=True) as client:
        for intento in range(3):
            try:
                resp = await client.post(API_URL, headers=HEADERS, json=QUERY_BODY)
                resp.raise_for_status()
                data = resp.json()

                resultados = data.get("items", []) if isinstance(data, dict) else []
                items = []
                for r in resultados:
                    try:
                        items.append(_build_item(r))
                    except Exception as e:
                        print(f"Error procesando resultado: {e}")

                print(f"{len(items)} noticias obtenidas.")
                return items

            except httpx.HTTPStatusError as e:
                print(f"HTTP {e.response.status_code} en intento {intento + 1}.")
                break  # error del servidor: no tiene sentido reintentar el mismo request
            except (httpx.RequestError, json.JSONDecodeError, ValueError) as e:
                print(f"Error en intento {intento + 1}: {e}")

        print("No se pudieron obtener noticias.")
        return []


# ---------------------------------------------------------------------------
# Ejecución directa
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    items = asyncio.run(scrape_anvisa_noti_br())

    print(json.dumps(
        [
            {
                **item,
                "presentation_date": (
                    item["presentation_date"].strftime("%Y-%m-%d")
                    if item["presentation_date"] else None
                ),
            }
            for item in items
        ],
        indent=4,
        ensure_ascii=False,
    ))