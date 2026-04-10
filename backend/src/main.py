from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pandas as pd
import io
from .factories.FactoryBanks import FactoryBank

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
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

        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            response.to_excel(writer, index=False)

        output.seek(0)

        headers = {
            'Content-Disposition': f'attachment; filename="{bank}_Atualizacoes.xlsx"'
        }

        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers=headers,
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": "Erro ao processar os arquivos.",
                "error": str(e)
            }
        )