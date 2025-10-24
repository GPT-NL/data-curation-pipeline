"""
This cli python script renames all parquet files in the input directory, using the given prefix and an incrementing number as suffix.


usage: rename_parquet.py [-h] --input_dir INPUT_DIR --prefix PREFIX [--verbose]

Rename parquet files in a directory.

options:
  -h, --help            show this help message and exit
  --input_dir INPUT_DIR
                        Input directory containing parquet files.
  --prefix PREFIX       Prefix for the new file names.
  --verbose             Print verbose output.
"""

import os
import argparse
from pathlib import Path
from typing import List

from parquet_utils import parquet_files_in


def rename_parquet_files(parquet_files: List[Path], prefix: str, verbose: bool = False):
    # Rename each file with the new prefix and an incrementing number
    for i, file_path in enumerate(parquet_files):
        new_file_name = file_path.parent / f"{prefix}_{i + 1:0>4}.parquet"
        if verbose:
            print(f"Renaming {file_path} to {new_file_name}")
        file_path.rename(new_file_name)


def make_parser():
    """Create an argument parser for the script."""
    parser = argparse.ArgumentParser(description="Rename parquet files in a directory.")
    parser.add_argument(
        "--input_dir",
        type=str,
        required=True,
        help="Input directory containing parquet files.",
    )
    parser.add_argument(
        "--prefix", type=str, required=True, help="Prefix for the new file names."
    )
    parser.add_argument("--verbose", action="store_true", help="Print verbose output.")
    return parser


def main():
    parser = make_parser()
    args = parser.parse_args()
    parquet_files = parquet_files_in(Path(args.input_dir))
    # Sort files to maintain order
    parquet_files.sort()
    rename_parquet_files(parquet_files, args.prefix, args.verbose)


if __name__ == "__main__":
    main()
