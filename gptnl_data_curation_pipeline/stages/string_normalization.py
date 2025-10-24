from collections import OrderedDict
from typing import Any

from gptnl_ftfy_formatter import FTFYFormatter
from gptnl_punctuation_formatter import PunctuationFormatter
from gptnl_whitespace_formatter import WhitespaceFormatter

from gptnl_data_curation_pipeline.stage import Stage


class StringNormalizationStage(Stage):

    def __init__(self):
        super().__init__()
        self._modules = OrderedDict(
            {
                "FTFYFormatter": {
                    "cls": FTFYFormatter,
                    "default": {"normalization": "NFC"},
                },
                "PunctuationFormatter": {"cls": PunctuationFormatter, "default": {}},
                "WhitespaceFormatter": {
                    "cls": WhitespaceFormatter,
                    "default": {},
                },
            }
        )
