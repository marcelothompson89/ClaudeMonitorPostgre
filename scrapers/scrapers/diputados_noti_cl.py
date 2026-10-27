import asyncio
import json
from datetime import datetime
from email.utils import parsedate_to_datetime
import aiohttp
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

# camara.cl bloquea el listado HTML de noticias con Cloudflare (403),
# por eso se usa el feed RSS de WordPress, que sí responde.
FEED_URL = "https://www.camara.cl/cms/feed/"

async def scrape_diputados_noti_cl():
    print("[Diputados Noticias Scraper] Iniciando scraping...")
    items = []

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(FEED_URL) as response:
                if response.status != 200:
                    print(f"[Diputados Noticias_CL] Error HTTP: {response.status}")
                    return []
                xml = await response.read()

        root = ET.fromstring(xml)
        for noticia in root.iter('item'):
            try:
                title = noticia.findtext('title', default='').strip()
                url = noticia.findtext('link', default='').strip()

                # La descripción puede traer HTML; se deja solo el texto
                desc_html = noticia.findtext('description', default='')
                description = BeautifulSoup(desc_html, 'html.parser').get_text(' ', strip=True)

                try:
                    date = parsedate_to_datetime(noticia.findtext('pubDate', default='').strip())
                except Exception as e:
                    print(f"[Diputados Noticias_CL] Error procesando fecha: {str(e)}")
                    date = datetime.now()

                img = noticia.find('enclosure')
                img_url = img.get('url') if img is not None else None

                item = {
                    "title": title,
                    "description": description,
                    "source_url": url,
                    "source_type": "Legislativo",
                    "country": "Chile",
                    "presentation_date": date,
                    'category': "Noticias",
                    "institution": 'Cámara de Diputados Chile',
                    "metadata": {
                        "image_url": img_url
                    }
                }
                items.append(item)
            except Exception as e:
                print(f"[Diputados Noticias_CL] Error procesando noticia: {str(e)}")
                continue

        print(f"[Diputados Noticias_CL] Se encontraron {len(items)} noticias")
        return items
    except Exception as e:
        print(f"[Diputados Noticias_CL] Error: {str(e)}")
        return []

if __name__ == "__main__":
    # Ejecutar el scraper y mostrar los resultados en JSON
    noticias = asyncio.run(scrape_diputados_noti_cl())
    print(json.dumps([{
        **noticia,
        'presentation_date': noticia['presentation_date'].strftime('%Y-%m-%d %H:%M') if noticia['presentation_date'] else None
    } for noticia in noticias], indent=4, ensure_ascii=False))
