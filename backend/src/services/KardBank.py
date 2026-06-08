from .Bank import Bank
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import io
from ..utils.utils import convertValues, formatar_br, remover_acentos
from ..config.bank.KardBankVariables import family_product, group_convenio, operation
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade

class KardBankMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file))
        return df

    def get_retencao(self, percent):
        bonus = 0

        if percent > 5 and percent <= 10:
            bonus = 0.5
            percent = percent - bonus
        elif percent > 10 and percent <= 15:
            bonus = 1
            percent = percent - bonus
        elif percent > 15 and percent <= 20:
            bonus = 1.5
            percent = percent - bonus
        elif percent > 20:
            bonus = 2
            percent = percent - bonus

        return percent, bonus

    def compare_archive(self, df_work, df_bank):

        df_bank['Tabela/Nome do Produto'] = df_bank['Tabela/Nome do Produto'].str.strip()
        df_work["Produto"] = df_work["Produto"].str.strip()

        df_bank["Prazo Final"] = df_bank["Prazo Inicial"].astype(str) + '-' + df_bank["Prazo Final"].astype(str)

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["Tabela/Nome do Produto", "Prazo Final"],
            right_on=["Produto", "Parc. Atual"],
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

            percent = convertValues(row["À Vista Empresa"])

            if row["Operação"] == "NOVO":
                bonus = 0.25
                percent = percent - bonus
            else:
                percent, bonus = self.get_retencao(percent)

            percent_work = convertValues(row["% Comissão"])

            row["retencao"] = bonus

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
        if "-" in product:
            firstProduct = str(product).upper().split("-")[0].strip()
        else:
            firstProduct = product
        categorias = {
            "GOV-": ["GOV", "GOV_", "GOV.", "SPPREV_", "AMA", "PMESP", "PMMG", "IPSEMG", "IPSM", "PM", "POL", "CBMG", "PIAUI", "CEARÁ", "AMPREV_", "IGEPREV_AS_TAXA"],
            "FEDERAL SIAPE": ["SIAPE", "SIA"],
            "TJ | ": ["TJ ", "TJ_", "TJ.", "TRT"],
            "PREF. ": ["PREF", "PREF_", "PREF.", "IPREM", "RCC", "IPAM", "IPREF", "COMISSIONADOS", "PREVIJUNO", "EMP"],
        }

        if firstProduct in ["AERONAUTICA", "MARINHA", "FGTS", "INSS", "CLT", "INSSC15"]:
            return firstProduct

        if "IPMO_RMC_TAXA" in product:
            return "PREF. OSASCO SP"

        for categoria, prefixos in categorias.items():
            prefixo_encontrado = next((p for p in prefixos if p in firstProduct), None)
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

            product = row["Tabela/Nome do Produto"]
            convenio = self.get_convenio(product)

            if "-" in convenio:
                agreement = convenio.split("-")[0].strip()
            else:
                agreement = convenio.split(" ")[0].strip()

            family = family_product[agreement]
            group = group_convenio[family]

            percent = convertValues(row["À Vista Empresa"])

            percent, bonus = self.get_retencao(percent)

            operation = self.getOperation(row["Tipo de Contrato"])

            grades = grade.get(operation, "")

            new_row = model.copy()

            new_row["Operação"] = operation
            new_row["Produto"] = row["Tabela/Nome do Produto"]
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Convênio"] = convenio
            new_row["Parc. Atual"] = row["Prazo Final"]
            new_row["% Mínima"] = percent * grades["min"]
            new_row["% Intermediária"] = percent * grades["med"]
            new_row["% Máxima"] = percent * grades["max"]
            new_row["% Comissão"] = percent
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Atualizações"] = "INCLUSÃO"

            if bonus != 0:
                new_row["BONUS VIP"] = "{:.2f}".format(bonus).replace('.', ',') + " | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                new_row["REPASSE BONUS VIP"] = "0,00 | 0,00 | 0,00"

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

        df = df.drop(['Convênio_x', 'Tabela/Nome do Produto', 'Código no Banco',
            'Id de Vigência', 'Início', 'Fim', 'Prazo Inicial', 'Prazo Final',
            'Tipo de Contrato', 'Tipo de Formalização', 'Fator', 'Taxa a.m',
            'Id de Prazo/Faixa', 'Idade Mínima', 'Idade Máxima',
            'Valor Contrato Inicial', 'Valor Contrato Final',
            'Valor Contrato Referência', 'Taxa Inicial', 'Taxa Final',
            'À Vista Empresa', 'Bônus Empresa', 'Diferido Empresa',
            'À Vista Repasse 1', 'Bônus Repasse 1', 'Diferido Repasse 1', '_merge'], axis=1, errors='ignore')

        df.columns = df.columns.str.replace('_y', '')

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = convertValues(row["À Vista Empresa"])

            percent, bonus = self.get_retencao(percent)

            row_close = row.copy()

            row_close["Término"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            row_close["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

            product = row["Tabela/Nome do Produto"]

            operation = self.getOperation(row["Tipo de Contrato"])

            grades = grade.get(operation, "")

            row_open["Término"] = ""
            row_open["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            row_open["ID"] = ''
            row_open["% Comissão"] = percent
            row_open["% Mínima"] = percent * grades["min"]
            row_open["% Intermediária"] = percent * grades["med"]
            row_open["% Máxima"] = percent * grades["max"]
            row_open["Atualizações"] = "ALTERAÇÃO"

            if bonus != 0:
                row_open["BONUS VIP"] = "{:.2f}".format(bonus).replace('.', ',') + " | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                row_open["REPASSE BONUS VIP"] = "0,00 | 0,00 | 0,00"

            list_of_convert_open_rows.append(row_open)

        df = pd.DataFrame(list_of_convert_close_rows)
        df2 = pd.DataFrame(list_of_convert_open_rows)

        colunas_remover = ['Convênio_x', 'Tabela/Nome do Produto', 'Código no Banco',
            'Id de Vigência', 'Início', 'Fim', 'Prazo Inicial', 'Prazo Final',
            'Tipo de Contrato', 'Tipo de Formalização', 'Fator', 'Taxa a.m',
            'Id de Prazo/Faixa', 'Idade Mínima', 'Idade Máxima',
            'Valor Contrato Inicial', 'Valor Contrato Final',
            'Valor Contrato Referência', 'Taxa Inicial', 'Taxa Final',
            'À Vista Empresa', 'Bônus Empresa', 'Diferido Empresa',
            'À Vista Repasse 1', 'Bônus Repasse 1', 'Diferido Repasse 1', '_merge']

        df.columns = df.columns.str.replace('_y', '')
        df2.columns = df.columns.str.replace('_y', '')

        df = df.drop(colunas_remover, axis=1, errors='ignore')
        df2 = df2.drop(colunas_remover, axis=1, errors='ignore')

        return df, df2

    def input_standard_values(self, model):

        model["Instituição"] = "KARDBANK"
        model["Parc. Refin."] = "0-0"
        model["% PMT Pagas"] = "0,00-0,00"
        model["% Taxa"] = "0,00-0,00"
        model["Idade"] = "0-80"
        model["-"] = "%"
        model["Base Comissão"] = "LIQUÍDO"
        model["Val. Base Produção"] = "LIQUÍDO"
        model["% Fator"] = "0,000000000"
        model["% TAC"] = "0,000000"
        model["Val. Teto TAC"] = "0,000000"
        model["Faixa Val. Contrato"] = "0,00-100.000,00-LÍQUIDO"
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