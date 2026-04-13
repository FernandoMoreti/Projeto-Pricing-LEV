from .Bank import Bank
from datetime import datetime
import pandas as pd
import io
from ..utils.utils import convertValues, remover_acentos
from ..config.bank.SantanderVariables import family_product, group_convenio, operation
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade
class SantanderMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file), sheet_name="Condições_comerciais")
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

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["codigo_regra"],
            right_on=["Id Tabela Banco"],
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

            if row["produto_regra"] == "Unificado" or row["produto_regra"] == "Ret Port":
                continue

            row["Diferido"] = row["percentual_comissao_diferido"]

            list_of_open_tables.append(row)

        df_matches["percent_converted"] = df_matches["percentual_comissao_a_vista"].apply(convertValues)
        df_matches["percent_work_converted"] = df_matches["% Comissão"].apply(convertValues)

        df_matches["Diferido"] = df_matches["percentual_comissao_diferido"]

        mask_diff = df_matches["percent_converted"] != df_matches["percent_work_converted"]
        df_diff = df_matches[mask_diff]

        list_to_close_and_open.extend(df_diff.to_dict('records'))

        df_matches.drop(columns=["percent_converted", "percent_work_converted"], inplace=True)

        return list_of_open_tables, list_of_close_tables, list_to_close_and_open

    def extract_city(self, product):
        product = str(product).upper().strip()

        product_limpo = remover_acentos(str(product).upper().strip())

        key_city = next((cidade for cidade in citys if cidade in product_limpo), None)

        cidade = citys.get(key_city) if key_city else None

        if cidade == None:
            if product == "PREFEITURA MUNICIPAL DE ITU":
                return "ITU"
            return "Sem convenio"

        return cidade

    def extract_uf_of_city(self, city):
        city = str(city).upper().strip()

        uf = " " + citys_uf.get(city, "")

        return uf

    def extract_uf_of_state(self, product):
        product = str(product).upper().strip()

        if product == "PROCURADORIA GERAL DO ESTADO DE SP":
            return "SP"

        if product == "PROCURADORIA GERAL DE JUSTICA DO ES":
            return "ES"

        product_limpo = remover_acentos(str(product).upper().strip())

        key_state = next((state for state in states if state in product_limpo), None)

        uf = states.get(key_state, "")

        if uf == "":
            key_city = next((city for city in citys if city in product_limpo), None)

            uf = citys_uf.get(key_city, "")

            if uf == "":
                return ""

        return uf

    def get_convenio(self, product):
        product = str(product).upper()
        categorias = {
            "CGI - IMOB": ["CGI", "USECASA"],
            "": ["CREMESP"],
            "AERONAUTIICA": ["AERONAUTICA"],
            "FEDERAL SIAPE": ["SIAPE"],
            "TJ | ": ["TRIB"],
            "GOV-": ["ASSEMB", "ESTADO", "AMAPA" "PROCURADORIA", "IPSEMG", "JUSTICA", "UNIVERSITARIO", "CORPO", "DEFENSORIA", "UNIVERSIDADE", "GOVERNO", "MINISTERIO", "POLICIA", "SANESUL"],
            "PREF. ": ["PREF", "PREV", "MUNICIP", "MUNIC", "AUTARQUIA", "INST", "ARAPREV", "ASPMI", "CARAGUAPREV", "COMPANHIA", "DEPART", "FUND", "IPASLUZ", "IPREM", "SECRETARIA", "SAAE", "SAEMAS", "SAMAE", "SAME", "SANEAMENTO", "SANEBAVI", "SEPREM", "SERV", "SUPERINTENDENCIA", "UNITAU", "FIEB"],
        }

        for categoria, prefixos in categorias.items():

            if product in ["SAO PAULO PREVIDENCIA", "CAMARA DOS DEPUTADOS", "FUND PRO SANGUE HEMOCENTRO SAO PAULO"]:
                convenio = "GOV-"
                prefixo_encontrado = True
            else:
                prefixo_encontrado = next((p for p in prefixos if p in product), None)
            if prefixo_encontrado:
                convenio = categoria

                if convenio in ["FEDERAL SIAPE", "AERONAUTIICA", "CGI - IMOB", ""]:
                    return convenio

                if convenio == "PREF. ":
                    city = self.extract_city(product)

                    if city == "":
                        return ""

                    uf = self.extract_uf_of_city(city)

                    convenio = convenio + city + uf
                    return convenio

                if convenio in ["GOV-", "TJ | "]:
                    uf = self.extract_uf_of_state(product)

                    if uf == "":
                        return ""

                    convenio = convenio + uf
                    return convenio

        return "CONVENIO DESCONHECIDO"

    def get_seguro(self, text):
        text = str(text).upper()
        if any(term in text for term in ["C SEGURO", "COM SEGURO", "C SEG"]):
            return " - C/ SEGURO - "
        if any(term in text for term in ["S SEGURO", "SEM SEGURO", "S SEG"]):
            return " - S/ SEGURO - "
        return " - S/ SEGURO - "

    def get_operation(self, value):
        return operation.get(value, "")

    def create_open_tables(self, list_of_open_tables, model):

        list_of_convert_rows = []

        for row in list_of_open_tables:

            product = row["nome_convenio"]
            operation = self.get_operation(row["produto_regra"])
            convenio = self.get_convenio(product)

            agreement = convenio.strip().split(" ")[0]
            family = family_product.get(agreement, "")
            group = group_convenio.get(family, "")
            percent = convertValues(row["percentual_comissao_a_vista"])
            seguro = self.get_seguro(row["descricao_regra"])

            codigo_str = str(row["codigo_regra"]).strip()
            complement = f"{codigo_str[4:]}{seguro}{row['codigo_regra']}"

            grades = grade.get(operation, "")

            new_row = model.copy()

            if seguro == " - C/ SEGURO - ":
                new_row["SEGURO"] = "0,56 | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                new_row["REPASSE SEGURO"] = "0,40 | 0,50 | 0,56"

            if operation == "PORTABILIDADE":
                new_row["Base Comissão"] = "BRUTO"
            else:
                new_row["Base Comissão"] = "LIQUÍDO"

            new_row["Produto"] = f"{product} - {int(row['codigo_regra'])}"
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Convênio"] = convenio
            new_row["Operação"] = operation
            new_row["Parc. Atual"] = row["faixa_parcela"]
            new_row["% Mínima"] = percent * grades["min"]
            new_row["% Intermediária"] = percent * grades["med"]
            new_row["% Máxima"] = percent * grades["max"]
            new_row["% Comissão"] = percent
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Complemento"] = complement
            new_row["Id Tabela Banco"] = row["codigo_regra"]
            new_row["DIFERIMENTO"] = f"{int(row['Diferido'])},00 | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"

            list_of_convert_rows.append(new_row)

        df = pd.DataFrame(list_of_convert_rows)

        return df

    def create_close_tables(self, list_of_close_tables):

        list_of_convert_rows = []

        for index, row in list_of_close_tables.iterrows():

            row["Término"] = datetime.now().strftime("%d/%m/%Y")

            list_of_convert_rows.append(row)

        df = pd.DataFrame(list_of_convert_rows)

        df = df.drop(["codigo_convenio", "nome_convenio", "rede", "regional", "status_convenio", "codigo_regra", "descricao_regra", "data_inicio_validade", "data_fim_validade", "tipo_conta_corrente", "sequencia_faixa", "range_faixa_taxa", "faixa_parcela", "taxa_juros_sem_seguro", "taxa_juros_com_seguro", "categoria_corban_para_comissao", "percentual_comissao_a_vista", "percentual_comissao_diferido", "percentual_comissao_total", "produto_regra", "canal_regra", '_merge'], axis=1)

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = convertValues(row["percentual_comissao_a_vista"])

            row_close = row.copy()

            row_close["Término"] = datetime.now().strftime("%d/%m/%Y")

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

            operation = self.get_operation(row["produto_regra"])
            grades = grade.get(operation, "")

            row_open["Término"] = ""
            row_open["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            row_open["ID"] = ''
            row_open["% Comissão"] = convertValues(row["percentual_comissao_a_vista"])
            row_open["% Mínima"] = percent * grades["min"]
            row_open["% Intermediária"] = percent * grades["med"]
            row_open["% Máxima"] = percent * grades["max"]

            list_of_convert_open_rows.append(row_open)

        df = pd.DataFrame(list_of_convert_close_rows)
        df2 = pd.DataFrame(list_of_convert_open_rows)

        colunas_remover = ["codigo_convenio", "nome_convenio", "rede", "regional", "status_convenio", "codigo_regra", "descricao_regra", "data_inicio_validade", "data_fim_validade", "tipo_conta_corrente", "sequencia_faixa", "range_faixa_taxa", "faixa_parcela", "taxa_juros_sem_seguro", "taxa_juros_com_seguro", "categoria_corban_para_comissao", "percentual_comissao_a_vista", "percentual_comissao_diferido", "percentual_comissao_total", "produto_regra", "canal_regra", '_merge', 'percent_converted', 'percent_work_converted', 'Diferido']

        df = df.drop(colunas_remover, axis=1)
        df2 = df2.drop(colunas_remover, axis=1)

        return df, df2

    def input_standard_values(self, model):

        model["Instituição"] = "SANTANDER"
        model["Parc. Refin."] = "0-0"
        model["% PMT Pagas"] = "0,00-0,00"
        model["% Taxa"] = "0,00-0,00"
        model["Idade"] = "0-80"
        model["-"] = "%"
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
                print(f"Sucesso! Total de linhas: {len(df_final)}")
            else:
                print("Nenhum dado encontrado para juntar.")
                df_final = pd.DataFrame()
            print("Processo de junção finalizado!")

            print("Exportando resultado para Excel...")
            df_final.to_excel("Santander_Atualizacoes.xlsx", index=False)
            print("Resultado exportado com sucesso!")

            print("Processo concluído!")

        except Exception as e:
            print(f"Erro durante o processamento: {str(e)}")
            return "error"
