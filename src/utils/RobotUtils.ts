import { Browser, BrowserContext, chromium, Page } from 'playwright'

interface BrowserInstance {
    browser: Browser,
    context: BrowserContext,
    page: Page
}

export interface BrowserOptions {
    geolocation?: { latitude: number; longitude: number };
    permissions?: string[];
    locale?: string;
    name?: string
}

export async function OpenBrowser(url: string, headless: boolean = true, options?: BrowserOptions): Promise<BrowserInstance> {

    console.log('Abrindo o navegador')

    const browser = await chromium.launch({ //crio o browser
        headless: headless
    })

    const context = await browser.newContext({ //crio um contexto com viewport null para respeitar o tamanho da janelo do os
        viewport: null,
        acceptDownloads: true,
        locale: options?.locale || 'pt-BR',
        geolocation: options?.geolocation,
        permissions: options?.permissions || [],
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    const page = await context.newPage()

    if (options?.name == "C6Bank" || options?.name == "QualiBank") {
        await page.goto(url)

        await page.waitForLoadState('networkidle')

        return { browser, context, page }
    }

    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 })

    await page.waitForTimeout(3000)

    return { browser, context, page }
}

export function getCorrectBank(bank: string): string {
    const mapper: { [key: string]: string } = {
        "digio": "225",
    }
    return mapper[bank]
}