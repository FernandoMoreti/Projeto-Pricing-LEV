from .Bank import Bank
from datetime import datetime
import pandas as pd
import io
from ..utils.utils import convertValues
from ..config.bank.CapitalConsigVariables import family_product, group_convenio
from ..config.citys_uf import citys

class CapitalConsigMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file))
        return df

    def compare_archive(self, df_work, df_bank):

        df_bank["prazo_formatado"] = df_bank["PRAZO "].astype(str) + "-" + df_bank["PRAZO "].astype(str)

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["NOMENCLATURA FUNÇÃO", "prazo_formatado"],
            right_on=["Produto", "Parc. Atual"],
            how="outer",
            indicator=True
        )

        list_of_open_tables = df_result[df_result["_merge"] == "left_only"]
        list_of_close_tables = df_result[df_result["_merge"] == "right_only"]
        list_to_close_and_open = []

        df_matches = df_result[df_result["_merge"] == "both"]

        if not df_matches.empty:
            print(f"Encontrados {len(df_matches)} correspondências!")

        for index, row in df_matches.iterrows():
            percent = convertValues(row["% PROMOTORA"] * 100)
            percent_work = convertValues(row["% Comissão"])
            if percent != percent_work:
                list_to_close_and_open.append(row)

        return list_of_open_tables, list_of_close_tables, list_to_close_and_open

    def extract_city(self, rest_of_product):
        rest_of_product = str(rest_of_product).upper().strip()

        cidade = rest_of_product.split("_")[0]

        if "PREV " in cidade:
            cidade = cidade.split(" ")[-1]

        print(cidade)

    def extract_of_uf(self, rest_of_product, convenio):
        rest_of_product = str(rest_of_product).upper().strip()

        cidade = rest_of_product.split("_")[0]

        print(rest_of_product)
        print(cidade)



        # mapeamento_especifico = {
        #     "SPPREV": "SP", "MACAÉ": "RJ", "MACAE": "RJ", "CONTAGEM": "MG",
        #     "PREVICON": "MG", "FUNEC": "MG", "TRANSCON": "MG", "ARAGUAÍNA": "TO",
        #     "ARAGUAINA": "TO", "BAURU": "SP", "RECIFE": "PE", "ÁGUAS LINDAS": "GO",
        #     "AGUAS LINDAS": "GO", "ANANINDEUA": "PA", "BH": "MG", "ALAGOINHAS": "BA",
        #     "CAMPINA_GRANDE": "PB", "CAMPO GRANDE": "MS", "SOROCABA": "SP",
        #     "SOBRAL": "CE", "SAO_LUIS": "MA", "SAO LUIS": "MA", "PICOS": "PI",
        #     "PREV PALMAS": "TO", "PALMAS": "TO", "ESP_SANTO": "ES",
        #     "JUAZEIRO": "CE", "TAUBATÉ": "SP", "TAUBATE": "SP", "DQ DE CAXIAS": "RJ",
        #     "IPMDC": "RJ", "IMPERATRIZ": "MA", "PLANALTINA": "GO", "PORTO_VELHO": "RO",
        #     "SANTA_RITA": "PB", "TERESINA": "PI", "CAMPINAS": "SP", "PARAIBA": "PB",
        #     "PBPREV": "PB", "UEPB": "PB", "MARANHAO": "MA", "NATAL": "RN",
        #     "SANTOS": "SP", "ALAGOAS": "AL", "PIAUI": "PI", "PARANA": "PR",
        #     "GUARULHOS": "SP", "RIBEIRAO PRETO": "SP", "S J RIO PRETO": "SP",
        #     "IPAM": "RO", "PE": "PE"
        # }

        # for cidade_ou_orgao, uf in mapeamento_especifico.items():
        #     if rest_of_product.startswith(cidade_ou_orgao):

        #         if convenio == "PREF. ":
        #             return f"{convenio} {cidade_ou_orgao.replace('_', ' ')} {uf}"

        #         return f"{convenio}{uf}"

        # prefixo = rest_of_product[:3]
        # if len(prefixo) >= 3 and prefixo[2] == "_":
        #     possivel_uf = prefixo[:2]
        #     ufs_validas = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", 
        #                 "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", 
        #                 "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

        #     if possivel_uf in ufs_validas:
        #         return f"{convenio}{possivel_uf}"

        # return convenio

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
                return convenio

                # if convenio == "FEDERAL SIAPE":
                #     return convenio

                # city = self.extract_city(rest_of_product)

        return "CONVENIO DESCONHECIDO"

    def convert_to_work_model(self, list_of_open_tables, list_of_close_tables, list_to_close_and_open, model):

        list_of_convert_rows = []

        print(list_of_open_tables)

        for index, row in list_of_open_tables.iterrows():

            product = row["NOMENCLATURA FUNÇÃO"]

            convenio = self.get_convenio(product)

            agreement = row[" CONVENIO"].strip().split(" ")[0]
            family = family_product[agreement]
            group = group_convenio[family]
            percent = convertValues(row["% PROMOTORA"])

            new_row = model.copy()

            if "_EMP_" in product:
                new_row["Operação"] = "NOVO"
            else:
                new_row["Operação"] = "CARTÃO"

            new_row["Produto"] = product
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Convênio"] = convenio
            new_row["Parc. Atual"] = row["prazo_formatado"]
            new_row["% Mínima"] = percent * 0.70
            new_row["% Intermediária"] = percent * 0.95
            new_row["% Máxima"] = percent
            new_row["% Comissão"] = percent

            list_of_convert_rows.append(new_row)

        df = pd.DataFrame(list_of_convert_rows)

        df.to_excel("debug.xlsx", index=False)

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


    def set_closing_date():
        pass

    def run(self, df_work, file_Bank):

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

        print("Iniciando a conversão para o modelo Workbank...")
        list_of_convert_rows = self.convert_to_work_model(list_of_open_tables, list_of_close_tables, list_to_close_and_open, model)
