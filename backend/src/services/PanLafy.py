from .Bank import Bank
from datetime import datetime, timedelta
import pandas as pd
import io
from ..utils.utils import convertValues, formatar_br, remover_acentos
from ..config.bank.PanLafyVariables import family_product, group_convenio, operation
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade

class PanLafyMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file))
        return df

    def compare_archive(self, df_work, df_bank):

        df_bank["Produto"] = df_bank["Produto"].str.strip()
        df_work["Produto"] = df_work["Produto"].str.strip()

        excecoes = ["PORTAB/REFIN", "PORTABILIDADE", "SAQUE COMPL.", "CARTÃO"]

        mask = ~df_bank["Operação"].isin(excecoes)
        df_bank.loc[mask, "Operação"] = df_bank.loc[mask, "Operação"].map(operation).fillna("")

        for i, row in df_bank.iterrows():

            text = row["Produto"]
            if text.startswith("PMESP-"):
                row["Produto"] = row["Produto"].split("- ")[1]
            elif text.startswith("GOV_PR_"):
                row["Produto"] = row["Produto"]
            else:
                row["Produto"] = row["Produto"].split(" - ")[1]

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["Produto", "Complemento", "Parc. Atual", "Operação", "Faixa Val. Seguro", "Venda Digital", "Idade", "Faixa Val. Contrato"],
            right_on=["Produto", "Complemento", "Parc. Atual", "Operação", "Faixa Val. Seguro", "Venda Digital", "Idade", "Faixa Val. Contrato"],
            how="outer",
            indicator=True
        )

        df_open = df_result[df_result["_merge"] == "left_only"]
        list_of_close_tables = df_result[df_result["_merge"] == "right_only"]
        list_to_close_and_open = []
        list_of_open_tables = []
        df_matches = df_result[df_result["_merge"] == "both"]

        if not df_matches.empty:
            print(f"Encontrados {len(df_matches)} correspondências!")

        list_of_open_tables = df_open.to_dict(orient="records")

        for index, row in df_matches.iterrows():

            percent = convertValues(row["% Comissão_x"])
            percent_work = convertValues(row["% Comissão_y"])
            if percent != percent_work:
                list_to_close_and_open.append(row)

        return list_of_open_tables, list_of_close_tables, list_to_close_and_open

    def extract_city(self, product):
        product = str(product).upper().strip()

        if product.split("_")[0] in ["IPREM"]:
            return citys.get(product.split(" ")[0], "")

        cidade = product.split("_")[1]

        if cidade in ["CAMPINA", "PORTO", "SANTA", "SAO", "BELO"]:
            cidade = product.split(" ")[1] + " " + product.split(" ")[2]

        cidade = remover_acentos(cidade)

        city = citys.get(cidade, "")

        return city

    def extract_uf_of_city(self, city):
        city = str(city).upper().strip()

        if city.startswith("DE "):
            city = city.split(" ")[1]

        uf = " " + citys_uf.get(city, "")

        return uf

    def extract_uf_of_state(self, rest_of_product):
        state = str(rest_of_product).upper().strip()

        if "_" in state:
            state = state.split("_")[1]

        state = remover_acentos(state)

        if len(state) == 2:
            return state

        uf = states.get(state, "")

        return uf

    def get_convenio(self, product):
        firstProduct = str(product).upper().split("-")[0].strip()
        categorias = {
            "GOV-": ["GOV", "GOV_", "GOV.", "SPPREV_", "AMA", "PMESP"],
            "FEDERAL SIAPE": ["SIAPE", "SIA"],
            "PREF. ": ["PREF", "PREF_", "PREF.", "IPREM", "PRE_"],
            "TJ | ": ["TJ ", "TJ_", "TJ."]
        }

        if firstProduct in ["AERONAUTICA", "MARINHA", "FGTS", "INSS", "CLT", "INSSC15"]:
            return firstProduct

        for categoria, prefixos in categorias.items():
            prefixo_encontrado = next((p for p in prefixos if p in firstProduct), None)
            if prefixo_encontrado:
                convenio = categoria

                if convenio == "FEDERAL SIAPE":
                    return convenio

                if convenio == "PREF. ":
                    city = self.extract_city(firstProduct)
                    uf = self.extract_uf_of_city(city)

                    if city == "":
                        return ""

                    convenio = convenio + city + uf
                    return convenio

                if convenio == "GOV-":
                    uf = self.extract_uf_of_state(firstProduct)
                    convenio = convenio + uf
                    return convenio

                if convenio == "TJ | ":
                    uf = self.extract_uf_of_state(firstProduct)
                    convenio = convenio + uf
                    return convenio
        return "CONVENIO DESCONHECIDO"

    def get_product_name(self, product):
        if "-" in product:
            product = str(product).upper().split("-")[1:]

        if len(product) > 1:
            product = "".join(p.strip() for p in product)
            return product

        return product[0].strip()

    def adding_values(self, new_row, row):
        if pd.isna(row["BÔNUS"]):
            new_row["BÔNUS"] = row["BÔNUS_CAMPANHA"]
        elif pd.isna(row["BÔNUS_CAMPANHA"]):
            new_row["BÔNUS"] = row["BÔNUS"]

        if pd.notna(new_row["BÔNUS"]):
            new_row["REPASSE BÔNUS"] = "0,00 | 0,00 | 0,00"

        new_row["ATIVAÇÃO"] = row["ATIVAÇÃO_x"]
        if pd.notna(new_row["ATIVAÇÃO"]):
            if "80,00" in new_row["ATIVAÇÃO"]:
                new_row["REPASSE ATIVAÇÃO"] = "55,00 | 64,00 | 72,00"
            else:
                new_row["REPASSE ATIVAÇÃO"] = "35,00 | 40,00 | 45,00"

        new_row["PRÉ-ADESÃO"] = row["PRE_ADESÃO"]
        if pd.notna(new_row["PRÉ-ADESÃO"]):
            if "50,00" in new_row["PRÉ-ADESÃO"]:
                new_row["REPASSE PRÉ-ADESÃO"] = "35,00 | 40,00 | 45,00"
            elif "80,00" in new_row["PRÉ-ADESÃO"]:
                new_row["REPASSE PRÉ-ADESÃO"] = "55,00 | 64,00 | 72,00"
            elif "160,00" in new_row["PRÉ-ADESÃO"]:
                new_row["REPASSE PRÉ-ADESÃO"] = "110,00 | 128,00 | 144,00"
            elif "300,00" in new_row["PRÉ-ADESÃO"]:
                new_row["REPASSE PRÉ-ADESÃO"] = "210,00 | 240,00 | 270,00"

        new_row["SEGURO PAN"] = row["SEGURO"]
        if pd.notna(new_row["SEGURO PAN"]):
            if "0,00 |" in new_row["SEGURO PAN"]:
                if pd.notna(row["SEGURO_CARTÃO"]):
                    new_row["SEGURO PAN"] = row["SEGURO_CARTÃO"]
                # elif pd.notna(row["SEGURO_CONSIG"]):
                #     new_row["SEGURO PAN"] = row["SEGURO_CONSIG"]
                elif pd.notna(row["SEGURO_FGTS"]):
                    new_row["SEGURO PAN"] = row["SEGURO_FGTS"]

        # VALIDAR NOVAMENTE
        if pd.notna(new_row["SEGURO PAN"]):
            if "0,00 |" in new_row["SEGURO PAN"] or "24,00" in new_row["SEGURO PAN"]:
                new_row["REPASSE SEGURO PAN"] = "0,00 | 0,00 | 0,00"
            elif "1,00" in new_row["SEGURO PAN"]:
                new_row["REPASSE SEGURO PAN"] = "0,65 | 0,70 | 0,80"
            elif "1,68" in new_row["SEGURO PAN"]:
                new_row["REPASSE SEGURO PAN"] = "1,15 | 1,30 | 1,50"
            elif "2,25" in new_row["SEGURO PAN"]:
                new_row["REPASSE SEGURO PAN"] = "1,60 | 1,80 | 2,03"

        return new_row

    def create_open_tables(self, list_of_open_tables, model):

        list_of_convert_rows = []

        for row in list_of_open_tables:

            product = row["Produto"]
            convenio = self.get_convenio(product)

            agreement = row["Família Produto_x"].strip()
            family = family_product[agreement]
            group = group_convenio[family]
            percent = convertValues(row["% Comissão_x"])

            operation = row["Operação"]

            if operation == "COMPRA DE DIVIDA":
                operation = "COMP.D.DIV"

            if operation == "SAQUE COMPL.":
                operation = "SAQUE"

            if operation == "":
                continue

            grades = grade.get(operation, "")

            nameTable = self.get_product_name(product)

            new_row = model.copy()

            new_row["Base Comissão"] = row["Base Comissão_x"]
            new_row["Val. Base Produção"] = new_row["Base Comissão"]
            new_row["Operação"] = operation
            new_row["Produto"] = nameTable
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Convênio"] = convenio
            new_row["Parc. Atual"] = row["Parc. Atual"]
            new_row["% Mínima"] = percent * grades["min"]
            new_row["% Intermediária"] = percent * grades["med"]
            new_row["% Máxima"] = percent * grades["max"]
            new_row["% Comissão"] = percent
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Complemento"] = row["Complemento"]
            new_row["Id Tabela Banco"] = row["Complemento"]
            new_row["Venda Digital"] = row["Venda Digital"]
            new_row["Faixa Val. Seguro"] = row["Faixa Val. Seguro"]
            new_row["Faixa Val. Contrato"] = row["Faixa Val. Contrato"]
            new_row["Idade"] = row["Idade"]

            new_row = self.adding_values(new_row, row)

            list_of_convert_rows.append(new_row)

        df = pd.DataFrame(list_of_convert_rows)

        return df

    def create_close_tables(self, list_of_close_tables):

        list_of_convert_rows = []


        for index, row in list_of_close_tables.iterrows():

            row["Término_y"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")

            list_of_convert_rows.append(row)

        df = pd.DataFrame(list_of_convert_rows)

        df = df.drop(['ID_x', 'Instituição_x', 'Família Produto_x', 'Grupo Convênio_x', 'Convênio_x', 'Parc. Refin._x', '% PMT Pagas_x', '% Taxa_x', '% Comissão_x', '-_x', 'Base Comissão_x', '% Mínima_x', '% Intermediária_x', '% Máxima_x', '% Fator_x', '% TAC_x', 'Val. Teto TAC_x', 'Vigência_x', 'Término_x', 'Visualização Restrita_x', 'Val. Base Produção_x', 'Val. Base Produção_x', 'Id Tabela Banco_x', 'ATIVAÇÃO_x', 'REPASSE ATIVAÇÃO_x', '_merge'], axis=1)
        df.columns = df.columns.str.replace('_y', '')

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = convertValues(row["% Comissão_y"])

            row_close = row.copy()

            row_close["Término_y"] = datetime.now().strftime("%d/%m/%Y")

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

            operation = row["Operação"]

            if operation == "COMPRA DE DIVIDA":
                operation = "COMP.D.DIV"

            if operation == "SAQUE COMPL.":
                operation = "SAQUE"

            if operation == "":
                continue

            grades = grade.get(operation, "")

            row_open["Término_y"] = ""
            row_open["Vigência_y"] = datetime.now().strftime("%d/%m/%Y")
            row_open["ID_y"] = ''
            row_open["% Comissão_y"] = percent
            row_open["% Mínima_y"] = percent * grades["min"]
            row_open["% Intermediária_y"] = percent * grades["med"]
            row_open["% Máxima_y"] = percent * grades["max"]

            list_of_convert_open_rows.append(row_open)

        df = pd.DataFrame(list_of_convert_close_rows)
        df2 = pd.DataFrame(list_of_convert_open_rows)

        colunas_remover = ['ID_x', 'Instituição_x', 'Família Produto_x', 'Grupo Convênio_x', 'Convênio_x', 'Parc. Refin._x', '% PMT Pagas_x', '% Taxa_x', '% Comissão_x', '-_x', 'Base Comissão_x', '% Mínima_x', '% Intermediária_x', '% Máxima_x', '% Fator_x', '% TAC_x', 'Val. Teto TAC_x', 'Vigência_x', 'Término_x', 'Visualização Restrita_x', 'Val. Base Produção_x', 'Val. Base Produção_x', 'Id Tabela Banco_x', 'ATIVAÇÃO_x', 'REPASSE ATIVAÇÃO_x', '_merge']

        df.columns = df.columns.str.replace('_y', '')
        df2.columns = df.columns.str.replace('_y', '')

        df = df.drop(colunas_remover, axis=1)
        df2 = df2.drop(colunas_remover, axis=1)

        return df, df2

    def input_standard_values(self, model):

        model["Instituição"] = "PANLAFY"
        model["Parc. Refin."] = "0-0"
        model["% PMT Pagas"] = "0,00-0,00"
        model["% Taxa"] = "0,00-0,00"
        model["-"] = "%"
        model["% Fator"] = "0,000000000"
        model["% TAC"] = "0,000000"
        model["Val. Teto TAC"] = "0,000000"
        model["Faixa Val. Contrato"] = "0,00-100.000,00-LÍQUIDO"
        model["Visualização Restrita"] = "Não"

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
            if len(list_of_close_tables) > 0:
                print(f"Foram encontradas {len(list_of_close_tables)} tabelas para fechar.")
                df_close = self.create_close_tables(list_of_close_tables)
            if len(list_to_close_and_open) > 0:
                print(f"Foram encontradas {len(list_to_close_and_open)} tabelas para fechar e abrir.")
                df_close2, df_open2 = self.create_close_open_tables(list_to_close_and_open)

            print("Iniciando processo de junção dos arquivos...")
            columns_in_order = df_open.columns.tolist()

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