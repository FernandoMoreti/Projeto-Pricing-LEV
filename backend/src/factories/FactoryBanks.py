from ..services.Amigoz import AmigozMapper
from ..services.BrbRed import BRBRedMapper
from ..services.CapitalConsig import CapitalConsigMapper
from ..services.Evol import EvolMapper
from ..services.KardBank import KardBankMapper
from ..services.Ole import OleMapper
from ..services.Safra import SafraMapper
from ..services.Santander import SantanderMapper
from ..services.Pan import PanMapper
from ..services.PanLafy import PanLafyMapper
from ..services.ParanaBank import ParanaBankMapper
from ..services.Phtech import PhtechMapper
from ..services.PresencaBank import PresencaBankMapper
from ..services.TotalCash import TotalCashMapper

class FactoryBank:
    _factoryBanksMapper = {
        "amigoz": AmigozMapper(),
        "brbred": BRBRedMapper(),
        "capitalconsig": CapitalConsigMapper(),
        "evol": EvolMapper(),
        "kardbank": KardBankMapper(),
        "ole": OleMapper(),
        "pan": PanMapper(),
        "panlafy": PanLafyMapper(),
        "phtech": PhtechMapper(),
        "paranabank": ParanaBankMapper(),
        "presencabank": PresencaBankMapper(),
        "safra": SafraMapper(),
        "santander": SantanderMapper(),
        "totalcash": TotalCashMapper(),
    }

    @staticmethod
    def getMapperBank(bank):
        mapper = FactoryBank._factoryBanksMapper.get(bank.lower())
        if not mapper:
            raise ValueError(f"Banco {bank} não é suportado pelo robô.")
        return mapper
