from .Bank import Bank
from datetime import datetime
import pandas as pd
import io
from ..utils.utils import convertValues, formatar_br, remover_acentos
from ..config.bank.SafraVariable import family_product, group_convenio, prazo_convenio
from ..config.citys_uf import citys, citys_uf, states

class SafraMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file)) # header=3
        return df

    def compare_archive(self, df_work, df_bank):

        filtro_legenda = df_bank["Atualizações"].str.contains("Legenda", na=False, case=False)

        if filtro_legenda.any():
            indice_corte = df_bank[filtro_legenda].index[0] - 1
            df_bank = df_bank.iloc[:indice_corte].copy()

        df_bank["PrazoDe"] = pd.to_numeric(df_bank["PrazoDe"], errors='coerce').fillna(0).astype(int)
        df_bank["PrazoAte"] = pd.to_numeric(df_bank["PrazoAte"], errors='coerce').fillna(0).astype(int)

        df_bank.loc[df_bank["Produto"] == "PORTABILIDADE", "PrazoDe"] = 1

        df_bank.loc[df_bank["Produto"] == "PORTABILIDADE", "PrazoAte"] = (
            df_bank["Convenio"].str.strip().map(prazo_convenio).fillna(0).astype(int)
        )

        df_bank["prazo_formatado"] = (
            df_bank["PrazoDe"].astype(str) + "-" + df_bank["PrazoAte"].astype(str)
        )
        df_work["Parc. Atual"] = df_work["Parc. Atual"].astype(str).str.strip()

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["Id Tabela Nova", "prazo_formatado"],
            right_on=["Id Tabela Banco", "Parc. Atual"],
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

            row["Diferido"] = row["CdvpDiferidoFuturo"]

            list_of_open_tables.append(row)

        for index, row in df_matches.iterrows():

            row["Diferido"] = row["CdvpDiferidoFuturo"]

            percent = convertValues(row["ComissaoAto"] * 100)
            percent_work = convertValues(row["% Comissão"])
            if percent != percent_work:
                list_to_close_and_open.append(row)

        return list_of_open_tables, list_of_close_tables, list_to_close_and_open

    def extract_city(self, product):
        product = str(product).upper().strip()

        if product.split(" ")[0] in ["IPREM"]:
            return citys.get(product.split(" ")[0], "")

        cidade = product.split(" ")[1]

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
            "GOV-": ["GOV", "GOV_", "GOV.", "SPPREV_"],
            "FEDERAL SIAPE": ["SIAPE"],
            "PREF. ": ["PREF", "PREF_", "PREF.", "IPREM"],
        }

        if product in ["AERONAUTICA", "MARINHA", "FGTS", "INSS"]:
            return product

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

                if convenio == "GOV-":
                    uf = product.split(" ")[1]
                    convenio = convenio + uf
                    return convenio

        return "CONVENIO DESCONHECIDO"

    def create_open_tables(self, list_of_open_tables, model):

        list_of_convert_rows = []

        for row in list_of_open_tables:

            product = row["Convenio"]

            if row["Produto_x"] == "PORTABILIDADE":
                row["Tabela"] = row["Convenio"] + " " + row["Tabela"]

            convenio = self.get_convenio(product)

            agreement = row["Convenio"].strip().split(" ")[0]
            family = family_product[agreement]
            group = group_convenio[family]
            percent = convertValues(row["ComissaoAto"] * 100)
            tkt_min = formatar_br(row["TktmMin"])
            tkt_max = formatar_br(row["TktmMax"])
            diferido = formatar_br(row['Diferido'] * 100 if row['Diferido'] != None else '0,00')

            new_row = model.copy()

            new_row["Operação"] = row["Produto_x"]
            new_row["Produto"] = row["Tabela"]
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Convênio"] = convenio
            new_row["Parc. Atual"] = row["prazo_formatado"]
            new_row["% Mínima"] = percent * 0.70
            new_row["% Intermediária"] = percent * 0.95
            new_row["% Máxima"] = percent
            new_row["% Comissão"] = percent
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Complemento"] = int(row["Id Tabela Nova"])
            new_row["Id Tabela Banco"] = int(row["Id Tabela Nova"])
            new_row["DIFERIMENTO"] = f"{diferido} | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
            new_row["Faixa Val. Contrato"] = f"{tkt_min}-{tkt_max}-LÍQUIDO"

            if new_row["DIFERIMENTO"] != "":
                new_row["REPASSE DIFERIMENTO"] = "0,00 | 0,00 | 0,00"

            list_of_convert_rows.append(new_row)

        df = pd.DataFrame(list_of_convert_rows)

        return df

    def create_close_tables(self, list_of_close_tables):

        list_of_convert_rows = []

        for index, row in list_of_close_tables.iterrows():

            row["Término"] = datetime.now().strftime("%d/%m/%Y")

            list_of_convert_rows.append(row)

        df = pd.DataFrame(list_of_convert_rows)

        df = df.drop(['Atualizações', 'Convenio', 'Tabela', 'Produto_x', 'DataInicioVigencia', 'PrazoDe', 'PrazoAte', 'TktmMin', 'TktmMax', 'Taxa', 'TaxaMaxima', 'CalculoComissao', 'Id Tabela Nova', 'IdConvenio', 'ComissaoAto', 'CdvpDiferidoVp', 'CdvpDiferidoMensal', 'CdvpDiferidoFuturo', 'CintDiferidoVp', 'CintDiferidoMensal', 'CintDiferidoFuturo', 'CprodDiferidoVp', 'CprodDiferidoMensal', 'CprodDiferidoFuturo', 'CmutDiferidoVp', 'CmutDiferidoMensal', 'CmutDiferidoFuturo', 'TotalDiferidoVp', 'TotalDiferidoMensal', 'TotalDiferidoFuturo', 'prazo_formatado', '_merge'], axis=1)

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

            row_open["Término"] = ""
            row_open["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            row_open["ID"] = ''
            row_open["% Comissão"] = convertValues(row["ComissaoAto"] * 100)
            row_open["% Mínima"] = percent * 0.70
            row_open["% Intermediária"] = percent * 0.95
            row_open["% Máxima"] = percent

            list_of_convert_open_rows.append(row_open)

        df = pd.DataFrame(list_of_convert_close_rows)
        df2 = pd.DataFrame(list_of_convert_open_rows)

        colunas_remover = ['Atualizações', 'Convenio', 'Tabela', 'Produto_x', 'DataInicioVigencia', 'PrazoDe', 'PrazoAte', 'TktmMin', 'TktmMax', 'Taxa', 'TaxaMaxima', 'CalculoComissao', 'Id Tabela Nova', 'IdConvenio', 'ComissaoAto', 'CdvpDiferidoVp', 'CdvpDiferidoMensal', 'CdvpDiferidoFuturo', 'CintDiferidoVp', 'CintDiferidoMensal', 'CintDiferidoFuturo', 'CprodDiferidoVp', 'CprodDiferidoMensal', 'CprodDiferidoFuturo', 'CmutDiferidoVp', 'CmutDiferidoMensal', 'CmutDiferidoFuturo', 'TotalDiferidoVp', 'TotalDiferidoMensal', 'TotalDiferidoFuturo', 'prazo_formatado', '_merge', 'Diferido']

        df = df.drop(colunas_remover, axis=1)
        df2 = df2.drop(colunas_remover, axis=1)

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

            print("""
    =======================================================
    Tabelas alteradas
    =======================================================
            """)
            if len(list_of_open_tables) > 0:
                print(f"Foram encontradas {len(list_of_open_tables)} tabelas para abrir.")
                df_open = self.create_open_tables(list_of_open_tables, model)
            if len(list_of_close_tables) > 0:
                print(f"Foram encontradas {len(list_of_close_tables)} tabelas para fechar.")
                df_close = self.create_close_tables(list_of_close_tables)
            if len(list_to_close_and_open) > 0:
                print(f"Foram encontradas {len(list_to_close_and_open)} tabelas para fechar e abrir.")
                df_close2, df_open2 = self.create_close_open_tables(list_to_close_and_open)

            print("""
    =======================================================
    Conversão realizada com sucesso!
    =======================================================
            """)

            print("Iniciando processo de junção dos arquivos...")
            dfs_para_juntar = [df for df in [df_close, df_close2, df_open, df_open2] if df is not None and not df.empty]
            if dfs_para_juntar:
                df_final = pd.concat(dfs_para_juntar, axis=0, ignore_index=True, sort=False)
                print(f"Sucesso! Total de linhas: {len(df_final)}")
            else:
                print("Nenhum dado encontrado para juntar.")
                df_final = pd.DataFrame()
            print("Processo de junção finalizado!")

            print("Exportando resultado para Excel...")
            df_final.to_excel("capital_consig_resultado.xlsx", index=False)
            print("Resultado exportado com sucesso!")

            print("Processo concluído!")

        except Exception as e:
            print(f"Erro durante o processamento: {str(e)}")
            return "error"