from .Bank import Bank
from datetime import datetime, timedelta
import pandas as pd
import io
from ..utils.utils import convertValues, formatar_br, remover_acentos, limpar_zeros, rename_duplicates
from ..config.bank.PanVariables import family_product, group_convenio, operation
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade
import numpy as np

class ParanaBankMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file))
        df = df.iloc[:-2]
        return df

    def compare_archive(self, df_work, df_bank):

        exclude_list = "COM SEGURO"
        df_bank = df_bank[~df_bank["Desc Regra"].str.contains(exclude_list, case=False, na=False)]

        df_bank["ParcelasMax"] = df_bank["ParcelasMin"].astype(str).str.replace(".0", "") + "-" + df_bank["ParcelasMax"].astype(str).str.replace(".0", "")
        df_work["Produto"] = df_work["Produto"].astype(str).str.strip()
        df_work["Parc. Atual"] = df_work["Parc. Atual"].astype(str).str.strip()

        df_work["Produto"] = df_work["Produto"].str.strip()

        pedacos_processados = []
        grupos = df_bank.groupby(["Desc Regra", "ParcelasMax"])

        for (regra, prazo), df_do_grupo in grupos:
            df_sub = df_do_grupo.copy()

            df_sub["TaxaMin_Pct"] = (df_sub["TaxaMin"] * 100).round(2)
            df_sub["TaxaMax_Pct"] = np.floor(df_sub["TaxaMax"] * 10000) / 100

            max_value = df_sub["TaxaMax_Pct"].max()

            nao_eh_o_maior = df_sub["TaxaMax_Pct"] < max_value
            df_sub.loc[nao_eh_o_maior, "TaxaMax_Pct"] = (df_sub.loc[nao_eh_o_maior, "TaxaMax_Pct"]).round(2)

            min_str = df_sub["TaxaMin_Pct"].map('{:.2f}'.format).str.replace('.', ',', regex=False)
            max_str = df_sub["TaxaMax_Pct"].map('{:.2f}'.format).str.replace('.', ',', regex=False)

            df_sub["TaxaMax"] = min_str + "-" + max_str

            pedacos_processados.append(df_sub)

        df_bank = pd.concat(pedacos_processados, ignore_index=True)

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["Desc Regra", "ParcelasMax", "TaxaMax"],
            right_on=["Produto", "Parc. Atual", "% Taxa"],
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

            percent = round(convertValues(row["A Vista"] * 100), 2)
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

        categorias = {
            "GOV-": ["GOVERNO", "POL", "ESTADO", "BOMBEIRO", "META", "IPSM", "SÃO PAULO PREV.", "SPPREV", "IPSM"],
            "FEDERAL SIAPE": ["SIAPE", "SIA", "SIAPEWEBSERVICE"],
            "PREF. ": ["PREF", "PREFEITURA", "IPM", "PM", "INST", "SANASA", "IPREM", "CAMPREV", "AFUMUSA", "PREVISERTI", "IPREVSANTOS", "IPREVSANTOS", "CAXIASPREV", "CAAPSML", "PREVISO"],
            "TJ | ": ["TRIBUNAL", "TJ", "TJ."],
        }

        if "FGTS" in product:
            return "FGTS"

        if "INSS" in product:
            return "INSS"

        if "CRED TRAB" in product:
            return "CLT"

        if "PREVISO" in product:
            return "PREF. SORRISO MT"

        for categoria, prefixos in categorias.items():
            prefixo_encontrado = next((p for p in prefixos if p in product), None)
            if prefixo_encontrado:
                convenio = categoria

                if convenio == "FEDERAL SIAPE":
                    return convenio

                if convenio == "PREF. ":
                    if product == "INST.P.R.P-PORT":
                        return "PREF. RIBEIRAO PRETO SP"
                    city = self.extract_city(product)
                    uf = self.extract_uf_of_city(city)

                    if city == "":
                        return ""

                    convenio = convenio + city + uf
                    return convenio

                if convenio in ["GOV-", "TJ | "]:
                    uf = self.extract_uf_of_state(product)
                    convenio = convenio + uf
                    return convenio

        return ""

    def create_open_tables(self, list_of_open_tables, model):

        list_of_convert_rows = []

        for row in list_of_open_tables:

            product = row["Nome Empregador"]
            convenio = self.get_convenio(product)

            if "-" in convenio and convenio:
                agreement = convenio.split("-")[0].strip()
            else:
                if product == "AFUMUSA" or product == "PREVISERTI":
                    agreement = "PREF."
                else:
                    agreement = convenio.split()[0].strip()

            family = family_product[agreement]
            group = group_convenio[family]

            percent = convertValues(row["A Vista"]) * 100

            operation = row["Tipo Operacão"]

            if operation == "NOVO COB":
                operation = "NOVO"
            elif operation == "REFIN COB":
                operation = "REFIN"
            elif operation == "REFIN+PORT":
                operation = "PORTAB/REFIN"

            if operation == "PORTABILIDADE":
                base_commission = "BRUTO"
            else:
                base_commission = "LÍQUIDO"

            grades = grade.get(operation, "")

            new_row = model.copy()

            new_row["Operação"] = operation
            new_row["Produto"] = row["Desc Regra"]
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["% Taxa"] = row["TaxaMax"]
            new_row["Base Comissão"] = base_commission
            new_row["Val. Base Produção"] = base_commission
            new_row["Convênio"] = convenio
            new_row["Parc. Atual"] = row["TaxaMax"]
            new_row["% Mínima"] = percent * grades["min"]
            new_row["% Intermediária"] = percent * grades["med"]
            new_row["% Máxima"] = percent * grades["max"]
            new_row["% Comissão"] = percent
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Complemento"] = row["Cod Regra"]
            new_row["Id Tabela Banco"] = row["Cod Regra"]
            new_row["Atualizações"] = "INCLUSÃO"

            list_of_convert_rows.append(new_row)

        df = pd.DataFrame(list_of_convert_rows)

        return df

    def create_close_tables(self, list_of_close_tables):

        list_of_convert_rows = []

        for row in list_of_close_tables:

            row["Término"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            row["Atualizações"] = "ENCERRAMENTO"
            row["Val. Base Produção"] = row["Base Comissão"]

            list_of_convert_rows.append(row)

        df = pd.DataFrame(list_of_convert_rows)

        df = df.drop(['Empregador Unico', 'Empregador', 'Nome Empregador', 'Tipo Operacão',
       'Cod Regra', 'Desc Regra', 'MinPago', 'ParcelasMin', 'ParcelasMax',
       'TaxaMin', 'TaxaMax', 'A Vista', 'PMT', 'Data Início', 'Seguro',
       'IniVigSeguro', 'PermiteSeguro', 'PermiteJuncao', 'Parcela', 'ID_Linha',
       'TaxaMin_Pct', 'TaxaMax_Pct', '_merge'], axis=1)

        df.columns = df.columns.str.replace('_y', '')

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = convertValues(row["A Vista"]) * 100

            row_close = row.copy()

            row_close["Término"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            row_close["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

            operation = row["Operação"]

            grades = grade.get(operation, "")

            row_open["Término"] = ''
            row_open["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            row_open["ID"] = ''
            row_open["% Comissão"] = percent
            row_open["Operação"] = operation
            row_open["% Mínima"] = percent * grades["min"]
            row_open["% Intermediária"] = percent * grades["med"]
            row_open["% Máxima"] = percent * grades["max"]
            row_open["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_open_rows.append(row_open)

        df = pd.DataFrame(list_of_convert_close_rows)
        df2 = pd.DataFrame(list_of_convert_open_rows)


        colunas_para_dropar = [
            'Empregador Unico', 'Empregador', 'Nome Empregador', 'Tipo Operacão',
            'Cod Regra', 'Desc Regra', 'MinPago', 'ParcelasMin', 'ParcelasMax',
            'TaxaMin', 'TaxaMax', 'A Vista', 'PMT', 'Data Início', 'Seguro',
            'IniVigSeguro', 'PermiteSeguro', 'PermiteJuncao', 'Parcela', 'ID_Linha',
            'TaxaMin_Pct', 'TaxaMax_Pct', '_merge'
        ]

        df = df.drop(colunas_para_dropar, axis=1, errors='ignore')
        df2 = df2.drop(colunas_para_dropar, axis=1, errors='ignore')

        return df, df2

    def input_standard_values(self, model):

        model["Instituição"] = "PARANA BANCO"
        model["Parc. Refin."] = "0-0"
        model["% PMT Pagas"] = "0,00-0,00"
        model["Idade"] = "0-80"
        model["-"] = "%"
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