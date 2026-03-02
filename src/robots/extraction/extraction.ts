import { WorkbankExtraction } from "./workbankExtraction";
import { C6Bank } from "./banks/c6bank";

const args = process.argv.slice(2);

const getArgValue = (argName: string): string | null => {
    const arg = args.find(a => a.startsWith(`--${argName}=`));
    return arg ? arg.split('=')[1] : null;
};

async function main() {

    const bank = getArgValue('bank');
    const bankOfWorkbank = getArgValue('bankWork') || "";

    console.log(bank)
    console.log(bankOfWorkbank)

    if (!bank) {
        console.error("❌ Erro: O argumento --bank é obrigatório.");
        process.exit(1);
    }

    try {
        switch (bank) {
            case 'c6bank':
                const runner = new C6Bank();
                await runner.Run();
                break;
            case 'workbank':
                const runnerWorkbank = new WorkbankExtraction(bankOfWorkbank);
                await runnerWorkbank.Run();
                break;
            default:
                console.error(`❌ Erro: Banco desconhecido "${bank}". Opções válidas são "c6bank" ou "workbank".`);
                process.exit(1);
        }
    } catch (error) {
        console.error("Erro durante a execução do robô:", error);
    }

}

main()
