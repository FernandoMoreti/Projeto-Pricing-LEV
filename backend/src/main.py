from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from .factories.FactoryBanks import FactoryBank

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/pricing")
async def edit_pricing(
    fileBank: UploadFile = File(...),
    fileWork: UploadFile = File(...),
    bank: str = Form(...)
):
    try:
        content_bank = await fileBank.read()
        content_work = await fileWork.read()

        bank = bank.strip().lower().replace(" ", "")

        bankMapper = FactoryBank.getMapperBank(bank)

        df_work = pd.read_excel(io.BytesIO(content_work))

        response = bankMapper.run(df_work, content_bank)

        if type(response) == str:
            return {
                "success": False,
                "message": "O Excel não foi gerado com sucesso.",
            }

        return {
            "success": True,
            "message": f"Processamento do banco {bank} concluído com sucesso!",
            "details": "Os arquivos foram unidos e o Excel foi gerado."
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": "Erro ao processar os arquivos.",
                "error": str(e)
            }
        )