from .Bank import Bank
from datetime import datetime, timedelta
import pandas as pd
import io
from ..utils.utils import convertValues, formatar_faixa_valores, remover_acentos, limpar_zeros, rename_duplicates
from ..config.bank.PanVariables import family_product, group_convenio, operation
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade
import numpy as np

class EvolMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file))
        return df

    def get_bonus(self, family, percent):
        if family == "FGTS":
            percent = round(percent, 1)
            return percent / 10
        elif family in ["INSS", "CLT"]:
            if percent > 0 and percent < 5:
                return 0.5
            elif percent >= 5 and percent < 10:
                return 1
            elif percent >= 10 and percent < 15:
                return 1.5
            else:
                return 2

    def compare_archive(self, df_work, df_bank):

        df_bank["Prazo Máximo"] = df_bank["Prazo Mínimo"].astype(str) + "-" + df_bank["Prazo Máximo"].astype(str)

        df_bank["Nome Tabela"] = df_bank["Nome Tabela"].astype(str).str.strip()
        df_work["Produto"] = df_work["Produto"].astype(str).str.strip()

        df_bank["Valor Final"] = df_bank["Valor Final"].astype(str)

        for index, row in df_bank.iterrows():

            if "Bruto" in str(row["Tipo Comissão"]):
                sufix = "BRUTO"
            else:
                sufix = "LIQUÍDO"

            value = str(row["Valor Inicial"]) + "-" + str(row["Valor Final"])
            faixa = formatar_faixa_valores(value)
            df_bank.at[index, "Valor Final"] = faixa + "-" + sufix

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["Nome Tabela", "Prazo Máximo", "Valor Final"],
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

            percent = round(convertValues(row["Comissão"] * 100), 2)
            percent_work = round(convertValues(row["% Comissão"]), 2)

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
        product = remover_acentos(product)

        if "ESTADO" in product:
            product = product.replace("ESTADO", "")

        for nome_cidade in sorted(states.keys(), key=len, reverse=True):
            if nome_cidade in product:
                uf = states[nome_cidade]
                break
            else:
                uf = ""

        return uf

    def get_convenio(self, product):
        if "INSS" in product:
            return "INSS"
        if "PORT" in product:
            return "INSS"
        elif "PRIVADO" in product:
            return "CLT"
        elif "CLT" in product:
            return "CLT"
        elif "FGTS" in product:
            return "FGTS"
        elif "FIXO" in product:
            return "FGTS"
        else:
            return "CONVENIO DESCONHECIDO"

    def get_operation(self, product):
        if "FLEX" in product:
            return "NOVO"
        elif "CLT" in product:
            return "NOVO"
        elif "FIXO" in product:
            return "NOVO"
        elif "NOVO" in product:
            return "NOVO"
        if "PORT + REFIN" in product:
            return "PORTAB/REFIN"
        if "PORTABILIDADE" in product:
            return "PORTABILIDADE"
        elif "PRIVADO" in product:
            return "NOVO"
        elif "SAQUE" in product:
            return "NOVO"
        else:
            return "OPERAÇÃO DESCONHECIDa"

    def create_open_tables(self, list_of_open_tables, model):

        list_of_convert_rows = []

        for row in list_of_open_tables:

            product = row["Nome Tabela"]
            convenio = self.get_convenio(product)

            family = family_product[convenio]
            group = group_convenio[family]

            percent = convertValues(row["Comissão"])

            operation = self.get_operation(product)

            bonus = self.get_bonus(family, percent)
            percent = percent - bonus

            if "PORT" in operation:
                base_commission = "BRUTO"
            else:
                base_commission = "LÍQUIDO"

            grades = grade.get(operation, "")

            new_row = model.copy()

            new_row["Operação"] = operation
            new_row["Produto"] = product
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Base Comissão"] = base_commission
            new_row["Val. Base Produção"] = base_commission
            new_row["Convênio"] = convenio
            new_row["Faixa Val. Contrato"] = row["Valor Final"]
            new_row["Parc. Atual"] = row["Prazo Máximo"]
            new_row["% Mínima"] = percent * grades["min"]
            new_row["% Intermediária"] = percent * grades["med"]
            new_row["% Máxima"] = percent * grades["max"]
            new_row["% Comissão"] = percent
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Complemento"] = row["Id Tabela Principal"]
            new_row["Id Tabela Banco"] = row["Id Tabela Principal"]
            new_row["BONUS VIP"] = f"{bonus:.2f}".replace(".", ",") + " | " + base_commission + " | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
            new_row["REPASSE BONUS VIP"] = "0,00 | 0,00 | 0,00"
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

        df = df.drop(['Id Tabela Principal', 'Id Tabela', 'Nome Tabela', 'Status',
       'Tipo Comissão', 'Comissão', 'Valor Inicial', 'Valor Final',
       'Prazo Mínimo', 'Prazo Máximo', 'Máximo de Parcelas',
       'Data Vigência Inicial', 'Data Vigência Final', '_merge'], axis=1)

        df.columns = df.columns.str.replace('_y', '')

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = convertValues(row["Comissão"])
            bonus = self.get_bonus(row["Família Produto"], percent)
            percent = percent - bonus

            row_close = row.copy()

            row_close["Término"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            row_close["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

            if "PORT" in operation:
                base_commission = "BRUTO"
            else:
                base_commission = "LÍQUIDO"

            operation = self.get_operation(row["Nome Tabela"])

            grades = grade.get(operation, "")

            row_open["Término"] = ''
            row_open["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            row_open["ID"] = ''
            row_open["% Comissão"] = percent
            row_open["Operação"] = operation
            row_open["% Mínima"] = percent * grades["min"]
            row_open["% Intermediária"] = percent * grades["med"]
            row_open["% Máxima"] = percent * grades["max"]
            row_open["BONUS VIP"] = f"{bonus:.2f}".replace(".", ",") + " | " + base_commission + " | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
            row_open["REPASSE BONUS VIP"] = "0,00 | 0,00 | 0,00"
            row_open["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_open_rows.append(row_open)

        df = pd.DataFrame(list_of_convert_close_rows)
        df2 = pd.DataFrame(list_of_convert_open_rows)


        colunas_para_dropar = [
            'Id Tabela Principal', 'Id Tabela', 'Nome Tabela', 'Status',
            'Tipo Comissão', 'Comissão', 'Valor Inicial', 'Valor Final',
            'Prazo Mínimo', 'Prazo Máximo', 'Máximo de Parcelas',
            'Data Vigência Inicial', 'Data Vigência Final', '_merge'
        ]

        df = df.drop(colunas_para_dropar, axis=1, errors='ignore')
        df2 = df2.drop(colunas_para_dropar, axis=1, errors='ignore')

        return df, df2

    def input_standard_values(self, model):

        model["Instituição"] = "EVOL"
        model["Parc. Refin."] = "0-0"
        model["% PMT Pagas"] = "0,00-0,00"
        model["Idade"] = "0-80"
        model["-"] = "%"
        model["% Fator"] = "0,000000000"
        model["% Taxa"] = "0,00-0,00"
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