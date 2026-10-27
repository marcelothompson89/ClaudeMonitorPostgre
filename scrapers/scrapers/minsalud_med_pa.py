import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import json

async def scrape_minsa_med_pa():
    print("[MINSA Alertas_PA] Iniciando scraping...")
    base_url = "https://www.minsa.gob.pa"
    # La antigua URL /informacion-salud/alertas-y-comunicados redirige aquí
    url = f"{base_url}/publicacion/notas-de-seguridad-de-medicamentos"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }

    try:
        print(f"[MINSA Alertas_PA] Accediendo a URL: {url}")
        async with httpx.AsyncClient(headers=headers, timeout=60, follow_redirects=True, verify=False) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Cada nota es un <article> dentro de div.views-row
        alertas = soup.select("div.view-content div.views-row article")
        if not alertas:
            print("[MINSA Alertas_PA] ⚠️ No se encontraron alertas.")
            return []

        items = []

        for alerta in alertas:
            try:
                # Extraer título y URL (normalmente un PDF)
                link = alerta.select_one("a.list--entity__title-link")
                if not link:
                    continue

                title = link.get_text(" ", strip=True)
                alerta_url = link["href"]
                alerta_url = f"{base_url}{alerta_url}" if alerta_url.startswith("/") else alerta_url

                # Extraer fecha, p.ej. "Jueves, 28 de Agosto de 2025"
                fecha_element = alerta.select_one("span.text-date")
                fecha = _parse_date(fecha_element.get_text(strip=True)) if fecha_element else datetime.now().date()

                # Crear objeto de alerta
                item = {
                    "title": title,
                    "description": title,
                    "source_url": alerta_url,
                    "source_type": "Ejecutivo",
                    "country": "Panamá",
                    "presentation_date": fecha,
                    "category": "Notas medicamentos",
                    "institution": "Ministerio de Salud Panamá",
                    "metadata": json.dumps({"tipo": "Nota de Seguridad"})
                }

                items.append(item)
                print(f"[MINSA Alertas_PA] ✅ Alerta procesada: {title[:100]}")

            except Exception as e:
                print(f"[MINSA Alertas_PA] ⚠️ Error procesando alerta: {str(e)}")
                continue

        print(f"[MINSA Alertas_PA] 🎯 Se encontraron {len(items)} alertas")
        return items

    except Exception as e:
        print(f"[MINSA Alertas_PA] ❌ Error: {str(e)}")
        return []


def _parse_date(fecha_str):
    """
    Convierte fechas en español como "Jueves, 28 de Agosto de 2025" a formato date.
    Si falla, usa la fecha actual.
    """
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
        'noviembre': 11, 'diciembre': 12
    }

    try:
        # Quitar el día de la semana si viene ("Jueves, ...")
        if "," in fecha_str:
            fecha_str = fecha_str.split(",", 1)[1]
        partes = [p for p in fecha_str.split() if p.lower() != "de"]
        dia, mes, anio = partes
        mes_num = meses[mes.lower()]
        return datetime(int(anio), mes_num, int(dia)).date()
    except Exception as e:
        print(f"[MINSA Alertas_PA] ⚠️ Error procesando fecha '{fecha_str}', se usará la fecha actual: {e}")
        return datetime.now().date()


# if __name__ == "__main__":
#     # Ejecutar el scraper y mostrar los resultados en JSON
#     alertas = asyncio.run(scrape_minsa_med_pa())
#     print(json.dumps([{
#         **alerta,
#         'presentation_date': alerta['presentation_date'].strftime('%Y-%m-%d') if alerta['presentation_date'] else None
#     } for alerta in alertas], indent=4, ensure_ascii=False))
