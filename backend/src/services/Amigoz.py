from .Bank import Bank
from datetime import datetime, timedelta
import pandas as pd
import io
from ..utils.utils import convertValues, formatar_br, remover_acentos, limpar_zeros, rename_duplicates
from ..config.bank.PanVariables import family_product, group_convenio, operation
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade

class AmigozMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file), header=3)
        return df

    def compare_archive(self, df_work, df_bank):

        novas_linhas = []

        for index, row in df_bank.iterrows():
            if row["Produto"] == "Cartão Consignado" or row["Produto"] == "Cartão Benefício":
                row["Convênio"] = (row["Convênio"] + ' - ' + row["Produto"]).upper()
                row["Prazo"] = str(row["Prazo"]) + '-' + str(row["Prazo"])
                taxa_formatada = f"{row['Taxa %']:.2f}".replace('.', ',')
                row["Taxa %"] = str(row["ID"]).strip() + ' | TX ' + taxa_formatada + '%'

                row_cartao = row.copy()
                row_cartao["Produto"] = "CARTÃO"
                row_cartao["% Comissao"] = row["Saque%"] * 100
                row_saque = row.copy()
                row_saque["Produto"] = "SAQUE COMPL."
                row_saque["% Comissao"] = row["Saque complementar %"] * 100
                row_cartao_seguro = row.copy()
                row_cartao_seguro["Produto"] = "CARTÃO"
                row_cartao_seguro["% Comissao"] = row["Saque complementar %"] * 100
                row_cartao_seguro["Taxa %"] = row_cartao_seguro["Taxa %"] + ' - COM SEGURO'
                row_saque_seguro = row.copy()
                row_saque_seguro["Produto"] = "SAQUE COMPL."
                row_saque_seguro["% Comissao"] = row["Saque complementar %"] * 100
                row_saque_seguro["Taxa %"] = row_saque_seguro["Taxa %"] + ' - COM SEGURO'

                if row["Apenas cartão"] != 0:
                    row["Produto"] = "CARTÃO"
                    row["Convênio"] = row["Convênio"] + ' - PLASTICO'
                    row["% Comissao"] = 0
                    row_plastico = row.copy()
                    novas_linhas.append(row_plastico)

                novas_linhas.append(row_cartao)
                novas_linhas.append(row_cartao_seguro)
                novas_linhas.append(row_saque)
                novas_linhas.append(row_saque_seguro)

        if novas_linhas:
            df_bank = pd.DataFrame(novas_linhas)

        df_work["Produto"] = df_work["Produto"].str.strip()

        df_bank = df_bank[df_bank["Status"] != "Bloqueado"]

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["Convênio", "Produto", "Prazo", "Taxa %"],
            right_on=["Produto", "Operação", "Parc. Atual", "Complemento"],
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

        # Validar matches
        for index, row in df_matches.iterrows():

            percent = convertValues(row["% Comissao"])
            percent_work = convertValues(row["% Comissao"])

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

        for nome_cidade in sorted(states.keys(), key=len, reverse=True):
            if nome_cidade in product:
                uf = states[nome_cidade]
                break
            else:
                uf = ""

        return uf

    def get_convenio(self, product):

        categorias = {
            "GOV-": ["GOVERNO", "POLÍCIA", "AMAZONPREV", "AMAZONPREV-AM", "IPER", "SPPREV"],
            "FEDERAL SIAPE": ["SIAPE", "SIA"],
            "PREF. ": ["PREF", "PREFEITURA", "MARINGAPREV", "MANAUSPREV", "JFPREV", "ISSA", "IPVV", "IPSEM", "IPSA", "IPREM", "IPMO", "IPMC", "CAXIASPREV", "CAAPSML", "PREVISO"],
            "TJ | ": ["TRIBUNAL", "TJ", "TJ."],
        }

        if "FGTS" in product:
            return "FGTS"

        if "INSS" in product:
            return "INSS"

        if "CONSIG PRIVADO" in product:
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

            product = row["Convênio_x"]
            convenio = self.get_convenio(product)

            if "-" in convenio:
                agreement = convenio.split("-")[0].strip()
            else:
                agreement = convenio.split()[0].strip()

            family = family_product[agreement]
            group = group_convenio[family]

            percent = convertValues(row["% Comissao"])

            operation = row["Produto_x"]

            grades = grade.get(operation, "")

            new_row = model.copy()

            new_row["Operação"] = operation
            new_row["Produto"] = row["Convênio_x"]
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Convênio"] = convenio
            new_row["Parc. Atual"] = row["Prazo"]
            new_row["% Mínima"] = percent * grades["min"]
            new_row["% Intermediária"] = percent * grades["med"]
            new_row["% Máxima"] = percent * grades["max"]
            new_row["% Comissão"] = percent
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Complemento"] = row["Taxa %"]

            if "COM SEGURO" in row["Taxa %"]:
                new_row["SEGURO DIAMANTE"] = "3,00 | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                new_row["REPASSE SEGURO DIAMANTE"] = "2,40 | 2,70 | 2,85"
                new_row["SEGURO SUPER DIAMANTE"] = "4,50 | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                new_row["REPASSE SEGURO SUPER DIAMANTE"] = "3,60 | 4,05 | 4,25"
                new_row["Faixa Val. Seguro"] = "2,00-5.000,00"
            else:
                new_row["Faixa Val. Seguro"] = "0,00-1,00"

            if "PLASTICO" not in convenio:
                new_row["BONUS EXTRA"] = "2,00 | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                new_row["REPASSE BONUS EXTRA"] = "0,00 | 0,00 | 0,00"
                new_row["-"] = "%"
            else:
                new_row["PRÉ-ADESÃO"] = f"{str(row[' Apenas cartão '])} | FIXO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                if row[' Apenas cartão '] == 0:
                    new_row["REPASSE PRÉ-ADESÃO"] = "0,00 | 0,00 | 0,00"
                elif row[' Apenas cartão '] == 50:
                    new_row["REPASSE PRÉ-ADESÃO"] = "35,00 | 40,00 | 45,00"
                elif row[' Apenas cartão '] == 70:
                    new_row["REPASSE PRÉ-ADESÃO"] = "52,50 | 59,50 | 66,50"
                elif row[' Apenas cartão '] == 100:
                    new_row["REPASSE PRÉ-ADESÃO"] = "70,00 | 80,00 | 90,00"
                elif row[' Apenas cartão '] == 150:
                    new_row["REPASSE PRÉ-ADESÃO"] = "105,00 | 120,00 | 135,00"
                elif row[' Apenas cartão '] == 200:
                    new_row["REPASSE PRÉ-ADESÃO"] = "140,00 | 160,00 | 180,00"
                new_row["-"] = "$"

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

        df = df.drop(['ID_x', 'Convênio_x', 'Produto_x',
       'Taxa %', 'Prazo', 'Saque%', 'Cartão no saque R$',
       'Apenas cartão', 'Saque complementar %', 'REFIN %', 'Seguro Diamante', 'Seguro Super Diamante',
       'Fator Multiplicador', 'Data Atualização', 'Status', 'Taxa Especial', '% Comissao'], axis=1)

        df.columns = df.columns.str.replace('_y', '')

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = convertValues(row["% Comissao"])

            row_close = row.copy()

            row_close["Término"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            row_close["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

            operation = row["Operação"]

            grades = grade.get(operation, "")

            row_open["Término"] = ''
            row_open["Vigência_y"] = datetime.now().strftime("%d/%m/%Y")
            row_open["ID_y"] = ''
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
            'ID_x', 'Convênio_x', 'Produto_x',
            'Taxa %', 'Prazo', 'Saque%', 'Cartão no saque R$',
            'Apenas cartão', 'Saque complementar %', 'REFIN %', 'Seguro Diamante', 'Seguro Super Diamante',
            'Fator Multiplicador', 'Data Atualização', 'Status', 'Taxa Especial', '% Comissao', '_merge', "Vigência"
        ]


        df = df.drop(colunas_para_dropar, axis=1, errors='ignore')
        df2 = df2.drop(colunas_para_dropar, axis=1, errors='ignore')

        df.columns = df.columns.str.replace('_y', '')
        df2.columns = df2.columns.str.replace('_y', '')

        return df, df2

    def input_standard_values(self, model):

        model["Instituição"] = "AMIGOZ"
        model["Parc. Refin."] = "0-0"
        model["% PMT Pagas"] = "0,00-0,00"
        model["% Taxa"] = "0,00-0,00"
        model["Idade"] = "0-80"
        model["% Fator"] = "0,000000000"
        model["% TAC"] = "0,000000"
        model["Val. Teto TAC"] = "0,000000"
        model["Faixa Val. Contrato"] = "0,00-100.000,00-LÍQUIDO"
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