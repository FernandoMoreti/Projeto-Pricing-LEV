from .Bank import Bank
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import io
from ..utils.utils import convertValues, formatar_centavos, remover_acentos
from ..config.bank.TotalCashVariables import family_product, group_convenio, operation
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade

class TotalCashMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file), sheet_name=None, skiprows=4)
        return df

    def compare_archive(self, df_work, df_bank):

        todas_as_abas_limpas = []

        for nome_da_aba, df in df_bank.items():
            if df.empty:
                continue

            df.columns = [f'Coluna{i}' for i in range(1, len(df.columns) + 1)]

            df = df.dropna(how='all')

            if df.empty:
                continue

            df = df[df['Coluna2'].notna()]
            df = df[df['Coluna1'] != 'Taxa']

            df = df.rename(columns={
                'Coluna1': 'Taxa',
                'Coluna2': 'Prazo',
                'Coluna3': 'Tkt Operação',
                'Coluna4': 'Comissão',
                'Coluna5': 'Data'
            })

            df['Aba Origem'] = nome_da_aba

            product = ''

            for index, row in df.iterrows():
                if pd.isna(row["Tkt Operação"]):
                    if "INSS" in row["Aba Origem"]:
                        product = "INSS - " + row["Prazo"]
                    else:
                        product = "CONSIGNADO PRIVADO - " + row["Prazo"]
                        product = product.replace(" Produto:", "").replace(" Prestamista", "")
                df.at[index, 'Product'] = product.upper().strip()

            df = df[['Aba Origem', 'Taxa', 'Prazo', 'Tkt Operação', 'Comissão', 'Data', 'Product']]

            todas_as_abas_limpas.append(df)

        df_bank = pd.concat(todas_as_abas_limpas, ignore_index=True)

        df_work["Produto"] = df_work["Produto"].str.strip()

        for index, row in df_bank.iterrows():
            prazo_cru = row["Tkt Operação"]
            faixa_cru = row["Comissão"]

            if prazo_cru is None or pd.isna(prazo_cru):
                continue

            if str(prazo_cru).strip() == "Prazo":
                continue

            valor_str = str(prazo_cru).strip()

            if "a" in valor_str:
                partes = valor_str.split('a')
                df_bank.at[index, "Tkt Operação"] = f"{partes[0].strip()}-{partes[1].strip()}"
            else:
                prazo = valor_str.replace('x', '').replace('X', '').strip()
                valor_limpo = prazo + "-" + prazo
                df_bank.at[index, "Tkt Operação"] = valor_limpo

            if "R$" in faixa_cru:
                valor_str = str(faixa_cru).strip().replace("R$", "").replace("<", "").replace(">", "").replace("=", "").strip()
                if "a" in valor_str:
                    partes = valor_str.split('a')
                else:
                    partes = valor_str.split(' ')

                if len(partes) == 1:
                    p0 = formatar_centavos(partes[0])

                    if "PORT" in row["Product"]:
                        df_bank.at[index, "Comissão"] = f"{p0}-100.000,00-BRUTO"
                    else:
                        df_bank.at[index, "Comissão"] = f"{p0}-100.000,00-LÍQUIDO"
                else:
                    p0 = formatar_centavos(partes[0])
                    p_fim = formatar_centavos(partes[-1])

                    if "PORT" in row["Product"]:
                        df_bank.at[index, "Comissão"] = f"{p0}-{p_fim}-BRUTO"
                    else:
                        df_bank.at[index, "Comissão"] = f"{p0}-{p_fim}-LÍQUIDO"


        df_bank = df_bank[df_bank["Tkt Operação"] != "Prazo"]
        df_bank = df_bank[pd.notna(df_bank["Tkt Operação"])]

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["Product", "Tkt Operação", "Comissão"],
            right_on=["Produto", "Parc. Atual", "Faixa Val. Contrato"],
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

        list_of_open_tables = df_open.to_dict(orient="records")
        list_of_close_tables = df_close.to_dict(orient="records")

        for index, row in df_matches.iterrows():

            percent = round(convertValues(row["Data"]) * 100, 2)
            percent_work = convertValues(row["% Comissão"])

            if round(percent, 2) != percent_work:
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
        if "INSS" in product:
            return "INSS"
        elif "CONSIGNADO PRIVADO" in product:
            return "CLT"
        else:
            return "CONVENIO DESCONHECIDO"

    def getOperation(self, product):
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

            product = row["Product"]
            convenio = self.get_convenio(product)

            family = family_product[convenio]
            group = group_convenio[family]

            percent = round(convertValues(row["Data"]) * 100, 2)

            operation = self.getOperation(product)

            grades = grade.get(operation, "")

            if type(row["Prazo"]) == float:
                taxa = str(round(row["Prazo"] * 100, 2)).replace(".", ",") + "-" + str(round(row["Prazo"] * 100, 2)).replace(".", ",")
            else:
                taxa = row["Prazo"].replace(" ", "").replace("%", "")

            new_row = model.copy()

            new_row["Operação"] = operation
            new_row["Produto"] = product
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Convênio"] = convenio
            new_row["Parc. Atual"] = row["Tkt Operação"]
            new_row["% Taxa"] = taxa
            new_row["Faixa Val. Contrato"] = row["Comissão"]
            new_row["% Mínima"] = round(percent, 2) * grades["min"]
            new_row["% Intermediária"] = round(percent, 2) * grades["med"]
            new_row["% Máxima"] = round(percent, 2) * grades["max"]
            new_row["% Comissão"] = round(percent, 2)
            new_row["Complemento"] = "TX " + taxa.split("-")[0] + "%"
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Atualizações"] = "INCLUSÃO"

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

        df = df.drop(['Aba Origem', 'Taxa', 'Prazo', 'Tkt Operação', 'Comissão', 'Data',
        'Product', '_merge'], axis=1, errors='ignore')

        df.columns = df.columns.str.replace('_y', '')

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = convertValues(round(row["Data"] * 100, 2))

            row_close = row.copy()

            row_close["Término"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            row_close["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

            operation = self.getOperation(row["Product"])

            grades = grade.get(operation, "")

            if type(row["Prazo"]) == float:
                taxa = str(round(row["Prazo"] * 100, 2)).replace(".", ",") + "-" + str(round(row["Prazo"] * 100, 2)).replace(".", ",")
            else:
                taxa = row["Prazo"].replace(" ", "").replace("%", "")

            row_open["Término"] = ""
            row_open["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            row_open["ID"] = ''
            row_open["% Taxa"] = taxa
            row_open["% Comissão"] = round(percent, 2)
            row_open["% Mínima"] = round(percent, 2) * grades["min"]
            row_open["% Intermediária"] = round(percent, 2) * grades["med"]
            row_open["% Máxima"] = round(percent, 2) * grades["max"]
            row_open["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_open_rows.append(row_open)

        df = pd.DataFrame(list_of_convert_close_rows)
        df2 = pd.DataFrame(list_of_convert_open_rows)

        colunas_remover = ['Aba Origem', 'Taxa', 'Prazo', 'Tkt Operação', 'Comissão', 'Data',
       'Product', '_merge']

        df.columns = df.columns.str.replace('_y', '')
        df2.columns = df.columns.str.replace('_y', '')

        df = df.drop(colunas_remover, axis=1, errors='ignore')
        df2 = df2.drop(colunas_remover, axis=1, errors='ignore')

        return df, df2

    def input_standard_values(self, model):

        model["Instituição"] = "TOTALCASH"
        model["Parc. Refin."] = "0-0"
        model["% PMT Pagas"] = "0,00-0,00"
        model["Idade"] = "0-80"
        model["-"] = "%"
        model["Base Comissão"] = "LIQUÍDO"
        model["Val. Base Produção"] = "LIQUÍDO"
        model["% Fator"] = "0,000000000"
        model["% TAC"] = "0,000000"
        model["Val. Teto TAC"] = "0,000000"
        model["Faixa Val. Seguro"] = "0,00-0,00"
        model["Venda Digital"] = "SIM"
        model["Visualização Restrita"] = "NÃO"

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