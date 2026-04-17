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

            print(row)

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
            new_row["BONUS EXTRA"] = row["BONUS EXTRA"]
            new_row["REPASSE BONUS EXTRA"] = row["REPASSE BONUS EXTRA"]
            new_row["ANTECIPAÇÃO"] = row["ANTECIPAÇÃO"]
            new_row["REPASSE ANTECIPAÇÃO"] = row["REPASSE ANTECIPAÇÃO"]
            new_row["ATIVAÇÃO"] = row["ATIVAÇÃO_x"]
            new_row["REPASSE ATIVAÇÃO"] = row["REPASSE ATIVAÇÃO_x"]
            new_row["BONUS VIP"] = row["BONUS VIP"]
            new_row["REPASSE BONUS VIP"] = row["REPASSE BONUS VIP"]
            new_row["BONUS VP"] = row["BONUS VP"]
            new_row["REPASSE BONUS VP"] = row["REPASSE BONUS VP"]
            new_row["PRÉ-ADESÃO"] = row["PRÉ-ADESÃO"]
            new_row["REPASSE PRÉ-ADESÃO"] = row["REPASSE PRÉ-ADESÃO"]
            new_row["RESERVA TRIBUTO"] = row["RESERVA TRIBUTO"]
            new_row["REPASSE RESERVA TRIBUTO"] = row["REPASSE RESERVA TRIBUTO"]
            new_row["SEGURO PAN"] = row["SEGURO PAN"]
            new_row["REPASSE SEGURO PAN"] = row["REPASSE SEGURO PAN"]
            new_row["VARIAVEL COMERCIAL"] = row["VARIAVEL COMERCIAL"]
            new_row["REPASSE VARIAVEL COMERCIAL"] = row["REPASSE VARIAVEL COMERCIAL"]

            list_of_convert_rows.append(new_row)

        df = pd.DataFrame(list_of_convert_rows)

        df.to_excel("123.xlsx", index=False)

        return df

    def create_close_tables(self, list_of_close_tables):

        list_of_convert_rows = []

        for index, row in list_of_close_tables.iterrows():

            row["Produto"] = row["Produto_y"]
            row["Término"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")

            list_of_convert_rows.append(row)

        df = pd.DataFrame(list_of_convert_rows)

        df = df.drop(['Atualizações', 'Convenio', 'Tabela', 'Produto', 'Produto_x', 'DataInicioVigencia', 'PrazoDe', 'PrazoAte', 'TktmMin', 'TktmMax', 'Taxa', 'TaxaMaxima', 'CalculoComissao', 'Id Tabela Nova', 'IdConvenio', 'ComissaoAto', 'CdvpDiferidoVp', 'CdvpDiferidoMensal', 'CdvpDiferidoFuturo', 'CintDiferidoVp', 'CintDiferidoMensal', 'CintDiferidoFuturo', 'CprodDiferidoVp', 'CprodDiferidoMensal', 'CprodDiferidoFuturo', 'CmutDiferidoVp', 'CmutDiferidoMensal', 'CmutDiferidoFuturo', 'TotalDiferidoVp', 'TotalDiferidoMensal', 'TotalDiferidoFuturo', 'prazo_formatado', '_merge'], axis=1)
        df = df.rename(columns = {
            'Produto_y': 'Produto'
        })

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = convertValues(row["ComissaoAto"] * 100)

            row_close = row.copy()

            row_close["Término"] = datetime.now().strftime("%d/%m/%Y")

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

            print(row)

            operation = row["Operação"]
            grades = grade.get(operation, "")

            row_open["Término"] = ""
            row_open["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            row_open["ID"] = ''
            row_open["% Comissão"] = convertValues(row["ComissaoAto"] * 100)
            row_open["% Mínima"] = percent * grades["min"]
            row_open["% Intermediária"] = percent * grades["med"]
            row_open["% Máxima"] = percent * grades["max"]

            list_of_convert_open_rows.append(row_open)

        df = pd.DataFrame(list_of_convert_close_rows)
        df2 = pd.DataFrame(list_of_convert_open_rows)

        colunas_remover = ['Atualizações', 'Convenio', 'Tabela', 'Produto_x', 'DataInicioVigencia', 'PrazoDe', 'PrazoAte', 'TktmMin', 'TktmMax', 'Taxa', 'TaxaMaxima', 'CalculoComissao', 'Id Tabela Nova', 'IdConvenio', 'ComissaoAto', 'CdvpDiferidoVp', 'CdvpDiferidoMensal', 'CdvpDiferidoFuturo', 'CintDiferidoVp', 'CintDiferidoMensal', 'CintDiferidoFuturo', 'CprodDiferidoVp', 'CprodDiferidoMensal', 'CprodDiferidoFuturo', 'CmutDiferidoVp', 'CmutDiferidoMensal', 'CmutDiferidoFuturo', 'TotalDiferidoVp', 'TotalDiferidoMensal', 'TotalDiferidoFuturo', 'prazo_formatado', '_merge', 'Diferido']

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
            dfs_para_juntar = [df for df in [df_close, df_close2, df_open, df_open2] if df is not None and not df.empty]
            if dfs_para_juntar:
                df_final = pd.concat(dfs_para_juntar, axis=0, ignore_index=True, sort=False)
                print(f"Sucesso! Total de linhas: {len(df_final)}")
            else:
                print("Nenhum dado encontrado para juntar.")
                df_final = pd.DataFrame()
            print("Processo de junção finalizado!")

            print("Processo concluído!")
            return df_final

        except Exception as e:
            print(f"Erro durante o processamento: {str(e)}")
            return "error"