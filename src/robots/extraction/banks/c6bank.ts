import { RobotExtraction } from "../../robot";
import { C6BANK_CONSTANTS } from "../../../config/c6bank";
import * as dotenv from 'dotenv';
dotenv.config()

const infosBank = C6BANK_CONSTANTS

export class C6Bank extends RobotExtraction {
    constructor() {
        super({
            name: "C6Bank",
            url: infosBank.url.login,
            user: process.env.LOGIN_C6_USER || "",
            password: process.env.LOGIN_C6_PASSWORD || "",
            selectors: {
                userSelector: infosBank.selector.username,
                passwordSelector: infosBank.selector.password,
                btnLogin: infosBank.selector.btnEntrar
            }
        });
    }

    async Navigate(): Promise<void> {
        console.log('Iniciando navegação no C6 Bank...');

        try{
            await this.page?.pause()

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

                await this.page?.waitForTimeout(10000)

                await this.page?.getByRole(
                    'button',
                    { name: 'Analítico Comissão Flat (' },
                ).click();
                await this.page?.getByRole('menuitem', { name: 'Download data' }).click();

                await this.page?.getByRole('dialog', { name: 'Download' }).click();
                await this.page?.getByRole('option',
                    { name: 'Excel Spreadsheet (Excel 2007' },
                ).click();
                await this.page?.getByRole('banner', { name: 'Download' }).click();

                await this.page?.getByRole('button',
                    { name: 'Advanced data options' },
                ).click();
                await this.page?.getByRole('radio', { name: 'All results' }).check();

                const [download] = await Promise.all([
                    this.page?.waitForEvent('download', { timeout: 30000 }),
                    this.page?.getByRole('button', { name: 'Download' }).click({ force: true }),
                ]);

                console.log("Download concluído com sucesso!");

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