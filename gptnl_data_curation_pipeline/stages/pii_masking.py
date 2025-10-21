from collections import OrderedDict

from gptnl_pii_mappers import PII_PrivateAI_TNO
from gptnl_pii_mappers._backend.private_ai_pii_list import PrivateAI_TNO
from jsonargparse import Namespace

from gptnl_data_curation_pipeline.stage import Stage


class PIIMaskingStage(Stage):

    def __init__(self):
        super().__init__()
        self._modules = OrderedDict(
            {
                "PII_PrivateAI_TNO": {
                    "cls": PII_PrivateAI_TNO,
                    "default": {
                        "api_endpoint": "http://localhost:8080/",
                        "replacement_type": "SYNTHETIC",
                        "entity_grouping_window": 4500,
                        "check_public_figure": True,
                        "record_processed_entities": True,
                        "request_batch_size": 1,
                    },
                    "skip": {"entity_types", "category"},
                },
            }
        )
