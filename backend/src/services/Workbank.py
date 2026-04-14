import asyncio
import os
from playwright.async_api import async_playwright

class Workbank:

    page = ''
    user = os.getenv("")
    password = os.getenv("")
    url = 'https://lev.workbankvirtual.com.br/login.aspx?pdc=true'

    def __init__(self, file, bank):
        self.file = file
        self.bank = bank

    async def inicialize_browser(self):
        context_options = {
            "permissions": ['geolocation'],
            "geolocation": {"latitude": -23.5505, "longitude": -46.6333},
            "locale": 'pt-BR',
        }

        browser_instance = await self.open_browser(self.url, headless=False, options=context_options)

        self.page = browser_instance.page
        self.browser = browser_instance.browser

    async def open_browser(self, url, headless, options):
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=headless)

        context = await browser.new_context(**options)
        page = await context.new_page()

        await page.goto(url)

        class BrowserInstance:
            def __init__(self, page, browser):
                self.page = page
                self.browser = browser

        return BrowserInstance(page, browser)

    async def login(self):
        attempt = 1
        max_attempt = 3

        while attempt <= max_attempt:
            try:
                print(f"Iniciando tentativa {attempt} de login...")

                await self.inicialize_browser()

                if not self.page:
                    raise Exception("Página não foi iniciada.")

                await self.page.wait_for_selector(self.selector["username"])
                await self.page.locator(self.selector["username"]).type(self.user, delay=100)
                await self.page.keyboard.press("Enter")

                await self.page.click(self.selector["password"])
                await self.page.wait_for_timeout(1500)
                await self.page.locator(self.selector["password"]).type(self.pass_word, delay=100)

                self.page.once("dialog", lambda dialog: dialog.accept())

                await self.page.keyboard.press("Enter")
                await self.page.wait_for_timeout(1500)

                await self.page.get_by_role("button", name="OPERACIONAL").click()

                try:
                    btn_ok = await self.page.wait_for_selector('button:has-text("OK")', timeout=3000)
                    if btn_ok:
                        await btn_ok.click()
                except:
                    pass

                return True

            except Exception as e:
                print(f"Erro na tentativa {attempt}: {e}")
                attempt += 1
                await self.close_browser()

        print("Número máximo de tentativas atingido.")
        return False

    def navigate(self):
        pass

    def input(self):
        pass

    def run(self):
        pass