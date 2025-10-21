import json
import re
from collections import OrderedDict
from typing import List

from datatrove.data import Document
from datatrove.pipeline.base import PipelineStep
from datatrove.pipeline.filters import LambdaFilter, LanguageFilter
from datatrove.pipeline.readers import ParquetReader
from datatrove.pipeline.writers.disk_base import DiskWriter
from datatrove.pipeline.writers.parquet import ParquetWriter
from gptnl_machine_translation.pipeline import SplittedRowsCombiner, TranslatorStep
from gptnl_regex_formatter.regex_formatter import RegexFormatter
from jsonargparse import ArgumentParser, Namespace

from gptnl_data_curation_pipeline.stage import Stage


class MachineTranslation(Stage):
    """Translates a dataset into Dutch, by splitting long text into smaller chunks."""

    def __init__(self):
        super().__init__()
        self._modules = OrderedDict(
            {
                "RegexFormatter": {  # TODO: check how to allow disabling this, or move to different Stage
                    "cls": RegexFormatter,
                    "default": {
                        "pattern": [
                            r"\b(\w+)\s+\1\s+\1(\s+\1)*\b",
                            r"\s?\[[a-zA-Z&;_à-üÀ-Ü\s]{0,15}\]",  # space at the beginning avoids double space in result, there are also a lot of [&nbsp;__&nbsp;]
                        ],
                        "repl": [r"\1", ""],
                        "flags": [re.DOTALL, re.S],
                    },
                },
                "RegexFormattedRowsParquetWriter": {
                    "cls": ParquetWriter,
                    "default": {"expand_metadata": True, "output_folder": ""},
                },
                # "PreLanguageFilter": {
                #     "cls": LanguageFilter,  # TODO: use filter on metadata of source dataset
                #     "default": {
                #         "languages": ["en"],  # TODO: germanic, spanish, french
                #         "language_threshold": 0.65,  # TODO: lower it
                #     },
                # },
                "ExtraFieldFilter": {
                    "cls": ExtraFieldFilterStep,
                    "default": {
                        "extra_field_name": ["original_language"],
                        "allowed_values": ["en"],
                        "raise_when_field_missing": True,
                        "keep_when_field_missing": False,
                    },
                },
                "TranslatorStep": {
                    "cls": TranslatorStep,
                    "default": {
                        "chunk_size": 1024,
                        "batch_size": 32,
                        "stop_at": None,
                        "batch_stop_at": None,
                        "dry_run": False,
                    },
                },
                "PostLanguageFilter": {
                    "cls": LanguageFilter,
                    "default": {
                        "languages": ["nl"],
                        "language_threshold": 0.65,
                    },
                },
                # "ChunksParquetWriter": { # Commented out: creates problem writing, inconsistent schema
                #     "cls": ParquetWriter,
                #     "default": {"expand_metadata": True, "output_folder": ""},
                # },
                "SplittedRowsCombiner": {"cls": SplittedRowsCombiner, "default": {}},
            }
        )

    def _specify_cli_arguments(self, parser_subcommand: ArgumentParser):
        """Specify CLI arguments.

        Args:
            parser_subcommand (ArgumentParser): the parser for the subcommand.
        """
        super()._specify_cli_arguments(parser_subcommand)

    def _set_up_modules(self, args: Namespace):
        """Constructs the modules of each stage based on the CLI arguments used for this stage."""
        # Some modules need to use self.output_folder not available at __init__
        for module_name, module in self._modules.items():
            if module_name in args:
                if module_name == "ExtraFieldFilter":
                    exclusion_writer = ParquetWriter(
                        f"{self.output_folder}/removed_data/extra_field_filter_pre_translation",
                        output_filename="${rank}.parquet",
                    )
                    args[module_name].exclusion_writer = exclusion_writer

                elif module_name == "PostLanguageFilter":
                    exclusion_writer = ParquetWriter(
                        f"{self.output_folder}/removed_data/language_filter_post_translation",
                        output_filename="${language}/${rank}.parquet",
                    )
                    args[module_name].exclusion_writer = exclusion_writer

                elif module_name == "ChunksParquetWriter":
                    args[module_name].output_folder = str(
                        f"{self.output_folder}/translated_chunks"
                    )

                elif module_name == "RegexFormattedRowsParquetWriter":
                    args[module_name].output_folder = str(
                        f"{self.output_folder}/regex_formatted_rows"
                    )

        super()._set_up_modules(args=args)


class ExtraFieldFilterStep(LambdaFilter):
    def __init__(
        self,
        extra_field_name: str,
        allowed_values: List[str],
        raise_when_field_missing: bool = True,
        keep_when_field_missing: bool = False,
        exclusion_writer: DiskWriter = None,
    ):
        self.extra_field_name = extra_field_name
        self.allowed_values = allowed_values
        self.raise_when_field_missing = raise_when_field_missing
        self.keep_when_field_missing = keep_when_field_missing
        super().__init__(self.filter_function, exclusion_writer=exclusion_writer)

    def filter_function(self, doc: Document) -> bool:
        extra = doc.metadata.get("extra", "")
        if not extra:
            extra_parsed = {}
        elif isinstance(extra, str):
            extra_parsed = json.loads(extra)
        elif isinstance(extra, dict):
            extra_parsed = extra
        else:
            raise ValueError(f"extra is of type {type(extra)}")
        existing_keys = extra_parsed.keys()
        if self.extra_field_name not in existing_keys:
            if self.raise_when_field_missing:
                raise KeyError(
                    f"{self.extra_field_name} not found in extra fields: {existing_keys}"
                )
            else:
                return self.keep_when_field_missing
        else:
            value = extra_parsed[self.extra_field_name]
            return value in self.allowed_values
