from .Bank import Bank
from datetime import datetime
import pandas as pd
import io
from ..utils.utils import convertValues, remover_acentos
from ..config.bank.CapitalConsigVariables import family_product, group_convenio
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade

class CapitalConsigMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file))
        return df

    def get_retencao(self, value):

        if value <= 10:
            bonus = 2
            resultado = value - 2
        elif value <= 20:
            bonus = 3
            resultado = value - 3
        else:
            bonus = 4
            resultado = value - 4

        return resultado / 100, bonus

    def compare_archive(self, df_work, df_bank):

        df_bank["prazo_formatado"] = df_bank["PRAZO "].astype(str) + "-" + df_bank["PRAZO "].astype(str)
        df_bank["NOMENCLATURA FUNÇÃO"] = df_bank["NOMENCLATURA FUNÇÃO"].astype(str).str.strip()
        df_bank["prazo_formatado"] = df_bank["prazo_formatado"].astype(str).str.strip()
        df_work["Produto"] = df_work["Produto"].astype(str).str.strip()
        df_work["Parc. Atual"] = df_work["Parc. Atual"].astype(str).str.strip()

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["NOMENCLATURA FUNÇÃO", "prazo_formatado"],
            right_on=["Produto", "Parc. Atual"],
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

        for index, row in df_open.iterrows():

            retencao, bonus = self.get_retencao(convertValues(row["% PROMOTORA"] * 100))

            row["% PROMOTORA"] = retencao
            row["BONUS"] = bonus

            list_of_open_tables.append(row)

        for index, row in df_matches.iterrows():

            retencao, bonus = self.get_retencao(convertValues(row["% PROMOTORA"] * 100))

            row["% PROMOTORA"] = retencao
            row["BONUS"] = bonus

            percent = convertValues(row["% PROMOTORA"] * 100)
            percent_work = convertValues(row["% Comissão"])
            if percent != percent_work:
                list_to_close_and_open.append(row)

        return list_of_open_tables, list_of_close_tables, list_to_close_and_open

    def extract_city(self, rest_of_product):
        rest_of_product = str(rest_of_product).upper().strip()

        cidade = rest_of_product.split("_")[0]

        sep = " "

        if sep in cidade:
            cidade = cidade.split(" ")[0]

        if cidade in ["CAMPINA", "PORTO", "SANTA", "SAO", "BELO"]:
            cidade = rest_of_product.split("_")[0] + " " + rest_of_product.split("_")[1]

        cidade = remover_acentos(cidade)

        if cidade.startswith("PREV "):
            cidade = cidade.split(" ")[1]
            city = "DE " + citys.get(cidade, "")
            return city

        if cidade == "IPAM":
            return ""

        city = citys.get(cidade, "")

        return city

    def extract_uf_of_city(self, city):
        city = str(city).upper().strip()

        if city.startswith("DE "):
            city = city.split(" ")[1]

        uf = " " + citys_uf.get(city, "")

        return uf

    def extract_uf_of_state(self, rest_of_product):
        rest_of_product = str(rest_of_product).upper().strip()

        state = rest_of_product.split("_")[0]

        state = remover_acentos(state)

        if len(state) == 2:
            return state

        uf = states.get(state, "")

        return uf

    def get_convenio(self, product):
        product = str(product).upper()
        categorias = {
            "GOV-": ["GOV ", "GOV_", "GOV.", "SPPREV_"],
            "FEDERAL SIAPE": ["SIAPE ", "SIAPE_", "SIAPE."],
            "PREF. ": ["PREF ", "PREF_", "PREF."],
            "TJ | ": ["TJ ", "TJ_", "TJ."]
        }

        for categoria, prefixos in categorias.items():
            prefixo_encontrado = next((p for p in prefixos if p in product), None)

            if prefixo_encontrado:
                partes = product.split(prefixo_encontrado, 1)
                rest_of_product = partes[1].strip() if len(partes) > 1 else ""
                convenio = categoria

                if convenio == "FEDERAL SIAPE":
                    return convenio

                if convenio == "PREF. ":
                    city = self.extract_city(rest_of_product)
                    uf = self.extract_uf_of_city(city)

                    if city == "":
                        return ""

                    convenio = convenio + city + uf
                    return convenio

                if convenio in ["GOV-", "TJ | "]:
                    uf = self.extract_uf_of_state(rest_of_product)
                    convenio = convenio + uf
                    return convenio

        return "CONVENIO DESCONHECIDO"

    def create_open_tables(self, list_of_open_tables, model):

        list_of_convert_rows = []

        for row in list_of_open_tables:

            product = row["NOMENCLATURA FUNÇÃO"]

            convenio = self.get_convenio(product)

            agreement = row[" CONVENIO"].strip().split(" ")[0]
            family = family_product[agreement]
            group = group_convenio[family]
            percent = convertValues(row["% PROMOTORA"] * 100)

            new_row = model.copy()

            if "_EMP_" in product:
                new_row["Operação"] = "NOVO"
            else:
                new_row["Operação"] = "CARTÃO"

            operation = new_row["Operação"]
            grades = grade.get(operation, "")

            new_row["Produto"] = product
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Convênio"] = convenio
            new_row["Parc. Atual"] = row["prazo_formatado"]
            new_row["% Mínima"] = percent * grades["min"]
            new_row["% Intermediária"] = percent * grades["med"]
            new_row["% Máxima"] = percent * grades["max"]
            new_row["% Comissão"] = percent
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Complemento"] = int(row["CÓD  "])
            new_row["Id Tabela Banco"] = int(row["CÓD  "])
            new_row["BONUS VIP"] = f"{row['BONUS']},00 | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"

            list_of_convert_rows.append(new_row)

        df = pd.DataFrame(list_of_convert_rows)

        return df

    def create_close_tables(self, list_of_close_tables):

        list_of_convert_rows = []

        for index, row in list_of_close_tables.iterrows():

            row["Término"] = datetime.now().strftime("%d/%m/%Y")

            list_of_convert_rows.append(row)

        df = pd.DataFrame(list_of_convert_rows)

        df = df.drop(['CÓD  ', 'NOMENCLATURA FUNÇÃO', 'Unnamed: 2', ' CONVENIO', 'PRAZO ', '% PROMOTORA', 'prazo_formatado', '_merge'], axis=1, errors='ignore')

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = convertValues(row["% PROMOTORA"] * 100)

            row_close = row.copy()

            row_close["Término"] = datetime.now().strftime("%d/%m/%Y")

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

            operation = row["Operação"]
            grades = grade.get(operation, "")

            row_open["Término"] = ""
            row_open["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            row_open["ID"] = ''
            row_open["% Comissão"] = convertValues(row["% PROMOTORA"] * 100)
            row_open["% Mínima"] = percent * grades["min"]
            row_open["% Intermediária"] = percent * grades["med"]
            row_open["% Máxima"] = percent * grades["max"]

            list_of_convert_open_rows.append(row_open)

        df = pd.DataFrame(list_of_convert_close_rows)
        df2 = pd.DataFrame(list_of_convert_open_rows)

        colunas_remover = [
            'CÓD  ', 'NOMENCLATURA FUNÇÃO', 'Unnamed: 2',
            ' CONVENIO', 'PRAZO ', '% PROMOTORA',
            'prazo_formatado', '_merge'
        ]

        df = df.drop(colunas_remover, axis=1, errors='ignore')
        df2 = df2.drop(colunas_remover, axis=1, errors='ignore')

        return df, df2

    def input_standard_values(self, model):

        model["Instituição"] = "CAPITAL CONSIG"
        model["Parc. Refin."] = "0-0"
        model["% PMT Pagas"] = "0,00-0,00"
        model["% Taxa"] = "0,00-0,00"
        model["Idade"] = "0-80"
        model["-"] = "%"
        model["Base Comissão"] = "LÍQUIDO"
        model["% Fator"] = "0,000000000"
        model["% TAC"] = "0,000000"
        model["Val. Teto TAC"] = "0,000000"
        model["Faixa Val. Contrato"] = "0,00-100.000,00-LÍQUIDO"
        model["Faixa Val. Seguro"] = "0,00-0,00"
        model["Venda Digital"] = "SIM"
        model["Visualização Restrita"] = "NÃO"
        model["Val. Base Produção"] = "LÍQUIDO"
        model["REPASSE BONUS VIP"] = "0,00 | 0,00 | 0,00"

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

            print("Iniciando a conversão para o modelo Workbank...")
            if len(list_of_open_tables) > 0:
                print(f"Foram encontradas {len(list_of_open_tables)} tabelas para abrir.")
                df_open = self.create_open_tables(list_of_open_tables, model)
            if len(list_of_close_tables) > 0:
                print(f"Foram encontradas {len(list_of_close_tables)} tabelas para fechar.")
                df_close = self.create_close_tables(list_of_close_tables)
            if len(list_to_close_and_open) > 0:
                print(f"Foram encontradas {len(list_to_close_and_open)} tabelas para fechar e abrir.")
                df_close2, df_open2 = self.create_close_open_tables(list_to_close_and_open)

            print("Conversão realizada com sucesso!")
            print("Iniciando processo de junção dos arquivos...")
            dfs_para_juntar = [df for df in [df_close, df_close2, df_open, df_open2] if df is not None and not df.empty]
            if dfs_para_juntar:
                df_final = pd.concat(dfs_para_juntar, axis=0, ignore_index=True, sort=False)
                df_final = df_final.drop(['BONUS', 'NÍVEL', 'EMPREGADOR'], axis=1, errors='ignore')
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
