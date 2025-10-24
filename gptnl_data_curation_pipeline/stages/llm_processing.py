from collections import OrderedDict

from datatrove.pipeline.base import PipelineStep
from datatrove.pipeline.filters import LanguageFilter, RegexFilter
from datatrove.pipeline.readers import ParquetReader
from datatrove.pipeline.writers.parquet import ParquetWriter
from gptnl_llm_processing.pipeline_step import LLMProcessingStep, RowSplitterOrCombiner
from jsonargparse import ArgumentParser, Namespace

from gptnl_data_curation_pipeline.stage import Stage


class LLMProcessingStage(Stage):
    """Use LLM to process text"""

    def __init__(self):
        super().__init__()
        self._modules = OrderedDict(
            {
                "RowSplitter": {
                    "cls": RowSplitterOrCombiner,
                    "default": {
                        "split": True,
                    },
                },
                "RegexFilter": {
                    "cls": RegexFilter,
                    "default": {
                        "regex_exp": r"([\d°]{3,})|(\.(\w{2,4}))|(\/\w+\/\w+)|(WorldCat)|(Wikikids)",
                    },
                },
                "RowCombiner": {
                    "cls": RowSplitterOrCombiner,
                    "default": {
                        "split": False,
                    },
                },
                "LLMProcessingStep": {
                    "cls": LLMProcessingStep,
                    "default": {
                        "model_name": "microsoft/phi4",
                        "prompt": "Given the following sentences, produce a fluent and coherent paragraph that contains all the information in the sentences. Do not generate any information that is not in the sentences. Ensure that the paragraph is grammatically and syntactically correct in Dutch. Do not produce any additional text, only the paragraph.\nSentences:\n{text}\n\nParagraph:\n",
                    },
                },
                "LanguageFilter": {
                    "cls": LanguageFilter,
                    "default": {
                        "languages": ["nl", "en"],
                        "language_threshold": 0.65,
                    },
                },
            }
        )

    def specify_cli_arguments(self, parser_subcommand: ArgumentParser):
        """Specify CLI arguments.

        Args:
            parser_subcommand (ArgumentParser): the parser for the subcommand.
        """
        super().specify_cli_arguments(parser_subcommand)

    def set_up_modules(self, args: Namespace):
        """Constructs the modules of each stage based on the CLI arguments used for this stage."""
        # Some modules need to use self.output_folder not available at __init__
        for module_name, module in self._modules.items():
            if module_name in args:
                if module_name == "RegexFilter":
                    exclusion_writer = ParquetWriter(
                        f"{self.output_folder}/removed_data/regex_filter",
                        output_filename="${rank}.parquet",
                    )
                    args[module_name].exclusion_writer = exclusion_writer

                elif module_name == "LanguageFilter":
                    exclusion_writer = ParquetWriter(
                        f"{self.output_folder}/removed_data/language_filter_post_translation",
                        output_filename="${language}/${rank}.parquet",
                    )
                    args[module_name].exclusion_writer = exclusion_writer

        super().set_up_modules(args=args)
