import { RobotExtraction } from "../robot";
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';
import { WORKBANK_CONSTANTS } from "../../config/workbank";
import * as dotenv from 'dotenv';
import { getCorrectBank } from "../../utils/RobotUtils";
dotenv.config()

const infosBank = WORKBANK_CONSTANTS
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class WorkbankExtraction extends RobotExtraction {
    constructor(nameBank: string) {
        super({
            name: "Workbank",
            bank: nameBank,
            url: infosBank.url.login,
            user: process.env.LOGIN_WORKBANK_USER || "",
            password: process.env.LOGIN_WORKBANK_PASSWORD || "",
            selectors: {
                userSelector: infosBank.selector.username,
                passwordSelector: infosBank.selector.password,
                btnLogin: infosBank.selector.btnEntrar,
                btnOperacional: infosBank.selector.btnOperacional
            }
        });
    }

    async Login() {
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
                await this.page.locator(
                    this.config.selectors.userSelector).pressSequentially(this.config.user, { delay: 100 });
                await this.page.keyboard.press('Enter');

                await this.page.click(
                    this.config.selectors.passwordSelector);
                await this.page.waitForTimeout(1500)
                await this.page.locator(
                    this.config.selectors.passwordSelector).pressSequentially(this.config.password, { delay: 100 });

                this.page.once('dialog', async d => d.accept());

                await this.page.keyboard.press('Enter');

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

    async Navigate(): Promise<void> {
        console.log('Iniciando navegação no C6 Bank...');

        const optionBank = getCorrectBank(this.config.bank!)

        try{
            await this.page?.getByTitle('Fechar').click();

            await this.page?.getByRole('link', { name: '  CADASTROS' }).click();
            await this.page?.waitForTimeout(1500)
            await this.page?.getByRole('link', { name: 'Administrativo' }).click();
            await this.page?.waitForTimeout(1500)
            await this.page?.getByRole('link', { name: 'Empresa' }).click();
            await this.page?.waitForTimeout(1500)
            await this.page?.getByRole('link', { name: 'Tab. Comissão Empresa' }).click();

            await this.page?.waitForTimeout(5000)
            await this.page?.locator('#ddlBancoPesquisa').selectOption(optionBank);
            await this.page?.getByText('Exibir Outras Comissões').click();
            await this.page?.getByText('Pesquisar').click();

            await this.page?.waitForTimeout(15000)
        } catch (error) {
            console.error("Erro durante a navegação no C6 Bank:", error);
            throw error;
        }
    }

    async Download(): Promise<void> {
        let attempt = 0
        const maxAttempts = 3

        while (attempt < maxAttempts) {

            attempt++;

            try {

                const [download] = await Promise.all([
                    this.page?.waitForEvent('download', { timeout: 60000 }),
                    this.page?.getByRole('button', { name: 'Extrair Tabelas open_in_new' }).click({ force: true }),
                ]);

                const tempDir = path.resolve(__dirname, '../../temp');

                if (!fs.existsSync(tempDir)) {
                    fs.mkdirSync(tempDir, { recursive: true });
                }

                const fileName = download?.suggestedFilename();

                if (fileName) {
                    const filePath = path.join(tempDir, fileName);

                    await download?.saveAs(filePath);

                    console.log(`✅ Download concluído: ${fileName}`);
                }

                return
            } catch (e) {
                console.error(`Erro na tentativa ${attempt}:`, e);

                if (attempt >= maxAttempts) {
                    throw new Error(`Falha no download após ${maxAttempts} tentativas. Erro original: ${e}`);
                }

                await this.page?.waitForTimeout(3000);
            }
        }
    }
}