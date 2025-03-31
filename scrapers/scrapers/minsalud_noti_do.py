import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_minsalud_noti_do():
    print("[MSP Noticias_RD] Iniciando scraping...")
    base_url = "https://www.msp.gob.do"
    url = f"{base_url}/web/?page_id=3371"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    async with httpx.AsyncClient() as client:
        try:
            print(f"[MSP Noticias_RD] Accediendo a URL: {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Buscar todas las noticias dentro del widget de entradas recientes
            noticias = soup.select("div.widget_recent_entries ul li")
            if not noticias:
                print("[MSP Noticias_RD] ⚠️ No se encontraron noticias.")
                return []

            items = []

            for noticia in noticias:
                try:
                    # Extraer título y URL
                    link = noticia.find("a")
                    title = link.text.strip()
                    news_url = link["href"]
                    news_url = f"{base_url}{news_url}" if news_url.startswith("/") else news_url

                    # Extraer fecha
                    fecha_element = noticia.find("span", class_="post-date")
                    fecha_str = fecha_element.text.strip() if fecha_element else None
                    fecha = _convert_date(fecha_str)

                    # Crear objeto de noticia
                    item = {
                        "title": title,
                        "description": title,
                        "source_url": news_url,
                        "source_type": "Ejecutivo",
                        "country": "República Dominicana",
                        "presentation_date": fecha,
                        "category": "Noticias",
                        "institution": "Ministerio de Salud República Dominicana",
                        "metadata": json.dumps({"tipo": "Noticia"})
                    }

                    items.append(item)
                    print(f"[MSP Noticias_RD] ✅ Noticia procesada: {title[:100]}")

                except Exception as e:
                    print(f"[MSP Noticias_RD] ⚠️ Error procesando noticia: {str(e)}")
                    continue

            print(f"[MSP Noticias_RD] 🎯 Se encontraron {len(items)} noticias")
            return items

        except Exception as e:
            print(f"[MSP Noticias_RD] ❌ Error: {str(e)}")
            return []

def _convert_date(fecha_str):
    """
    Convierte una fecha de formato '17 febrero, 2025' a 'YYYY-MM-DD'
    """
    try:
        meses = {
            "enero": "01", "febrero": "02", "marzo": "03", "abril": "04", "mayo": "05", "junio": "06",
            "julio": "07", "agosto": "08", "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
        }
        if fecha_str:
            partes = fecha_str.replace(",", "").split()
            dia, mes, anio = partes[0], meses[partes[1].lower()], partes[2]
            return datetime.strptime(f"{anio}-{mes}-{dia}", "%Y-%m-%d").date()
    except Exception as e:
        print(f"[MSP Noticias_RD] ⚠️ Error convirtiendo fecha '{fecha_str}': {e}")
    return None  # Si falla, devolver None

# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados en JSON
#     noticias = asyncio.run(scrape_msp_rd())
#     print(json.dumps([{
#         **noticia,
#         'presentation_date': noticia['presentation_date'].strftime('%Y-%m-%d') if noticia['presentation_date'] else None
#     } for noticia in noticias], indent=4, ensure_ascii=False))
