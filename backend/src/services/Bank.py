from abc import ABC
import pandas as pd

class Bank(ABC):

    columns = [
        'ID', 'Instituição', 'Produto', 'Família Produto', 'Grupo Convênio',
        'Convênio', 'Operação', 'Parc. Atual', 'Parc. Refin.', '% PMT Pagas',
        '% Taxa', 'Idade', '% Comissão', '-', 'Base Comissão', '% Mínima',
        '% Intermediária', '% Máxima', '% Fator', '% TAC', 'Val. Teto TAC',
        'Faixa Val. Contrato', 'Faixa Val. Seguro', 'Vigência', 'Término',
        'Complemento', 'Venda Digital', 'Visualização Restrita',
        'Val. Base Produção', 'Id Tabela Banco',
        '% ANTECIPAÇÃO', 'REPASSE % ANTECIPAÇÃO', '1º PARCELA', 'REPASSE 1º PARCELA', 
        '2º PARCELA', 'REPASSE 2º PARCELA', 'ACORDO', 'REPASSE ACORDO', 
        'ANTECIPAÇÃO', 'REPASSE ANTECIPAÇÃO', 'ATIVAÇÃO', 'REPASSE ATIVAÇÃO', 
        'ATIVAÇÃO IMEDIATA', 'REPASSE ATIVAÇÃO IMEDIATA', 'BÔNUS', 'REPASSE BÔNUS', 
        'BONUS EXTRA', 'REPASSE BONUS EXTRA', 'BONUS VIP', 'REPASSE BONUS VIP', 
        'BONUS VP', 'REPASSE BONUS VP', 'C6 BANK C. MENSAL', 'REPASSE C6 BANK C. MENSAL', 
        'C6 BANK C. TRIMESTRAL', 'REPASSE C6 BANK C. TRIMESTRAL', 
        'C6 BANK GRT BIMESTRAL', 'REPASSE C6 BANK GRT BIMESTRAL', 
        'CAMP. META BMG', 'REPASSE CAMP. META BMG', 'CAMP. META WEBCASH', 
        'REPASSE CAMP. META WEBCASH', 'CAMPANHA ANUAL', 'REPASSE CAMPANHA ANUAL', 
        'CAMPANHA CONVENIOS', 'REPASSE CAMPANHA CONVENIOS', 'CAMPANHA FIDELIZA', 
        'REPASSE CAMPANHA FIDELIZA', 'CAMPANHA PROD.', 'REPASSE CAMPANHA PROD.', 
        'CONTA', 'REPASSE CONTA', 'CONTEMPLAÇÃO', 'REPASSE CONTEMPLAÇÃO', 
        'DIFERIMENTO', 'REPASSE DIFERIMENTO', 'NOVO SAQUE C. MENSAL', 
        'REPASSE NOVO SAQUE C. MENSAL', 'PACOTE BENEFICIO', 'REPASSE PACOTE BENEFICIO', 
        'PARCELAS', 'REPASSE PARCELAS', 'PORTABILIDADE', 'REPASSE PORTABILIDADE', 
        'PRÉ-ADESÃO', 'REPASSE PRÉ-ADESÃO', 'RESERVA TRIBUTO', 'REPASSE RESERVA TRIBUTO', 
        'ROTATIVO', 'REPASSE ROTATIVO', 'SAFRA C. MENSAL', 'REPASSE SAFRA C. MENSAL', 
        'SEGURO', 'REPASSE SEGURO', 'SEGURO BMG FAMILIAR', 'REPASSE SEGURO BMG FAMILIAR', 
        'SEGURO BMG MED FAM', 'REPASSE SEGURO BMG MED FAM', 'SEGURO BMG MED IND', 
        'REPASSE SEGURO BMG MED IND', 'SEGURO BMG MED PLUS', 'REPASSE SEGURO BMG MED PLUS', 
        'SEGURO BTW', 'REPASSE SEGURO BTW', 'SEGURO C6BANK', 'REPASSE SEGURO C6BANK', 
        'SEGURO DAYCOVAL', 'REPASSE SEGURO DAYCOVAL', 'SEGURO DIAMANTE', 
        'REPASSE SEGURO DIAMANTE', 'SEGURO PAN', 'REPASSE SEGURO PAN', 
        'SEGURO PARANA', 'REPASSE SEGURO PARANA', 'SEGURO PRESTAMISTA', 
        'REPASSE SEGURO PRESTAMISTA', 'SEGURO SUPER DIAMANTE',
        'REPASSE SEGURO SUPER DIAMANTE', 'VARIAVEL COMERCIAL', 'REPASSE VARIAVEL COMERCIAL'
    ]

    def createNullModel(self):
        return {chave: None for chave in self.columns}

    def paint_row(self, df, column):
        def apply_style(row):
            color = 'background-color: yellow' if row[column] == '' else ''
            return [color] * len(row)

        return df.style.apply(apply_style, axis=1)