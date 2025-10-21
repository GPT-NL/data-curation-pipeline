from collections import OrderedDict

from gptnl_toxic_language_detection import ToxicLanguageDetection
from jsonargparse import Namespace

from gptnl_data_curation_pipeline.stage import Stage


class ToxicLanguageDetectionStage(Stage):

    def __init__(self):
        super().__init__()
        self._modules = OrderedDict(
            {
                "ToxicLanguageDetection": {
                    "cls": ToxicLanguageDetection,
                    "default": {
                        "threshold": 0.995,
                        "max_chunk_length": 256,
                    },
                },
            }
        )
