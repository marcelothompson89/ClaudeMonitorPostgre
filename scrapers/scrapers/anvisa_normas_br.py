from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
import json

async def scrape_anvisa_legis_dom():
    """
    Scraper que renderiza el JavaScript completo en Playwright usando
    el navegador Chrome instalado localmente para evitar detección.
    Extrae los <article class="ato"> del DOM ya pintado.
    """
    base_url = "https://anvisalegis.datalegis.net"
    open_url = (
        f"{base_url}/action/ActionDatalegis.php"
        f"?acao=abrirEmentario&cod_modulo=293&cod_menu=8499"
    )

    async with async_playwright() as p:
        # 1) Usa Chrome real en lugar de Chromium
        browser = await p.chromium.launch(channel="chrome", headless=False)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1280, "height": 800})

        # 2) Carga página y espera que la red se estabilice
        await page.goto(open_url, wait_until="networkidle")
        # 3) Simula interacción para disparar JS/lazy-loads
        await page.mouse.click(100, 100)
        # 4) Espera hasta que los actos estén presentes (máx. 2 min)
        await page.wait_for_selector("article.ato", timeout=120000)

        # 5) Captura el HTML renderizado
        html = await page.content()
        await browser.close()

    # 6) Parséalo con BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # Fecha general
    fecha_general = None
    fecha_tag = soup.select_one("div.resenhaTitulo span")
    if fecha_tag:
        text = fecha_tag.get_text(strip=True)
        try:
            from datetime import datetime
            fecha_general = datetime.strptime(text, "%d/%m/%Y").date().isoformat()
        except ValueError:
            fecha_general = text

    # Extrae cada acto
    for art in soup.select("article.ato"):
        link = art.select_one(".ementa a.link")
        if not link:
            continue
        title = link.select_one("strong").get_text(strip=True)
        status_tag = link.select_one("span.ico-situacao")
        status = status_tag.get_text(strip=True) if status_tag else None
        description = "\n".join(
            p.get_text(strip=True)
            for p in link.find_all("p")
            if p.get_text(strip=True)
        )
        href = link.get("href")
        source_url = base_url + href if href else None

        items.append({
            "title": title,
            "status": status,
            "description": description,
            "source_url": source_url,
            "presentation_date": fecha_general
        })

    return items

if __name__ == "__main__":
    datos = asyncio.run(scrape_anvisa_legis_dom())
    print(json.dumps(datos, indent=4, ensure_ascii=False))
