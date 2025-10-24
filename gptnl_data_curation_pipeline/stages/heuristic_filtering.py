from collections import OrderedDict

from datatrove.pipeline.filters import LanguageFilter
from datatrove.pipeline.writers.parquet import ParquetWriter
from gptnl_gopher_quality_filter import GopherQualityFilter
from gptnl_gopher_repetition_filter import GopherRepetitionFilter
from gptnl_nordicpile_quality_filter import NordicPileQualityFilter
from jsonargparse import Namespace

from gptnl_data_curation_pipeline.stage import Stage


class HeuristicFilteringStage(Stage):

    def __init__(self):
        super().__init__()
        self._modules = OrderedDict(
            {
                "LanguageFilter": {
                    "cls": LanguageFilter,
                    "default": {
                        "languages": [
                            "en",  # English
                            "nl",  # Dutch
                            "da",  # Danish
                            "sv",  # Swedish
                            "af",  # Afrikaans
                            "fy",  # Frisian
                            "de",  # German
                        ]
                    },
                },
                "NordicPileQualityFilter": {
                    "cls": NordicPileQualityFilter,
                    "default": {},
                },
                "GopherQualityFilter": {
                    "cls": GopherQualityFilter,
                    "default": {
                        "min_doc_words": None,
                        "max_doc_words": None,
                        "min_avg_word_length": None,
                        "max_avg_word_length": None,
                        "max_symbol_word_ratio": 0.1,
                        "max_bullet_lines_ratio": 0.9,
                        "max_ellipsis_lines_ratio": 0.3,
                        "max_non_alpha_words_ratio": 0.8,
                        "min_stop_words": 2,
                    },
                },
                "GopherRepetitionFilter": {
                    "cls": GopherRepetitionFilter,
                    "default": {
                        "top_n_grams": [[2, 0.25], [3, 0.23], [4, 0.21]],
                        "dup_n_grams": [
                            [5, 0.20],
                            [6, 0.19],
                            [7, 0.18],
                            [8, 0.17],
                            [9, 0.16],
                            [10, 0.15],
                        ],
                    },
                },
            }
        )

    def _set_up_modules(self, args: Namespace):
        """Constructs the modules of each stage based on the CLI arguments used for this stage."""
        for module_name, module in self._modules.items():
            if module_name in args:

                output_filename = (
                    "${filter_reason}/${rank}.parquet"
                    if module_name != "LanguageFilter"
                    else "${language}/${rank}.parquet"
                )

                exclusion_writer = ParquetWriter(
                    f"{self.output_folder}/removed_data/{module_name}",
                    output_filename=output_filename,
                    expand_metadata=True,
                    max_file_size=0.5 * 2**30,  # 500MB sizes
                )
                args[module_name].exclusion_writer = exclusion_writer

                self.active_modules.append(module["cls"](**vars(args[module_name])))
