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
        print(df)
        return df

    def compare_archive(self, df_work, df_bank):

        novas_linhas = []

        for index, row in df_bank.iterrows():
            if row["Produto"] == "Cartão Consignado" or row["Produto"] == "Cartão Benefício":
                row["Convênio"] = (row["Convênio"] + ' - ' + row["Produto"]).upper()
                row["Prazo"] = str(row["Prazo"]) + '-' + str(row["Prazo"])
                row["Taxa %"] = str(row["ID"]).strip() + ' | TX ' + str(round(row["Taxa %"], 2)) + '%'

                row_cartao = row.copy()
                row_saque = row.copy()
                row_cartao_seguro = row.copy()
                row_cartao_seguro["Taxa %"] = row_cartao_seguro["Taxa %"] + ' - COM SEGURO'
                row_saque_seguro = row.copy()
                row_saque_seguro["Taxa %"] = row_saque_seguro["Taxa %"] + ' - COM SEGURO'

                if pd.notna(row["Apenas cartão"]):
                    row["Convênio"] = row["Convênio"] + ' - PLASTICO'
                    row_plastico = row.copy()
                    novas_linhas.append(row_plastico)

                novas_linhas.append(row_cartao)
                novas_linhas.append(row_cartao_seguro)
                novas_linhas.append(row_saque)
                novas_linhas.append(row_saque_seguro)

        if novas_linhas:
            df_bank = pd.DataFrame(novas_linhas)

        df_work["Produto"] = df_work["Produto"].str.strip()

        df_result = pd.merge(
            df_bank,
            df_work,
            left_on=["Convênio", "Prazo", "Taxa %"],
            right_on=["Produto", "Parc. Atual", "Complemento"],
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

            percent = convertValues(row["Flat"])
            percent_work = convertValues(row["% Comissão"])

            if pd.notna(row["Pmt"]):
                diferimento = convertValues(row["Pmt"])
            else:
                diferimento = None

            if pd.notna(row["DIFERIMENTO"]):
                diferimento_work = convertValues(row["DIFERIMENTO"].split("|")[0].strip())
            else:
                diferimento_work = 0.0

            if percent != percent_work:
                list_to_close_and_open.append(row)
            elif diferimento != diferimento_work:
                list_to_close_and_open.append(row)

        return list_of_open_tables, list_of_close_tables, list_to_close_and_open

    def extract_city(self, product):
        product = str(product).upper().strip()

        if "IPREM" in product:
            return citys.get("IPREM", "")

        if "_" in product:
            cidade = product.split("_")[1]
        else:
            cidade = product.split(" ")[1]

        if cidade == "SEC":
            return citys.get("SEC", "")

        if cidade in ["CAMPINA", "PORTO", "SANTA", "SAO", "BELO"]:
            if "_" in product:
                cidade = product.split("_")[1] + " " + product.split("_")[2]
            else:
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
        state = str(rest_of_product).upper().strip()

        if "IPSEMG" in state:
            return states.get("IPSEMG", "")

        if "_" in state:
            state = state.split("_")[1]
        else:
            state = state.split(" ")[1]

        state = remover_acentos(state)

        if len(state) == 2:
            return state

        uf = states.get(state, "")

        return uf

    def get_convenio(self, product):

        firstProduct = str(product).upper().split(" ")[0].strip()

        categorias = {
            "GOV-": ["GOV", "GOV_", "GOV.", "GOV ", "SPPREV_", "AMA", "PMESP", "IPSEMG", "RIO"],
            "FEDERAL SIAPE": ["SIAPE", "SIA"],
            "PREF. ": ["PREF", "PREF_", "PREF.", "PREF ", "IPREM", "PRE_"],
            "TJ | ": ["TJ ", "TJ_", "TJ."],
        }

        if firstProduct in ["AERONAUTICA", "MARINHA", "FGTS", "INSS", "CLT", "INSSC15"]:
            return firstProduct

        if "FGTS" in product:
            return "FGTS"

        if "CONSIG PRIVADO" in product:
            return "CLT"

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
                    uf = self.extract_uf_of_state(firstProduct)
                    convenio = convenio + uf
                    return convenio

        return "CONVENIO DESCONHECIDO"

    def create_open_tables(self, list_of_open_tables, model):

        list_of_convert_rows = []

        for row in list_of_open_tables:

            product = row["Empregador"]
            convenio = self.get_convenio(product)

            if "-" in convenio:
                agreement = convenio.split("-")[0].strip()
            else:
                agreement = convenio.split()[0].strip()

            family = family_product[agreement]
            group = group_convenio[family]

            percent = convertValues(row["Flat"])

            operation = row["Operação"]

            if (operation == "CARTÃO") or (operation == "SAQUE COMPL."):
                percent = percent * 100

            grades = grade.get(operation, "")

            if operation == "CARTÃO" or operation == "SAQUE COMPL.":
                nameTable = row["Empregador"]
                prazo = row["Prazo"]
                codigo = row["Código da tabela"]
            else:
                nameTable = row["Tabela Financiamento"]
                prazo = row["Plano"]
                codigo = row["Cód Tabela"]


            new_row = model.copy()

            if operation == "PORTABILIDADE":
                new_row["Base Comissão"] = "BRUTO"
                new_row["Val. Base Produção"] = "BRUTO"
            else:
                new_row["Base Comissão"] = "LÍQUIDO"
                new_row["Val. Base Produção"] = "LÍQUIDO"
            new_row["Operação"] = operation
            new_row["Produto"] = nameTable
            new_row["Família Produto"] = family
            new_row["Grupo Convênio"] = group
            new_row["Convênio"] = convenio
            new_row["Parc. Atual"] = prazo
            new_row["% Mínima"] = percent * grades["min"]
            new_row["% Intermediária"] = percent * grades["med"]
            new_row["% Máxima"] = percent * grades["max"]
            new_row["% Comissão"] = percent
            new_row["Vigência"] = datetime.now().strftime("%d/%m/%Y")
            new_row["Complemento"] = int(codigo)
            new_row["Id Tabela Banco"] = int(codigo)
            new_row["SEGURO PAN"] = row["teste_seguro"]

            if pd.notna(new_row["SEGURO PAN"]) and new_row["SEGURO PAN"] != '':
                if "1,20" in new_row["SEGURO PAN"]:
                    new_row["REPASSE SEGURO PAN"] = "1,00 | 1,00 | 1,00"
                elif "1,47" in new_row["SEGURO PAN"]:
                    new_row["REPASSE SEGURO PAN"] = "1,20 | 1,20 | 1,20"
                elif "17,55" in new_row["SEGURO PAN"]:
                    new_row["REPASSE SEGURO PAN"] = "14,04 | 16,67 | 17,55"
                elif "2,25" in new_row["SEGURO PAN"]:
                    new_row["REPASSE SEGURO PAN"] = "1,80 | 2,13 | 2,25"
                elif "405,00" in new_row["SEGURO PAN"]:
                    new_row["REPASSE SEGURO PAN"] = "324,00 | 384,75 | 405,00"

            if family == "CLT":
                new_row["Visualização Restrita"] = "NÃO"
                new_row["Venda Digital"] = "NÃO"
            else:
                new_row["Visualização Restrita"] = "SIM"
                new_row["Venda Digital"] = "SIM"

            if row["SEGURO PAN"] != '':
                new_row["Faixa Val. Seguro"] = "2,00-5.000,00"
            else:
                new_row["Faixa Val. Seguro"] = "0,00-1,00"

            if operation == "REFIN":
                new_row["Parc. Refin."] = "0-99"
                new_row["% PMT Pagas"] = "0,00-99,00"
            else:
                new_row["Parc. Refin."] = "0-0"
                new_row["% PMT Pagas"] = "0,00-0,00"

            if percent == 0:
                new_row["-"] = "$"
            else:
                new_row["-"] = "%"

            if operation == "CARTÃO" or operation == "SAQUE COMPL.":
                if pd.notna(row["Ativacao"]) and row["Ativacao"] != None and row["Ativacao"] != 0:
                    new_row["ATIVAÇÃO"] = f"{row['ATIVAÇÃO']} | FIXO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"

                    if row["Ativacao"] == 80:
                        new_row["REPASSE ATIVAÇÃO"] = "56,00 | 68,00 | 76,00"
                    elif row["Ativacao"] == 50:
                        new_row["REPASSE ATIVAÇÃO"] = "35,00 | 40,00 | 45,00"
                    elif row["Ativacao"] == 40:
                        new_row["REPASSE ATIVAÇÃO"] = "28,00 | 32,00 | 36,00"

                if pd.notna(row["Venda"]) and row["Venda"] != None and row["Venda"] != 0:
                    new_row["PRÉ-ADESÃO"] = f"{row['Venda']} | FIXO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"

                    if row["Venda"] == 50:
                        new_row["REPASSE ATIVAÇÃO"] = "35,00 | 40,00 | 45,00"
                    elif row["Venda"] == 80:
                        new_row["REPASSE ATIVAÇÃO"] = "60,00 | 68,00 | 76,00"
                    elif row["Venda"] == 160:
                        new_row["REPASSE ATIVAÇÃO"] = "112,00 | 128,00 | 144,00"
                    elif row["Venda"] == 300:
                        new_row["REPASSE ATIVAÇÃO"] = "28,00 | 32,00 | 36,00"

                if pd.notna(row["PMT"]) and row["PMT"] != None and round(row["PMT"] * 100, 2) != 0:
                    new_row["DIFERIMENTO"] = f"{round(row['PMT'] * 100, 2)} | FIXO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                    new_row["REPASSE DIFERIMENTO"] = "0,00 | 0,00 | 0,00"
            else:
                if pd.notna(row["Pmt"]) and row["Pmt"] != None and round(row["Pmt"] * 100, 2) != 0:
                    new_row["DIFERIMENTO"] = f"{round(row['Pmt'] * 100, 2)} | FIXO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                    new_row["REPASSE DIFERIMENTO"] = "0,00 | 0,00 | 0,00"


            if family == "CLT":
                new_row["Faixa Val. Contrato"] = "0,00-100.000,00-BRUTO"
            elif family == "FGTS" and new_row["SEGURO PAN"] == "2,25 | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO":
                new_row["Faixa Val. Contrato"] = "780,00-18.000,00-LÍQUIDO"
            elif family == "FGTS" and new_row["SEGURO PAN"] == "405,00 | FIXO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO":
                new_row["Faixa Val. Contrato"] = "18.000,01-100.000,00-LÍQUIDO"
            elif family == "FGTS" and new_row["SEGURO PAN"] == "17,55 | FIXO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO":
                new_row["Faixa Val. Contrato"] = "0,00-779,00-LÍQUIDO"
            elif new_row["Faixa Val. Seguro"] == "0,00-1,00":
                new_row["Faixa Val. Contrato"] = "0,00-100.000,00-LÍQUIDO"
            elif new_row["Faixa Val. Seguro"] == "2,00-5.000,00":
                new_row["Faixa Val. Contrato"] = "0,00-18.000,00-LÍQUIDO"

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

        df['Vigência_y'] = df['Vigência_y'].combine_first(df['Vigência'])

        df = df.drop(['Convênio_x', 'Empregador', 'Cód Tabela',
       'Tabela Financiamento', 'Tipo Tabela', 'Plano', 'Taxa Início',
       'Taxa Fim', 'Flat', 'Pmt', 'Fator Antecipação', 'Vp Antecipada',
       'VP Total', 'Port', 'MinOperacao', 'MaxOperacao', 'MinParcela',
       'Seguro', '% Fator Seguro', 'Prêmio', 'Comissão Seguro',
       'Comissão Seguro + VP ', 'Vigência_x', 'Observação', 'teste_seguro', 'Prazo',
       'Tipo', 'Código da tabela', 'PMT', 'base_comissao', 'Venda', 'Ativacao', 'Vigência'], axis=1)

        df.columns = df.columns.str.replace('_y', '')

        return df

    def create_close_open_tables(self, list_of_close_open):

        list_of_convert_open_rows = []
        list_of_convert_close_rows = []

        for row in list_of_close_open:

            percent = convertValues(row["Flat"])

            row_close = row.copy()

            row_close["Término"] = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            row_close["Atualizações"] = "ALTERAÇÃO"

            list_of_convert_close_rows.append(row_close)

            row_open = row.copy()

            operation = row["Operação"]

            if operation == "PORTABILIDADE":
                row_open["Base Comissão"] = "BRUTO"
                row_open["Val. Base Produção"] = "BRUTO"
            else:
                row_open["Base Comissão"] = "LÍQUIDO"
                row_open["Val. Base Produção"] = "LÍQUIDO"

            grades = grade.get(operation, "")

            row_open["Término"] = ""
            row_open["Vigência_y"] = datetime.now().strftime("%d/%m/%Y")
            row_open["ID"] = ''
            row_open["% Comissão"] = percent
            row_open["Operação"] = operation
            row_open["% Mínima"] = percent * grades["min"]
            row_open["% Intermediária"] = percent * grades["med"]
            row_open["% Máxima"] = percent * grades["max"]
            row_open["Atualizações"] = "ALTERAÇÃO"

            if pd.notna(row["Pmt"]) and row["Pmt"] != None and round(row["Pmt"] * 100, 2) != 0:
                row_open["DIFERIMENTO"] = f"{round(row['Pmt'] * 100, 2)} | FIXO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                row_open["REPASSE DIFERIMENTO"] = "0,00 | 0,00 | 0,00"

            list_of_convert_open_rows.append(row_open)

        df = pd.DataFrame(list_of_convert_close_rows)
        df2 = pd.DataFrame(list_of_convert_open_rows)

        colunas_para_dropar = [
            'Convênio_x', 'Empregador', 'Cód Tabela',
            'Tabela Financiamento', 'Tipo Tabela', 'Plano', 'Taxa Início',
            'Taxa Fim', 'Flat', 'Pmt', 'Fator Antecipação',
            'Vp Antecipada', 'VP Total', 'Port', 'MinOperacao',
            'MaxOperacao', 'MinParcela', 'Seguro', '% Fator Seguro',
            'Prêmio', 'Comissão Seguro', 'Comissão Seguro + VP',
            'Vigência_x', 'Observação', 'teste_seguro', '_merge', 'Vigência'
        ]


        df = df.drop(colunas_para_dropar, axis=1, errors='ignore')
        df2 = df2.drop(colunas_para_dropar, axis=1, errors='ignore')

        df.columns = df.columns.str.replace('_y', '')
        df2.columns = df2.columns.str.replace('_y', '')

        return df, df2

    def input_standard_values(self, model):

        model["Instituição"] = "PAN"
        model["% Taxa"] = "0,00-0,00"
        model["Idade"] = "0-80"
        model["% Fator"] = "0,000000000"
        model["% TAC"] = "0,000000"
        model["Val. Teto TAC"] = "0,000000"
        model["Visualização Restrita"] = "Não"

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