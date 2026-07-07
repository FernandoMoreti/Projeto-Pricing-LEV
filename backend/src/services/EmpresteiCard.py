from .Bank import Bank
from datetime import datetime, timedelta
import pandas as pd
import io
from ..utils.utils import convertValues, formatar_br, remover_acentos, limpar_zeros, rename_duplicates
from ..config.bank.EmpresteiCardVariables import family_product, group_convenio, operation
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade

class EmpresteiCardMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file), header=1)
        return df

    def create_row(self, taxa, percent, prazo, row):
        row1 = row.copy()

        row1["Prazo"] = prazo
        row1["Percent"] = row[percent]

        valor_taxa = str(row[taxa])

        if " - " in valor_taxa:
            parte = valor_taxa.split(" - ")[0]
            taxa_formatada = float(f"{parte}".replace(",", "."))

            row1["Taxa"] = f"{taxa_formatada:.2f}-{taxa_formatada:.2f}".replace(".", ",")
            row1["Revision"] = ""
        else:
            valor_float = float(valor_taxa)
            taxa_formatada = f"{valor_float:.2f}".replace(".", ",")

            row1["Taxa"] = f"{taxa_formatada}-{taxa_formatada}"
            row1["Revision"] = "False"

        return row1

    def compare_archive(self, df_work, df_bank):

        novas_linhas = []

        df_bank = df_bank[pd.notna(df_bank["CONVÊNIOS "])]

        for index, row in df_bank.iterrows():

            if "Suspenso" in str(row["CONVÊNIOS "]):
                continue

            if row["CONVÊNIOS "] == "CANOAS PREV - RS":
                row["CONVÊNIOS "] = "CANOAS PREV. - CARTAO"
            elif row["CONVÊNIOS "] == "GOIAS (GOV.)":
                row["CONVÊNIOS "] = "GOV. GO - CARTAO"
            elif row["CONVÊNIOS "] == "MARANHÃO (GOV.) - MA":
                row["CONVÊNIOS "] = "GOV. MA - CARTAO"
            else:
                row["CONVÊNIOS "] = "PREF. " + remover_acentos(row["CONVÊNIOS "].split("-")[0]) + " - CARTAO"

            if pd.notna(row["Qtd de Parcelas "]):
                row = self.create_row("Taxa Operação", "Qtd de Parcelas ", "96-96", row)
                novas_linhas.append(row)
            if pd.notna(row["Unnamed: 3"]):
                row = self.create_row("Taxa Operação", "Unnamed: 3", "84-95", row)
                novas_linhas.append(row)
            if pd.notna(row["Unnamed: 4"]):
                row = self.create_row("Taxa Operação", "Unnamed: 4", "72-83", row)
                novas_linhas.append(row)
            if pd.notna(row["Unnamed: 5"]):
                row = self.create_row("Taxa Operação", "Unnamed: 5", "60-71", row)
                novas_linhas.append(row)
            if pd.notna(row["Unnamed: 6"]):
                row = self.create_row("Taxa Operação", "Unnamed: 6", "48-59", row)
                novas_linhas.append(row)
            if pd.notna(row["Unnamed: 7"]):
                row = self.create_row("Taxa Operação", "Unnamed: 7", "36-47", row)
                novas_linhas.append(row)
            if pd.notna(row["Qtd Parcelas "]):
                row = self.create_row("Taxa Operação.1", "Qtd Parcelas ", "96-96", row)
                novas_linhas.append(row)
            if pd.notna(row["Unnamed: 10"]):
                row = self.create_row("Taxa Operação.1", "Unnamed: 10", "60-95", row)
                novas_linhas.append(row)
            if pd.notna(row["Unnamed: 11"]):
                row = self.create_row("Taxa Operação.1", "Unnamed: 11", "48-59", row)
                novas_linhas.append(row)
            if pd.notna(row["Unnamed: 12"]):
                row = self.create_row("Taxa Operação.1", "Unnamed: 12", "36-47", row)
                novas_linhas.append(row)
            if pd.notna(row["Qtd Parcelas .1"]):
                row = self.create_row("Taxa Operação.2", "Qtd Parcelas .1", "6-6", row)
                novas_linhas.append(row)

        if novas_linhas:
            df_bank = pd.DataFrame(novas_linhas)

        df_bank = df_bank[~df_bank["CONVÊNIOS "].str.contains("Suspenso", case=False, na=False)]

        df_work["Produto"] = df_work["Produto"].str.strip()

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["CONVÊNIOS ", "Prazo", "Taxa"],
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
            print(f"Encontrados {len(df_open)} open!")
            print(f"Encontrados {len(df_close)} close!")

        list_of_open_tables = df_open.to_dict(orient="records")
        list_of_close_tables = df_close.to_dict(orient="records")

        # Validar matches
        for index, row in df_matches.iterrows():

            percent = convertValues(row["Percent"])
            percent_work = convertValues(row["% Comissão"])

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
            "GOV-": ["GOVERNO", "GOV", "POLÍCIA", "POLICIA", "BOMBEIROS", "DEFENSORIA", "AMAZONPREV", "AMAZONPREV-AM", "IPER", "SPPREV", "IPSM"],
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

            product = row["CONVÊNIOS "]
            convenio = self.get_convenio(product)

            if "-" in convenio:
                agreement = convenio.split("-")[0].strip()
            else:
                agreement = convenio.split()[0].strip()

            family = family_product[agreement]
            group = group_convenio[family]

            percent = convertValues(row["Percent"])
            valor_str = row["Taxa"].split("-")[0]

            valor_float = float(valor_str.replace(',', '.'))

            operation = "CARTÃO"

            grades = grade.get(operation, "")

            new_row = model.copy()

            new_row["Operação"] = operation
            new_row["Produto"] = row["CONVÊNIOS "]
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Convênio"] = convenio
            new_row["Parc. Atual"] = row["Prazo"]
            new_row["% Mínima"] = percent * grades["min"]
            new_row["% Intermediária"] = percent * grades["med"]
            new_row["% Máxima"] = percent * grades["max"]
            new_row["% Comissão"] = percent
            new_row["% Taxa"] = row["Taxa"]
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Complemento"] = f"TX {valor_float:.2f}%".replace('.', ',')
            new_row["Revision"] = row["Revision"]
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
            row["Revision"] = "False"

            list_of_convert_rows.append(row)

        df = pd.DataFrame(list_of_convert_rows)

        df = df.drop(['CONVÊNIOS ', 'Taxa Operação', 'Qtd de Parcelas ', 'Unnamed: 3',
            'Unnamed: 4', 'Unnamed: 5', 'Unnamed: 6', 'Unnamed: 7',
            'Taxa Operação.1', 'Qtd Parcelas ', 'Unnamed: 10', 'Unnamed: 11',
            'Unnamed: 12', 'Taxa Operação.2', 'Qtd Parcelas .1', 'SITUAÇÃO',
            'Prazo', 'Percent', 'Taxa', '_merge'], axis=1)

        df.columns = df.columns.str.replace('_y', '')

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = convertValues(row["Percent"])

            row_close = row.copy()

            row_close["Término"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            row_close["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

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
            'CONVÊNIOS ', 'Taxa Operação', 'Qtd de Parcelas ', 'Unnamed: 3',
            'Unnamed: 4', 'Unnamed: 5', 'Unnamed: 6', 'Unnamed: 7',
            'Taxa Operação.1', 'Qtd Parcelas ', 'Unnamed: 10', 'Unnamed: 11',
            'Unnamed: 12', 'Taxa Operação.2', 'Qtd Parcelas .1', 'SITUAÇÃO',
            'Prazo', 'Percent', 'Taxa', '_merge'
        ]


        df = df.drop(colunas_para_dropar, axis=1, errors='ignore')
        df2 = df2.drop(colunas_para_dropar, axis=1, errors='ignore')

        df.columns = df.columns.str.replace('_y', '')
        df2.columns = df2.columns.str.replace('_y', '')

        return df, df2

    def input_standard_values(self, model):

        model["Instituição"] = "EMPRESTEI CARD"
        model["Parc. Refin."] = "0-0"
        model["% PMT Pagas"] = "0,00-0,00"
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

            df_final = self.paint_row(df_final, "Revision")
            print("Processo concluído!")
            return df_final

        except Exception as e:
            print(f"Erro durante o processamento: {str(e)}")
            return "error"