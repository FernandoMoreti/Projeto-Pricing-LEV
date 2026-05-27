from ..services.Amigoz import AmigozMapper
from ..services.BrbRed import BRBRedMapper
from ..services.Safra import SafraMapper
from ..services.CapitalConsig import CapitalConsigMapper
from ..services.Santander import SantanderMapper
from ..services.Pan import PanMapper
from ..services.PanLafy import PanLafyMapper
from ..services.ParanaBank import ParanaBankMapper
from ..services.PresencaBank import PresencaBankMapper
from ..services.Ole import OleMapper

class FactoryBank:
    _factoryBanksMapper = {
        "amigoz": AmigozMapper(),
        "brbred": BRBRedMapper(),
        "capitalconsig": CapitalConsigMapper(),
        "pan": PanMapper(),
        "panlafy": PanLafyMapper(),
        "paranabank": ParanaBankMapper(),
        "presencabank": PresencaBankMapper(),
        "safra": SafraMapper(),
        "santander": SantanderMapper(),
        "ole": OleMapper(),
    }

    @staticmethod
    def getMapperBank(bank):
        mapper = FactoryBank._factoryBanksMapper.get(bank.lower())
        if not mapper:
            raise ValueError(f"Banco {bank} não é suportado pelo robô.")
        return mapper
