from .Bank import Bank
from datetime import datetime, timedelta
import pandas as pd
import io
from ..utils.utils import convertValues, formatar_br, remover_acentos, limpar_zeros, rename_duplicates
from ..config.bank.PanVariables import family_product, group_convenio, operation
from ..config.citys_uf import citys, citys_uf, states
from ..config.grade import grade

class PanMapper(Bank):

    def read_archive(self, file):
        df = pd.read_excel(io.BytesIO(file), sheet_name=None)
        return df

    def compare_archive(self, df_work, df_bank):

        df_bank_b2b = df_bank["B2B"]
        novas_linhas = []

        # Fragmentar linhas
        for index, row in df_bank_b2b.iterrows():
            if row["Seguro"] == "S":
                row_copy = row.copy()
                row_copy["teste_seguro"] = "1,20 | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                novas_linhas.append(row_copy)

        df_bank_b2b_privado = df_bank["B2B Privado"]

        df_bank_fgts = df_bank["FGTS"]
        # Fragmentar linhas
        for index, row in df_bank_fgts.iterrows():
            row_copy = row.copy()
            row_copy2 = row.copy()
            row_copy3 = row.copy()
            row_copy["teste_seguro"] = "17,55 | FIXO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
            row_copy2["teste_seguro"] = "405,00 | FIXO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
            row_copy3["teste_seguro"] = "2,25 | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
            novas_linhas.append(row_copy)
            novas_linhas.append(row_copy2)
            novas_linhas.append(row_copy3)

        df_bank_cartao = df_bank["Cartão"]
        df_bank_cartao.columns = df_bank_cartao.iloc[0]
        df_bank_cartao = df_bank_cartao[1:]

        df_bank_cartao.columns = rename_duplicates(df_bank_cartao.columns)

        colunas_base = ['Convênio', 'Empregador', 'Prazo', 'Tipo', 'Código da tabela']

        dados_final = []

        # Fragmentar linhas
        for index, row in df_bank_cartao.iterrows():
            linha_cartao = {col: row[col] for col in colunas_base}

            linha_cartao['Operação'] = 'CARTÃO'
            linha_cartao['Flat'] = row['Flat']
            linha_cartao['PMT'] = row['PMT']
            linha_cartao['Seguro'] = row['Seguro']
            linha_cartao["base_comissao"] = "LÍQUIDO"
            linha_cartao["Venda"] = row["Venda"]
            linha_cartao["Ativacao"] = row["Ativacao"]

            linha_plastico = linha_cartao.copy()
            linha_plastico["Empregador"] = linha_plastico["Empregador"] + " - PLASTICO"
            linha_plastico["Flat"] = 0
            linha_plastico["PMT"] = 0
            linha_plastico["base_comissao"] = "FIXO "
            linha_plastico["Venda"] = row["Venda"]
            linha_plastico["Ativacao"] = row["Ativacao"]

            if row["Seguro"] == "S":
                linha_cartao_seguro = linha_cartao.copy()
                linha_cartao_seguro['teste_seguro'] = "1,47 | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                dados_final.append(linha_cartao_seguro)
            dados_final.append(linha_plastico)
            dados_final.append(linha_cartao)

            linha_saque = {col: row[col] for col in colunas_base}

            linha_saque['Operação'] = 'SAQUE COMPL.'
            linha_saque['Flat'] = row['Flat.1']
            linha_saque['PMT'] = row['PMT.1']
            linha_saque['Seguro'] = row['Seguro.1']
            linha_saque["base_comissao"] = "LÍQUIDO"

            if row["Seguro"] == "S":
                linha_saque_seguro = linha_saque.copy()
                linha_saque_seguro['teste_seguro'] = "1,47 | LIQUIDO | 0,00 | NÃO | SEM VIG. INÍCIO | SEM VIG. TÉRMINO"
                dados_final.append(linha_saque_seguro)
            dados_final.append(linha_saque)

        df_bank_cartao = pd.DataFrame(dados_final)

        df_bank = pd.concat([df_bank_b2b, df_bank_b2b_privado, df_bank_fgts], ignore_index=True)

        if novas_linhas:
            df_bank = pd.concat([df_bank, pd.DataFrame(novas_linhas)], ignore_index=True)

        df_bank["Tabela Financiamento"] = df_bank["Tabela Financiamento"].str.strip()
        df_bank_cartao["Empregador"] = df_bank_cartao["Empregador"].str.strip()
        df_work["Produto"] = df_work["Produto"].str.strip()

        excecoes = ["Refinanciamento de Portabilidade Pós"]

        mask = ~df_bank["Operação"].isin(excecoes)
        df_bank.loc[mask, "Operação"] = df_bank.loc[mask, "Operação"].map(operation).fillna("")

        df_bank = df_bank[df_bank['Operação'] != 'Refinanciamento de Portabilidade Pós']

        for index, row in df_bank.iterrows():
            row["Plano"] = str(row["Plano"]).strip()
            if 'até' in row["Plano"]:
                novo_valor = f"{row['Plano'].split('até')[0].strip()}-{row['Plano'].split('até')[1].strip()}"
            else:
                if '-' in row["Plano"]:
                    novo_valor = limpar_zeros(row["Plano"])
                else:
                    novo_valor = f"{row['Plano']}-{row['Plano']}"

            df_bank.at[index, "Plano"] = novo_valor

        df_work_cartao = df_work[(df_work['Operação'] == 'CARTÃO') | (df_work['Operação'] == 'SAQUE COMPL.')]
        df_bank_cartao["Prazo"] = "1-" + df_bank_cartao["Prazo"].astype(str)

        df_work_all = df_work[(df_work['Operação'] != 'CARTÃO') & (df_work['Operação'] != 'SAQUE COMPL.')]

        df_result = pd.merge(
            df_bank,
            df_work_all,
            left_on=["Tabela Financiamento", "Operação", "Plano", "teste_seguro"],
            right_on=["Produto", "Operação", "Parc. Atual", "SEGURO PAN"],
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

        df_result = pd.merge(
            df_bank_cartao,
            df_work_cartao,
            left_on=["Empregador", "Prazo", "Operação", "base_comissao", "teste_seguro"],
            right_on=["Produto", "Parc. Atual", "Operação", "Base Comissão", "SEGURO PAN"],
            how="outer",
            indicator=True
        )

        df_open = df_result[df_result["_merge"] == "left_only"]
        df_close = df_result[df_result["_merge"] == "right_only"]
        df_matches = df_result[df_result["_merge"] == "both"]

        for index, row in df_close.iterrows():
            list_of_close_tables.append(row)

        for index, row in df_open.iterrows():
            list_of_open_tables.append(row)

        # Validar matches
        for index, row in df_matches.iterrows():

            percent = convertValues(row["Flat"]) * 100
            percent_work = convertValues(row["% Comissão"])

            if pd.notna(row["PMT"]):
                diferimento = round(convertValues(row["PMT"]) * 100, 2)
            else:
                diferimento = 0.0

            if pd.notna(row["DIFERIMENTO"]):
                diferimento_work = convertValues(row["DIFERIMENTO"].split("|")[0].strip())
            else:
                diferimento_work = 0.0

            if pd.notna(row["Venda"]):
                if row["Venda"] == "":
                    pre_adesao = 0.0
                else:
                    pre_adesao = convertValues(row["Venda"])
            else:
                pre_adesao = 0.0

            if pd.notna(row["PRÉ-ADESÃO"]):
                pre_adesao_work = convertValues(row["PRÉ-ADESÃO"].split("|")[0].strip())
            else:
                pre_adesao_work = 0.0

            if pd.notna(row["Ativacao"]):
                if row["Ativacao"] == "":
                    ativacao = 0.0
                else:
                    ativacao = convertValues(row["Ativacao"])
            else:
                ativacao = 0.0

            if pd.notna(row["ATIVAÇÃO"]):
                ativacao_work = convertValues(row["ATIVAÇÃO"].split("|")[0].strip())
            else:
                ativacao_work = 0.0

            if percent != percent_work:
                list_to_close_and_open.append(row)
            elif diferimento != diferimento_work:
                list_to_close_and_open.append(row)
            elif pre_adesao != pre_adesao_work:
                list_to_close_and_open.append(row)
            elif ativacao != ativacao_work:
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