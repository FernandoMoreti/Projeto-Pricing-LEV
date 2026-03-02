import { Page, Browser } from 'playwright'
import { OpenBrowser } from "../utils/RobotUtils"

export interface LoginSelectors {
    userSelector: string
    passwordSelector: string
    btnLogin: string
    btnOperacional?: string
    popupBtnSelector?: string
}

export interface BankConfig {
    name: string
    bank?: string
    url: string
    user: string
    password: string
    selectors: LoginSelectors
}

export abstract class RobotExtraction {
    protected config: BankConfig
    protected page: Page | undefined;
    protected browser: Browser | undefined;

    constructor(config: BankConfig) {
        this.config = config;
    }

    async inicializeBrowser() {
        const options = {
            permissions: ['geolocation'],
            geolocation: { latitude: -23.5505, longitude: -46.6333 },
            locale: 'pt-BR',
            name: this.config.name
        }

        const browserInstance = await OpenBrowser(this.config.url, false, options) // posso adicionar true se nn quiser ver e false se quiser
        this.page = browserInstance.page
        this.browser = browserInstance.browser
    }

    async Login(): Promise<void> {
        let attempt = 0
        const maxAttempt = 3

        if (!this.config.user || !this.config.password) {
            throw new Error("ERRO: Credenciais não encontradas no arquivo .env");
        }

        while (attempt < maxAttempt) {
            try {
                console.log(`Iniciando tentativa ${attempt + 1} de login...`)

                await this.inicializeBrowser()

                if (!this.page) throw new Error("Página não foi iniciada.");

                await this.page.waitForSelector(
                    this.config.selectors.userSelector);
                await this.page.fill(
                    this.config.selectors.userSelector, this.config.user);

                await this.page.click(
                    this.config.selectors.passwordSelector);
                await this.page.waitForTimeout(1500)
                await this.page.fill(
                    this.config.selectors.passwordSelector, this.config.password);

                this.page.once('dialog', async d => d.accept());

                await this.page.click(this.config.selectors.btnLogin);

                try {
                    const btnHtml = await this.page.waitForSelector('button:has-text("OK")', { timeout: 3000 });
                    if(btnHtml) await btnHtml.click();
                } catch {}

                return
            } catch (e) {
                console.error("Erro durante o processo de login:", e)

                if (this.browser) {
                    await this.browser.close();
                    this.browser = undefined;
                    this.page = undefined;
                }

                attempt++

                if (attempt >= maxAttempt) {
                    throw new Error(`Falha crítica ao logar no ${this.config.name} após ${maxAttempt} tentativas. Erro: ${e}`);
                }
            }
        }
    }

    abstract Navigate(): Promise<void>

    abstract Download(): Promise<void>

    public async Run(): Promise<void> {
        console.log(`\nIniciando Robo: ${this.config.name} `);

        try {
            console.log(`[${this.config.name}] Logando no site...`);
            await this.Login();

            console.log(`[${this.config.name}] Navegando para extratos...`);
            await this.Navigate();

            console.log(`[${this.config.name}] Iniciando download...`);
            await this.Download();

            console.log(`[${this.config.name}] Processo finalizado com SUCESSO!`);

        } catch (error) {
            console.error(`[${this.config.name}] FALHA CRÍTICA:`, error);
        } finally {
            await this.CloseBrowser();
            console.log(`Fechando Browser...\n`);
        }
    }

    async CloseBrowser(): Promise<void> {
        if (this.browser) {
            await this.browser.close();
        }
    }

}