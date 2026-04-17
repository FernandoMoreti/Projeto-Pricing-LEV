from ..services.Safra import SafraMapper
from ..services.CapitalConsig import CapitalConsigMapper
from ..services.Santander import SantanderMapper
from ..services.PanLafy import PanLafyMapper

class FactoryBank:
    _factoryBanksMapper = {
        "capitalconsig": CapitalConsigMapper(),
        "panlafy": PanLafyMapper(),
        "safra": SafraMapper(),
        "santander": SantanderMapper(),
    }

    @staticmethod
    def getMapperBank(bank):
        mapper = FactoryBank._factoryBanksMapper.get(bank.lower())
        if not mapper:
            raise ValueError(f"Banco {bank} não é suportado pelo robô.")
        return mapper
