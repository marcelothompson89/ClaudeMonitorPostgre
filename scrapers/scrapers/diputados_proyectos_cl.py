import asyncio
from datetime import datetime
import aiohttp
import xml.etree.ElementTree as ET
import json

# camara.cl bloquea el scraping del listado HTML con Cloudflare (403),
# por eso se usa el servicio de Datos Abiertos de la Cámara.
API_URL = "https://opendata.camara.cl/camaradiputados/WServices/WSLegislativo.asmx"
DETALLE_URL = "https://www.camara.cl/legislacion/ProyectosDeLey/tramitacion.aspx?prmID={id}&prmBOLETIN={boletin}"
NS = {'c': 'http://opendata.camara.cl/camaradiputados/v1'}
MAX_ITEMS = 50

async def _fetch_proyectos(session, metodo, anio):
    url = f"{API_URL}/{metodo}?prmAnno={anio}"
    async with session.get(url) as response:
        if response.status != 200:
            print(f"[Diputados Proyectos_CL] Error HTTP {response.status} en {metodo}")
            return []
        root = ET.fromstring(await response.read())
        return root.findall('c:ProyectoLey', NS)

async def scrape_diputados_proyectos_cl():
    print("[Diputados Proyectos_CL] Iniciando scraping...")
    items = []
    anio = datetime.now().year

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            resultados = await asyncio.gather(
                _fetch_proyectos(session, 'retornarMensajesXAnno', anio),
                _fetch_proyectos(session, 'retornarMocionesXAnno', anio),
            )

        for proyecto in [p for lista in resultados for p in lista]:
            try:
                proyecto_id = proyecto.findtext('c:Id', default='', namespaces=NS).strip()
                boletin = proyecto.findtext('c:NumeroBoletin', default='', namespaces=NS).strip()
                titulo = proyecto.findtext('c:Nombre', default='', namespaces=NS).strip()
                tipo = proyecto.findtext('c:TipoIniciativa', default='No especificado', namespaces=NS).strip()
                camara_origen = proyecto.findtext('c:CamaraOrigen', default='No especificado', namespaces=NS).strip()
                fecha_str = proyecto.findtext('c:FechaIngreso', default='', namespaces=NS).strip()

                if not titulo:
                    continue

                try:
                    fecha = datetime.fromisoformat(fecha_str)
                except ValueError:
                    print(f"[Diputados Proyectos_CL] Error procesando fecha {fecha_str}")
                    fecha = datetime.now()

                items.append({
                    "title": titulo,
                    "description": f"Boletín: {boletin} - Tipo: {tipo} - Cámara de origen: {camara_origen}",
                    "source_url": DETALLE_URL.format(id=proyecto_id, boletin=boletin),
                    "source_type": "Legislativo",
                    "country": "Chile",
                    "presentation_date": fecha,
                    "category": "Proyecto de Ley",
                    "institution": "Cámara de Diputados Chile",
                    "metadata": {
                        "boletin": boletin,
                        "tipo": tipo,
                        "camara_origen": camara_origen
                    }
                })
            except Exception as e:
                print(f"[Diputados Proyectos_CL] Error procesando proyecto: {str(e)}")
                continue

        # Solo los proyectos más recientes
        items.sort(key=lambda x: x['presentation_date'], reverse=True)
        items = items[:MAX_ITEMS]

        print(f"[Diputados Proyectos_CL] Se encontraron {len(items)} proyectos")
        return items
    except Exception as e:
        print(f"[Diputados Proyectos_CL] Error: {str(e)}")
        return []

if __name__ == "__main__":
    # Ejecutar el scraper y mostrar los resultados en JSON
    proyectos = asyncio.run(scrape_diputados_proyectos_cl())
    print(json.dumps([{
        **proyecto,
        'presentation_date': proyecto['presentation_date'].strftime('%Y-%m-%d') if proyecto['presentation_date'] else None
    } for proyecto in proyectos], indent=4, ensure_ascii=False))
