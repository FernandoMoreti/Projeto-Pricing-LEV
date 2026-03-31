from abc import ABC, abstractmethod

class Bank(ABC):

    columns = ['ID', 'Instituição', 'Produto', 'Família Produto', 'Grupo Convênio',
       'Convênio', 'Operação', 'Parc. Atual', 'Parc. Refin.', '% PMT Pagas',
       '% Taxa', 'Idade', '% Comissão', '-', 'Base Comissão', '% Mínima',
       '% Intermediária', '% Máxima', '% Fator', '% TAC', 'Val. Teto TAC',
       'Faixa Val. Contrato', 'Faixa Val. Seguro', 'Vigência', 'Término',
       'Complemento', 'Venda Digital', 'Visualização Restrita',
       'Val. Base Produção', 'Id Tabela Banco', 'BONUS VIP',
       'REPASSE BONUS VIP']

    def createNullModel(self):
        return {chave: None for chave in self.columns}