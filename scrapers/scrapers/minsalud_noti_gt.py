import asyncio
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET
import aiohttp
from bs4 import BeautifulSoup
import json

# mspas.gob.gt bloquea el scraping con un desafío JavaScript de Cloudflare,
# incluyendo sus feeds RSS. Se usa Google News filtrando solo fuentes oficiales
# del Gobierno de Guatemala que publican los comunicados del MSPAS.
QUERY = '(MSPAS OR "Ministerio de Salud Pública") Guatemala when:30d'
FEED_URL = f"https://news.google.com/rss/search?q={quote_plus(QUERY)}&hl=es-419&gl=GT&ceid=GT:es-419"
FUENTES_OFICIALES = {
    "agn.gt": "Agencia Guatemalteca de Noticias",
    "guatemala.gob.gt": "Gobierno de Guatemala",
    "dca.gob.gt": "Diario de Centro América",
    "mspas.gob.gt": "MSPAS",
}

def _dominio_oficial(source_url):
    """Devuelve el dominio oficial que coincide con la URL de la fuente, o None"""
    host = source_url.split("//")[-1].split("/")[0].lower()
    for dominio in FUENTES_OFICIALES:
        if host == dominio or host.endswith("." + dominio):
            return dominio
    return None

async def scrape_minsalud_noti_gt():
    """Noticias del MSPAS Guatemala publicadas por medios oficiales (vía Google News)"""
    print("[MinSalud Noticias_GT] Iniciando scraping...")
    items = []

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(FEED_URL) as response:
                if response.status != 200:
                    print(f"[MSPAS Noticias_GT] ❌ Error HTTP: {response.status}")
                    return []
                xml = await response.read()

        root = ET.fromstring(xml)
        titulos_vistos = set()

        for noticia in root.iter('item'):
            try:
                source_el = noticia.find('source')
                if source_el is None:
                    continue
                dominio = _dominio_oficial(source_el.get('url', ''))
                if not dominio:
                    continue
                fuente = source_el.text.strip() if source_el.text else FUENTES_OFICIALES[dominio]

                # Google News agrega " - <Fuente>" al final del título
                title = noticia.findtext('title', default='').strip()
                sufijo = f" - {fuente}"
                if title.endswith(sufijo):
                    title = title[:-len(sufijo)].strip()
                if not title or title.lower() in titulos_vistos:
                    continue
                titulos_vistos.add(title.lower())

                noticia_url = noticia.findtext('link', default='').strip()

                try:
                    fecha = parsedate_to_datetime(noticia.findtext('pubDate', default='').strip())
                except Exception:
                    fecha = datetime.now()

                # La descripción de Google News es HTML con el título y la fuente
                desc_html = noticia.findtext('description', default='')
                descripcion = BeautifulSoup(desc_html, 'html.parser').get_text(' ', strip=True)
                if not descripcion or descripcion.startswith(title):
                    descripcion = f"{title} ({fuente})"

                items.append({
                    "title": title,
                    "description": descripcion,
                    "source_url": noticia_url,
                    "source_type": "Ejecutivo",
                    "country": "Guatemala",
                    "presentation_date": fecha,
                    "category": "Noticias",
                    "institution": "Ministerio de Salud Guatemala",
                    "metadata": {"fuente": fuente}
                })
                print(f"[MSPAS Noticias_GT] ✅ Procesada: {title[:80]}...")

            except Exception as e:
                print(f"[MSPAS Noticias_GT] ⚠️ Error procesando noticia: {str(e)}")
                continue

        items.sort(key=lambda x: x['presentation_date'], reverse=True)
        print(f"[MSPAS Noticias_GT] 🎯 Total procesadas: {len(items)} noticias")
        return items

    except Exception as e:
        print(f"[MSPAS Noticias_GT] ❌ Error: {str(e)}")
        return []


if __name__ == "__main__":
    noticias = asyncio.run(scrape_minsalud_noti_gt())
    print(json.dumps([{
        **noticia,
        'presentation_date': noticia['presentation_date'].strftime('%Y-%m-%d %H:%M')
    } for noticia in noticias], indent=4, ensure_ascii=False))
