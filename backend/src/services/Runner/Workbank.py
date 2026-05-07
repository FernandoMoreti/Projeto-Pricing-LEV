from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

load_dotenv()

def login(page):

    login = os.getenv("USER_WORKBANK")
    senha = os.getenv("PASS_WORKBANK")

    page.wait_for_selector('input[id="usuario"]', state='visible')
    page.locator('input[id="usuario"]').fill(login)
    page.locator('input[id="usuario"]').press('Enter')

    page.wait_for_timeout(1500)

    page.wait_for_selector('input[id="senha"]', state='visible')
    page.locator('input[id="senha"]').fill(senha)
    page.locator('input[id="senha"]').press('Enter')

    page.wait_for_timeout(1500)

    page.get_by_role('button', name='OPERACIONAL').click()

    page.wait_for_timeout(5000)

    try:
        btn_html = page.wait_for_selector('button:has-text("OK")', timeout=3000)
        if btn_html:
            btn_html.click()
    except:
        pass

    page.wait_for_timeout(1500)

    seletor = page.get_by_title('Fechar')
    if seletor.is_visible():
        seletor.click()

def navegation(page):
    page.get_by_role("link", name="  CADASTROS").click()
    page.wait_for_timeout(1000)
    page.get_by_role("link", name="Administrativo").click()
    page.wait_for_timeout(1000)
    page.get_by_role("link", name="Empresa").click()
    page.wait_for_timeout(1000)
    page.get_by_role("link", name="Tab. Comissão Empresa").click()
    page.pause()

def iniciar_robo_sync():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        url = os.getenv("URL_WORKBANK")
        context = browser.new_context(
            permissions=['geolocation'],
            geolocation={'latitude': -23.550520, 'longitude': -46.633308}
        )
        page = context.new_page()

        try:

            page.goto(url)

            print("Logando...")
            login(page)
            print("Navegando...")
            navegation(page)
            print("Processo finalizado com sucesso!")

        except Exception as e:
            print(f"Error occurred while navigating to login page: {e}")
        finally:
            browser.close()