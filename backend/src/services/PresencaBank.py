from .Bank import Bank
from datetime import datetime, timedelta
import pandas as pd
import io
from ..utils.utils import convertValues, formatar_br, remover_acentos, limpar_zeros, rename_duplicates
from ..config.bank.PanVariables import family_product, group_convenio, operation
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade

class PresencaBankMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file))
        return df

    def compare_archive(self, df_work, df_bank):

        df_bank["Tabela Nome"] = df_bank["Tabela Nome"].astype(str).str.strip().str.upper()
        df_work["Produto"] = df_work["Produto"].astype(str).str.strip().str.upper()

        first_prazo = df_bank["Prazo"].astype(str).str.split().str[0]

        df_bank["Prazo"] = first_prazo + "-" + first_prazo

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["Tabela Nome", "Prazo"],
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
            print(f"Encontrados {len(df_open)} correspondências!")
            print(f"Encontrados {len(df_close)} correspondências!")

        list_of_open_tables = df_open.to_dict(orient="records")
        list_of_close_tables = df_close.to_dict(orient="records")

        # Validar matches
        for index, row in df_matches.iterrows():

            percent = convertValues(row["Comissão"])
            percent_work = convertValues(row["% Comissão"])

            percent, bonus, tribut = self.get_retencao(percent)

            if "PRIVADO CLT" in row["Tabela Nome"]:
                tribut = 0.5
                bonus = 1
                percent = percent - 1.5

            row["bonus"] = bonus
            row["tributo"] = tribut

            if round(percent, 2) != round(percent_work, 2):
                list_to_close_and_open.append(row)

        return list_of_open_tables, list_of_close_tables, list_to_close_and_open

    def get_retencao(self, percent):

        bonus = 0
        tribut = 0

        if percent >= 8 and percent < 25:
            bonus = 0.5
        elif percent >= 25 and percent <= 40:
            bonus = 1

        if percent >= 1 and percent < 3:
            tribut = 0.5
        elif percent >= 4 and percent < 14:
            tribut = 1
        elif percent >= 14 and percent < 25:
            tribut = 1.5
        elif percent >= 25 and percent < 40:
            tribut = 2

        percent = percent - (tribut + bonus)

        return percent, bonus, tribut

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

        for nome_cidade in sorted(states.keys(), key=len, reverse=True):
            if nome_cidade in product:
                uf = states[nome_cidade]
                break
            else:
                uf = ""

        return uf

    def get_convenio(self, product):

        categorias = {
            "GOV-": ["GOVERNO", "GOV.", "GOV"],
            "FEDERAL SIAPE": ["SIAPE"],
            "PREF. ": ["PREF.", "PREFEITURA", "IPAM", "PREF"],
            "TJ | ": ["TRIBUNAL", "TJ", "TJ."],
        }

        if "FGTS" in product:
            return "FGTS"

        if "INSS" in product:
            return "INSS"

        if "PRIVADO CLT" in product:
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

        return "CONVENIO DESCONHECIDO"

    def create_open_tables(self, list_of_open_tables, model):

        list_of_convert_rows = []

        for row in list_of_open_tables:

            product = row["Tabela Nome"]
            convenio = self.get_convenio(product)

            if "-" in convenio:
                agreement = convenio.split("-")[0].strip()
            else:
                agreement = convenio.split()[0].strip()

            family = family_product[agreement]
            group = group_convenio[family]

            percent = convertValues(row["Comissão"])

            percent, bonus, tribut = self.get_retencao(percent)

            if group == "CLT":
                tribut = 0.5
                bonus = 1
                percent = percent - 1.5

            operation = row["Tipo Crédito"]

            if operation == "Novo":
                operation = "NOVO"
            elif "Cartão" in operation:
                operation = "CARTÃO"

            grades = grade.get(operation, "")

            new_row = model.copy()
            if agreement in ["INSS", "FEDERAL SIAPE", "CLT"]:
                new_row["Base Comissão"] = "BRUTO"
            else:
                new_row["Base Comissão"] = "LIQUÍDO"

            limite_min = str(row["Limite Operacional Mínimo"]).replace("R$", "").strip()
            limite_max = str(row["Limite Operacional Máximo"]).replace("R$", "").strip()
            idade_min = str(row["Idade Mínima"]).split(" ")[0]
            idade_max = str(row["Idade Máxima"]).split(" ")[0]

            new_row["Faixa Val. Contrato"] = f"{limite_min}-{limite_max}-{new_row['Base Comissão']}"

            new_row["Idade"] = idade_min + '-' + idade_max
            new_row["Operação"] = operation
            new_row["Produto"] = row["Tabela Nome"]
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Convênio"] = convenio
            new_row["Parc. Atual"] = row["Prazo"]
            new_row["% Comissão"] = percent
            new_row["% Mínima"] = percent * grades["min"]
            new_row["% Intermediária"] = percent * grades["med"]
            new_row["% Máxima"] = percent * grades["max"]
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Complemento"] = row["Tabela Id"]
            new_row["Id Tabela Banco"] = row["Tabela Id"]
            new_row["Atualizações"] = "INCLUSÃO"
            new_row["Val. Base Produção"] = new_row["Base Comissão"]
            new_row["RESERVA TRIBUTO"] = f"{str(tribut)} | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
            new_row["REPASSE RESERVA TRIBUTO"] = "0,00 | 0,00 | 0,00"
            if bonus != 0:
                new_row["BONUS VIP"] = f"{str(bonus)} | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                new_row["REPASSE BONUS VIP"] = "0,00 | 0,00 | 0,00"

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

        df = df.drop(['Tabela Id', 'Tabela Nome', 'Produto_x', 'Tipo Crédito', 'Comissão',
       'Limite Operacional Mínimo', 'Limite Operacional Máximo',
       'Taxa de Juros', 'Prazo', 'Idade Mínima', 'Idade Máxima',
       'Data Inicio Vigência', 'Data Fim Vigência', '_merge'], axis=1)

        df.columns = df.columns.str.replace('_y', '')

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = convertValues(row["Comissão"])

            row_close = row.copy()

            row_close["Término"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            row_close["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

            operation = row["Operação"]

            if operation == "Novo":
                operation = "NOVO"
            elif "Cartão" in operation:
                operation = "CARTÃO"

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
            'Tabela Id', 'Tabela Nome', 'Produto_x', 'Tipo Crédito', 'Comissão',
            'Limite Operacional Mínimo', 'Limite Operacional Máximo',
            'Taxa de Juros', 'Prazo', 'Idade Mínima', 'Idade Máxima',
            'Data Inicio Vigência', 'Data Fim Vigência', '_merge'
        ]


        df = df.drop(colunas_para_dropar, axis=1, errors='ignore')
        df2 = df2.drop(colunas_para_dropar, axis=1, errors='ignore')

        df.columns = df.columns.str.replace('_y', '')
        df2.columns = df2.columns.str.replace('_y', '')

        return df, df2

    def input_standard_values(self, model):

        model["Instituição"] = "PRESENCA BANK"
        model["Parc. Refin."] = "0-0"
        model["% PMT Pagas"] = "0,00-0,00"
        model["% Taxa"] = "0,00-0,00"
        model["-"] = "%"
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