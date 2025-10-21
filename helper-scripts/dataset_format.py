## This file helps preparing the dataset for delivery formatting it to a standard format.
##
## The scritp receives one parquet file as input.
## It drops all the columns that are NOT in the standard format column set, and it saves the result with the same filename.  Thus, this script replaces the original file!!! Use with caution.
from pathlib import Path
from typing import Tuple
import pandas as pd
import pyarrow.parquet as pq
import sys
import argparse

from parquet_utils import (
    format_dataset_to_gpt_nl_standard,
    parquet_files_in,
)


def make_parser():
    """Create an argument parser for the script."""
    _SCRIPT_DESCRIPTION = (
        "Format dataset to comply with the GPT-NL dataset standard format.\n\n"
        "Please ensure to backup your original file before running this script.\n"
        "This script replaces the original file, use with caution.\n"
    )
    parser = argparse.ArgumentParser(description=_SCRIPT_DESCRIPTION)
    parser.add_argument(
        "file_path",
        type=str,
        help="Path to the input parquet file. If file path is a directory, the command will apply the format to all the internal *.parquet files.",
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="A dry run will save the changes to a new file with '_formatted' suffix instead of overwriting the original file.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Assume 'yes' to all prompts, useful for scripting.",
    )
    return parser


if __name__ == "__main__":

    parser = make_parser()
    args = parser.parse_args()
    file_path = Path(args.file_path).resolve()

    print(parser.description)

    if (
        not args.yes
        and not args.dry_run
        and (
            input("Do you want to continue? (yes/no) Default is no: ").strip().lower()
            != "yes"
        )
    ):
        print("Operation cancelled.")
        sys.exit(0)

    def destination_path(file_path: str) -> Path:
        """Determine the destination path for the formatted file."""
        if args.dry_run:
            return Path(file_path.replace(".parquet", "_formatted.parquet"))
        return Path(file_path)

    if file_path.is_file():
        save_to = destination_path(str(file_path))
        format_dataset_to_gpt_nl_standard(file_path=file_path, dest_path=save_to)

    if file_path.is_dir():
        parquet_files = parquet_files_in(file_path, recursive=False)
        save_files = [destination_path(str(file)) for file in parquet_files]
        for file, save_to in zip(parquet_files, save_files):
            format_dataset_to_gpt_nl_standard(file_path=file, dest_path=save_to)

    print("Formatting completed successfully.")
