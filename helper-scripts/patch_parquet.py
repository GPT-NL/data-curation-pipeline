"""This script patches one or more parquet files in a dataset, applying some fixes to
the `text` column.

Use conscioulsy!
"""

from pathlib import Path
import argparse
from parquet_utils import (
    apply_patches_to_parquet_files,
    parquet_files_in,
)
import pyarrow.compute as pc


## Run this only to make tests
def _test_eliminate_whitespaces_around_newline(text_column):
    """Eliminate whitespaces around newlines in the text column."""
    a = pc.match_substring_regex(text_column, pattern=" \n ").to_pandas()
    b = text_column.to_pandas()
    print(b[a])
    patched = pc.replace_substring_regex(
        text_column, pattern=" \n +", replacement=" \n"
    )
    pattern_in_patched = pc.match_substring_regex(patched, pattern=" \n ").to_pandas()
    b = text_column.to_pandas()
    print(b[pattern_in_patched])
    return patched


def _eliminate_whitespaces_around_newline(text_column):
    """Eliminate whitespaces around newlines in the text column."""
    return pc.replace_substring_regex(text_column, pattern=" \n +", replacement=" \n")


def make_parser():
    """Create an argument parser for the script."""
    parser = argparse.ArgumentParser(
        description="Patches the text column in the given gpt-nl parquet files."
    )
    parser.add_argument(
        "input_file_or_dir",
        type=str,
        help="Input .parquet file or directory containing parquet files.  It is assumed that all .parquet files in the directory are in the gpt-nl format.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose output on every modification.",
    )
    return parser


def main():
    parser = make_parser()
    args = parser.parse_args()
    input_file_or_dir = Path(args.input_file_or_dir).resolve()

    if input_file_or_dir.exists() and input_file_or_dir.is_file():
        parquet_files = [input_file_or_dir]
    elif input_file_or_dir.exists() and input_file_or_dir.is_dir():
        parquet_files = parquet_files_in(Path(input_file_or_dir))
    else:
        raise ValueError(
            f"Input path {input_file_or_dir} is neither a file nor a directory."
        )

    if not parquet_files:
        print(f"No parquet files found in the input: {input_file_or_dir}")
        return

    # Sort files to maintain order
    parquet_files.sort()
    apply_patches_to_parquet_files(
        parquet_files,
        patches=(_eliminate_whitespaces_around_newline,),
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
