from ..services.Amigoz import AmigozMapper
from ..services.AmigozEmprestimo import AmigozEmprestimoMapper
from ..services.BrbRed import BRBRedMapper
from ..services.AgoraConsig import AgoraConsigMapper
from ..services.EmpresteiCard import EmpresteiCardMapper
from ..services.Evol import EvolMapper
from ..services.KardBank import KardBankMapper
from ..services.MeucashCard import MeucashCardMapper
from ..services.Ole import OleMapper
from ..services.Sabemi import SabemiMapper
from ..services.Safra import SafraMapper
from ..services.Santander import SantanderMapper
from ..services.Pan import PanMapper
from ..services.PanLafy import PanLafyMapper
from ..services.ParanaBank import ParanaBankMapper
from ..services.Phtech import PhtechMapper
from ..services.PresencaBank import PresencaBankMapper
from ..services.TotalCash import TotalCashMapper
from ..services.WebCash import WebCashMapper

class FactoryBank:
    _factoryBanksMapper = {
        "amigoz": AmigozMapper(),
        "amigozemprestimo": AmigozEmprestimoMapper(),
        "brbred": BRBRedMapper(),
        "agoraconsig": AgoraConsigMapper(),
        "empresteicard": EmpresteiCardMapper(),
        "evol": EvolMapper(),
        "kardbank": KardBankMapper(),
        "meucashcard": MeucashCardMapper(),
        "ole": OleMapper(),
        "pan": PanMapper(),
        "panlafy": PanLafyMapper(),
        "phtech": PhtechMapper(),
        "paranabank": ParanaBankMapper(),
        "presencabank": PresencaBankMapper(),
        "sabemi": SabemiMapper(),
        "safra": SafraMapper(),
        "santander": SantanderMapper(),
        "totalcash": TotalCashMapper(),
        "webcash": WebCashMapper(),
    }

    @staticmethod
    def getMapperBank(bank):
        mapper = FactoryBank._factoryBanksMapper.get(bank.lower())
        if not mapper:
            raise ValueError(f"Banco {bank} não é suportado pelo robô.")
        return mapper
