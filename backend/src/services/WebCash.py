from .Bank import Bank
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import io
from ..utils.utils import convertValues, formatar_br, remover_acentos
from ..config.bank.WebCashVariables import family_product, group_convenio, operation
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade

class WebCashMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file))
        return df

    def compare_archive(self, df_work, df_bank):

        df_bank["CONVÊNIO"] = df_bank["CONVÊNIO"].astype(str).str.strip()
        df_bank["TABELA"] = df_bank["TABELA"].astype(str).str.strip()
        df_bank["PRODUTO"] = df_bank["PRODUTO"].astype(str).str.strip()

        df_bank = df_bank[df_bank["SITUAÇÃO"] != "SUSPENSO"]
        df_bank = df_bank[df_bank["SITUAÇÃO"] != "INATIVO"]

        valores_vazios = ["nan", "none", "", "nat", "<na>"]

        df_bank["product"] = df_bank.apply(
            lambda row: (
                f"{row['CONVÊNIO']} - {row['TABELA']} - {row['PRODUTO']}"
                if str(row["TABELA"]).strip().lower() not in valores_vazios 
                and str(row["PRODUTO"]).strip().lower() not in valores_vazios
                and str(row["CONVÊNIO"]).strip().lower() not in valores_vazios
                else f"{row['SIGLA']} - {row['TABELA']} - {row['PRODUTO']}"
                if str(row["CONVÊNIO"]).strip().lower() in valores_vazios
                else f"{row['CONVÊNIO']}"
            ),
            axis=1
        )

        listOfRows = []

        for index, row in df_bank.iterrows():
            if pd.notna(row["COMISSÃO \nSEM SEGURO"]):
                rowSeguro = row.copy()
                rowSeguro["COMISSAO REAL"] = rowSeguro["COMISSÃO \nCOM SEGURO"]
                rowSeguro["FAIXA SEG"] = "2,00-100.000,00"
                listOfRows.append(rowSeguro)

            row["COMISSAO REAL"] = row["COMISSÃO \nSEM SEGURO"]
            row["FAIXA SEG"] = "0,00-1,00"
            listOfRows.append(row)

        df_bank = pd.DataFrame(listOfRows)

        df_bank["Prazo"] = df_bank["PARCELAS"].astype(str) + "-" + df_bank["PARCELAS"].astype(str)
        df_work["Produto"] = df_work["Produto"].str.strip()

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["product", "Prazo", "FAIXA SEG"],
            right_on=["Produto", "Parc. Atual", "Faixa Val. Seguro"],
            how="outer",
            indicator=True
        )

        df_open = df_result[df_result["_merge"] == "left_only"]
        df_close = df_result[df_result["_merge"] == "right_only"]
        df_matches = df_result[df_result["_merge"] == "both"]
        list_to_close_and_open = []
        list_of_open_tables = []
        list_of_close_tables = []

        if not df_matches.empty:
            print(f"Encontrados {len(df_matches)} correspondências!")
            print(f"Encontrados {len(df_open)} open!")
            print(f"Encontrados {len(df_close)} close!")

        list_of_open_tables = df_open.to_dict(orient="records")
        list_of_close_tables = df_close.to_dict(orient="records")

        for index, row in df_matches.iterrows():

            percent = round(convertValues(row["COMISSAO REAL"] * 100), 2)
            percent_work = convertValues(row["% Comissão"])

            if percent != percent_work:
                list_to_close_and_open.append(row)

        return list_of_open_tables, list_of_close_tables, list_to_close_and_open

    def extract_city(self, product):
        product = str(product).upper().strip()
        product = remover_acentos(product)

        for nome_cidade in sorted(citys.keys(), key=len, reverse=True):
            if nome_cidade in product:
                city = citys[nome_cidade]
                break
            else:
                city = ""

        return city

    def extract_uf_of_city(self, city):
        city = str(city).upper().strip()

        if city.startswith("DE "):
            city = city.split(" ")[1]

        uf = " " + citys_uf.get(city, "")

        return uf

    def extract_uf_of_state(self, product):

        product = str(product).upper().strip()
        product = remover_acentos(product)

        for state in sorted(states.keys(), key=len, reverse=True):
            if state in product:
                result = states[state]
                break
            else:
                result = ""

        return result

    def get_convenio(self, product):
        categorias = {
            "GOV-": ["GOV", "GOV_", "GOV.", "IGEPREV", "MINISTERIO", "ESTADO", "LEGISLATIVA", "PM"],
            "FEDERAL SIAPE": ["SIAPE", "SIA"],
            "TJ | ": ["TJ ", "TJ_", "TJ.", "TRT", "TRIBUNAL"],
            "PREF. ": ["PREF", "PREV", "PREF_", "PREF.", "IPREM", "RCC", "IPAM", "IPREF", "COMISSIONADOS", "PREVIJUNO"],
        }

        for categoria, prefixos in categorias.items():
            prefixo_encontrado = next((p for p in prefixos if p in product), None)
            if prefixo_encontrado:
                convenio = categoria

                if convenio == "FEDERAL SIAPE":
                    return convenio

                if convenio == "PREF. ":
                    city = self.extract_city(product)
                    uf = self.extract_uf_of_city(city)

                    if city == "":
                        return ""

                    convenio = convenio + city + uf
                    return convenio

                if convenio == "GOV-":
                    uf = self.extract_uf_of_state(product)
                    convenio = convenio + uf
                    return convenio

                if convenio == "TJ | ":
                    uf = self.extract_uf_of_state(product)
                    convenio = convenio + uf
                    return convenio
        return "CONVENIO DESCONHECIDO"

    def getOperation(self, product):
        product = str(product).strip()

        for operator in sorted(operation.keys(), key=len, reverse=True):
            if operator in product:
                result = operation[operator]
                break
            else:
                result = ""

        return result

    def create_open_tables(self, list_of_open_tables, model):

        list_of_convert_rows = []

        for row in list_of_open_tables:

            product = row["product"]
            convenio = self.get_convenio(product)

            if "-" in convenio:
                agreement = convenio.split("-")[0].strip()
            else:
                agreement = convenio.split(" ")[0].strip()

            family = family_product[agreement]
            group = group_convenio[family]

            percent = round(convertValues(row["COMISSAO REAL"] * 100), 2)

            operation = self.getOperation(row["PRODUTO"])

            grades = grade.get(operation, "")

            new_row = model.copy()

            new_row["Operação"] = operation
            new_row["Produto"] = product
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Convênio"] = convenio
            new_row["Parc. Atual"] = row["Prazo"]
            new_row["% Mínima"] = percent * grades["min"]
            new_row["% Intermediária"] = percent * grades["med"]
            new_row["% Máxima"] = percent * grades["max"]
            new_row["% Comissão"] = percent
            new_row["Faixa Val. Seguro"] = row["FAIXA SEG"]
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Complemento"] = f"TX {(row['TAXA'] * 100):.2f}%"
            new_row["Atualizações"] = "INCLUSAO"

            list_of_convert_rows.append(new_row)

        df = pd.DataFrame(list_of_convert_rows)

        return df

    def create_close_tables(self, list_of_close_tables):

        list_of_convert_rows = []

        for row in list_of_close_tables:

            row["Término"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            row["Atualizações"] = "ENCERRAMENTO"

            list_of_convert_rows.append(row)

        df = pd.DataFrame(list_of_convert_rows)

        df = df.drop(['Unnamed: 0', 'CONVÊNIO', 'SIGLA', 'PRODUTO', 'TABELA', 'PARCELAS',
            'COMISSÃO', 'TAXA', 'SITUAÇÃO', 'product', 'Prazo', '_merge'], axis=1, errors='ignore')

        df.columns = df.columns.str.replace('_y', '')

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = round(convertValues(row["COMISSAO REAL"] * 100), 2)

            row_close = row.copy()

            row_close["Término"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            row_close["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

            operation = self.getOperation(row["PRODUTO"])

            grades = grade.get(operation, "")

            row_open["Término"] = ""
            row_open["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            row_open["ID"] = ''
            row_open["% Comissão"] = percent
            row_open["% Mínima"] = percent * grades["min"]
            row_open["% Intermediária"] = percent * grades["med"]
            row_open["% Máxima"] = percent * grades["max"]
            row_open["Faixa Val. Seguro"] = row["FAIXA SEG"]
            row_open["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_open_rows.append(row_open)

        df = pd.DataFrame(list_of_convert_close_rows)
        df2 = pd.DataFrame(list_of_convert_open_rows)

        colunas_remover = ['Unnamed: 0', 'CONVÊNIO', 'SIGLA', 'PRODUTO', 'TABELA', 'PARCELAS',
            'COMISSÃO', 'TAXA', 'SITUAÇÃO', 'product', 'Prazo', '_merge']

        df.columns = df.columns.str.replace('_y', '')
        df2.columns = df.columns.str.replace('_y', '')

        df = df.drop(colunas_remover, axis=1, errors='ignore')
        df2 = df2.drop(colunas_remover, axis=1, errors='ignore')

        return df, df2

    def input_standard_values(self, model):

        model["Instituição"] = "WEBCASH"
        model["Parc. Refin."] = "0-0"
        model["% PMT Pagas"] = "0,00-0,00"
        model["% Taxa"] = "0,00-0,00"
        model["Idade"] = "0-80"
        model["-"] = "%"
        model["Base Comissão"] = "LÍQUIDO"
        model["Val. Base Produção"] = "LÍQUIDO"
        model["% Fator"] = "0,000000000"
        model["% TAC"] = "0,000000"
        model["Val. Teto TAC"] = "0,000000"
        model["Faixa Val. Contrato"] = "0,00-100.000,00-LÍQUIDO"
        model["Venda Digital"] = "SIM"
        model["Visualização Restrita"] = "SIM"

        return model

    def run(self, df_work, file_Bank):

        try:

            print("Lendo arquivo enviado pelo banco...")
            df_bank = self.read_archive(file_Bank)
            print("Arquivo lido com sucesso!")

            print("Criando modelo nulo...")
            model = self.createNullModel()
            model = self.input_standard_values(model)
            print("Modelo criado com sucesso!")

            print("Comparando tabelas...")
            list_of_open_tables, list_of_close_tables, list_to_close_and_open = self.compare_archive(df_work, df_bank)
            print("Tabelas comparadas com sucesso...")

            df_open = None
            df_close = None
            df_close2 = None
            df_open2 = None

            if len(list_of_open_tables) > 0:
                print(f"Foram encontradas {len(list_of_open_tables)} tabelas para abrir.")
                df_open = self.create_open_tables(list_of_open_tables, model)
                columns_in_order = df_open.columns.tolist()
            if len(list_of_close_tables) > 0:
                print(f"Foram encontradas {len(list_of_close_tables)} tabelas para fechar.")
                df_close = self.create_close_tables(list_of_close_tables)
                columns_in_order = df_close.columns.tolist()
            if len(list_to_close_and_open) > 0:
                print(f"Foram encontradas {len(list_to_close_and_open)} tabelas para fechar e abrir.")
                df_close2, df_open2 = self.create_close_open_tables(list_to_close_and_open)
                columns_in_order = df_close2.columns.tolist()

            print("Iniciando processo de junção dos arquivos...")

            dfs_para_juntar = []

            for df in [df_close, df_close2, df_open, df_open2]:
                if df is not None and not df.empty:
                    df_temp = df.copy()
                    df_temp = df_temp.reindex(columns=columns_in_order)
                    dfs_para_juntar.append(df_temp)
            df_final = pd.concat(dfs_para_juntar, axis=0, ignore_index=True, sort=False)
            print(f"Sucesso! Total de linhas: {len(df_final)}")

            print("Processo concluído!")
            return df_final

        except Exception as e:
            print(f"Erro durante o processamento: {str(e)}")
            return "error"