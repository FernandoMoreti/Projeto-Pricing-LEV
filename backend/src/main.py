from fastapi import FastAPI, File, UploadFile, Form
import pandas as pd
import io
from .services.CapitalConsig import CapitalConsigMapper
from .factories.FactoryBanks import FactoryBank

app = FastAPI()

@app.post("/pricing")
async def edit_pricing(
    fileBank: UploadFile = File(...),
    fileWork: UploadFile = File(...),
    bank: str = Form(...)
):
    content_bank = await fileBank.read()
    content_work = await fileWork.read()

    bank = bank.strip().lower().replace(" ", "")

    bankMapper = FactoryBank.getMapperBank(bank)

    df_work = pd.read_excel(io.BytesIO(content_work))

    bankMapper.run(df_work, content_bank)

    return 200