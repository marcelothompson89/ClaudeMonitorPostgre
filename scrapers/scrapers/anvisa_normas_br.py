import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def scrape_with_playwright():
    async with async_playwright() as p:
        # Lanzar Chromium en modo visible para probar y evitar posibles bloqueos por automatización.
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        url = "https://anvisalegis.datalegis.net/action/ActionDatalegis.php?acao=abrirEmentario&cod_modulo=293&cod_menu=8499"
        
        # Navegar a la URL y esperar que la red esté inactiva
        await page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Esperar a que aparezca algún selector característico, por ejemplo: un artículo (si se espera que aparezca "article.ato")
        try:
            await page.wait_for_selector("article.ato", timeout=30000)
        except Exception as e:
            print("Timeout esperando los elementos 'article.ato':", e)
        
        # Simular un scroll para activar el lazy load
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        # Simula también un pequeño movimiento del ratón
        await page.mouse.move(100, 100)
        # Espera adicional para que se cargue cualquier contenido asíncrono
        await page.wait_for_timeout(5000)
        
        html = await page.content()
        await browser.close()
        
        soup = BeautifulSoup(html, 'html.parser')
        snippet = soup.prettify()[:500]
        print("Snippet del HTML renderizado:")
        print(snippet)
        return soup

async def main():
    await scrape_with_playwright()

if __name__ == "__main__":
    asyncio.run(main())
