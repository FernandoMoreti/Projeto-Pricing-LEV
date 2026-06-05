from .Bank import Bank
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import io
from ..utils.utils import convertValues, formatar_br, remover_acentos
from ..config.bank.SabemiVariables import family_product, group_convenio, operation
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade

class SabemiMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file), sheet_name=None)
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
                'Coluna2': 'Id da tabela',
                'Coluna3': 'comissao',
                'Coluna4': 'taxa',
                'Coluna5': 'nome tabela'
            })

            df['Aba Origem'] = nome_da_aba

            df = df[['Aba Origem', 'Taxa', 'Id da tabela', 'comissao', 'taxa', 'nome tabela']]

            df = df[df["Aba Origem"] != "FATORES DAS TABELAS VARIÁVEIS"]
            df = df[df["Aba Origem"] != "L'ARCA"]
            df = df[df["Aba Origem"] != "DAYCOVAL"]

            product = ''

            names = ['SIAPE - SS', 'SIAPE SÊNIOR - SS', 'EXÉRCITO - SS', 'EXÉRCITO SÊNIOR- SS', 'AERO - SS', 'MARINHA - SS', 'SIAPE', 'SIAPE - SENIOR', 'EXÉRCITO', 'EXÉRCITO - SENIOR', 'AERO', 'AERO -  SENIOR', 'MARINHA', 'MARINHA - SENIOR', 'EXÉRCITO']

            type = ''
            ope = ''

            for index, row in df.iterrows():
                if str(row["Id da tabela"]).strip() in names:
                    type = str(row["Id da tabela"]).strip()
                if pd.notna(row["nome tabela"]):
                    if row["Aba Origem"] == "RP" and row["nome tabela"] != "Operação e Prazo":
                        product = "RP - " + type + " - " + " ".join(row["nome tabela"].split(" ")[2:])
                    elif row["Aba Origem"] == "RP - CLIENTE NOVO" and row["nome tabela"] != "Operação e Prazo":
                        product = "RP - CLIENTE NOVO - " + type + " - " + " ".join(row["nome tabela"].split(" ")[2:])
                    elif row["Aba Origem"] == "FUTURO" and row["nome tabela"] != "Operação e Prazo":
                        product = "FUTUROPREV - " + type + " - " + " ".join(row["nome tabela"].split(" ")[2:])
                    elif row["Aba Origem"] == "SIMPALA" and row["nome tabela"] != "Operação e Prazo":
                        product = "SIMPALA - " + type + " - " + " ".join(row["nome tabela"].split(" ")[2:])

                    if str(row["nome tabela"]).split(" ")[1] in ['ML', 'ME', 'CDV', 'RFN']:
                        ope = operation[str(row["nome tabela"]).split(" ")[1]]
                    df.at[index, 'Operation'] = ope.upper().strip()

                df.at[index, 'Product'] = product.upper().strip()

            todas_as_abas_limpas.append(df)

        df_bank = pd.concat(todas_as_abas_limpas, ignore_index=True)
        df_bank = df_bank[df_bank["nome tabela"] != "Operação e Prazo"]
        df_bank = df_bank.dropna(subset=["nome tabela"])

        df_work["Produto"] = df_work["Produto"].str.strip()

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["Product", "Operation"],
            right_on=["Produto", "Operação"],
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

        df_open.to_excel("open.xlsx", index=False)

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
        if "-" in product:
            firstProduct = str(product).upper().split("-")[0].strip()
        else:
            firstProduct = product
        categorias = {
            "GOV-": ["GOV", "GOV_", "GOV.", "SPPREV_", "AMA", "PMESP", "PMMG", "IPSEMG", "IPSM", "PM", "POL", "CBMG", "PIAUI", "CEARÁ", "AMPREV_", "IGEPREV_AS_TAXA"],
            "FEDERAL SIAPE": ["SIAPE", "SIA"],
            "TJ | ": ["TJ ", "TJ_", "TJ.", "TRT"],
            "PREF. ": ["PREF", "PREF_", "PREF.", "IPREM", "RCC", "IPAM", "IPREF", "COMISSIONADOS"],
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