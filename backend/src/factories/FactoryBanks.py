from ..services.CapitalConsig import CapitalConsigMapper

class FactoryBank:
    _factoryBanksMapper = {
        "capitalconsig": CapitalConsigMapper(),
    }

    @staticmethod
    def getMapperBank(bank):
        mapper = FactoryBank._factoryBanksMapper.get(bank.lower())
        if not mapper:
            raise ValueError(f"Banco {bank} não é suportado pelo robô.")
        return mapper
