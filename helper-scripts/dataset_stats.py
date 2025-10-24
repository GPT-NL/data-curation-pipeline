from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import sys
import argparse
import yaml

from parquet_utils import parquet_files_in, read_parquet_file, parquet_file_info

WORDS_COUNT_COLUMN = "n_non_symbol_words"
CHARS_COUNT_COLUMN = "n_char"
LANGUAGE_SCORE_COLUMN = "language_score"
LANGUAGE_COLUMN = "language"
LICENSE_COLUMN = "license"
AVG_WORD_LENGTH_COLUMN = "avg_word_length"


def dataset_stats(data_table: pa.Table) -> pd.DataFrame:
    """Collect statistics for the dataset represented by the given pyarrow Table.

    Args:
        data_table (pa.Table): The dataset as a pyarrow Table.

    Returns:
        pd.DataFrame: A DataFrame containing the statistics of the dataset.
    """
    stats = {
        "n_rows": data_table.num_rows,
        "n_columns": len(data_table.column_names),
        "columns": data_table.column_names,
        ## collect the unique values of column "license"
        "licenses": data_table[LICENSE_COLUMN].unique().to_pylist(),
        "column_types": [
            str(data_table.schema.field(i).type) for i in range(len(data_table.schema))
        ],
        "text_stats": collect_column_stats(
            column_name=WORDS_COUNT_COLUMN, data_table=data_table
        ),
        "char_stats": collect_column_stats(
            column_name=CHARS_COUNT_COLUMN, data_table=data_table
        ),
        "word_average_length_stats": collect_column_stats(
            column_name=AVG_WORD_LENGTH_COLUMN, data_table=data_table
        ),
        "language_score_stats": collect_language_stats(data_table),
    }
    return stats


def collect_language_stats(data_table: pa.Table) -> list[str]:
    """Collect unique languages from the dataset.

    Args:
        data_table (pa.Table): The dataset as a pyarrow Table.

    Returns:
        List[str]: A list of unique languages found in the dataset.
    """
    lang_stats = data_table.group_by(LANGUAGE_COLUMN).aggregate(
        [
            (LANGUAGE_COLUMN, "count"),
            (WORDS_COUNT_COLUMN, "sum"),
            (WORDS_COUNT_COLUMN, "mean"),
            (WORDS_COUNT_COLUMN, "min"),
            (WORDS_COUNT_COLUMN, "max"),
            (WORDS_COUNT_COLUMN, "stddev"),
            (CHARS_COUNT_COLUMN, "sum"),
            (CHARS_COUNT_COLUMN, "mean"),
            (CHARS_COUNT_COLUMN, "min"),
            (CHARS_COUNT_COLUMN, "max"),
            (CHARS_COUNT_COLUMN, "stddev"),
            (LANGUAGE_SCORE_COLUMN, "mean"),
            (LANGUAGE_SCORE_COLUMN, "min"),
            (LANGUAGE_SCORE_COLUMN, "max"),
            (LANGUAGE_SCORE_COLUMN, "stddev"),
            (AVG_WORD_LENGTH_COLUMN, "mean"),
            (AVG_WORD_LENGTH_COLUMN, "stddev"),
        ]
    )

    return lang_stats.to_pydict()


def collect_column_stats(column_name: str, data_table: pa.Table) -> dict:
    """Collect text statistics from the dataset.

    Args:
        column_name (str): The name of the column to collect statistics from.
        data_table (pa.Table): The dataset as a pyarrow Table.

    Returns:
        dict: A dictionary containing text statistics.
    """
    text_stats = {}
    try:
        n_words_column = column(column_name, data_table)
    except ValueError:
        return text_stats

    text_stats["total"] = aggregate(n_words_column, pc.sum)
    text_stats["mean"] = aggregate(n_words_column, pc.mean)
    text_stats["min"] = aggregate(n_words_column, pc.min)
    text_stats["max"] = aggregate(n_words_column, pc.max)
    text_stats["std"] = aggregate(n_words_column, pc.stddev)

    return text_stats


def column(column_name: str, data_table: pa.Table) -> pa.Array | pa.ChunkedArray:
    """Get a column from the dataset as a pyarrow Array or ChunkedArray.

    Args:
        column_name (str): The name of the column to retrieve.
        data_table (pa.Table): The dataset as a pyarrow Table.

    Returns:
        pa.Array | pa.ChunkedArray: The requested column.
    """
    if column_name in data_table.column_names:
        return data_table.column(column_name)
    else:
        raise ValueError(f"Column '{column_name}' not found in the dataset.")


def aggregate(column: pa.Array | pa.ChunkedArray, agg_function: callable) -> float:
    """Aggregate a column in the dataset using the specified aggregation function.

    Internal utility function to avoid code duplication.
    """
    return agg_function(column).as_py()


def gpt_nl_parquet_stats(parquet_file: Path) -> dict:
    stats = parquet_file_info(parquet_file)
    data_table: pa.Table = read_parquet_file(parquet_file)
    stats["stats"] = dataset_stats(data_table)
    return stats


def gpt_nl_dataset_stats(parquet_files: list[Path]) -> list[dict]:
    """Collect statistics for each parquet file in the dataset.
    Args:
        parquet_files (list[Path]): A list of Paths to parquet files.
    Returns:
        list[dict]: A list of dictionaries containing statistics for each parquet file.
        Returns an empty list if no parquet files are found.
    """

    if not parquet_files:
        return list()

    stats_list = []
    for file_path in parquet_files:
        stats_list.append(gpt_nl_parquet_stats(file_path))

    return stats_list


def _make_parser():
    """Create an argument parser for the script."""
    _SCRIPT_DESCRIPTION = "Collect statistics for each parquet file in the dataset"
    parser = argparse.ArgumentParser(description=_SCRIPT_DESCRIPTION)
    parser.add_argument(
        "dataset_dir",
        type=str,
        help="Path to the dataset folder. We assume the folder is populated with .parquet files with a table structure defined in the GPT-NL dataset standard format.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Prints all the statistics for each parquet file in the dataset to the console.",
    )
    parser.add_argument(
        "--sample",
        "-s",
        action="store_true",
        help="Prints a sample statistics file information with 3 files sampled from the dataset directory.",
    )
    return parser


if __name__ == "__main__":
    parser = _make_parser()
    args = parser.parse_args()
    dataset_dir = Path(args.dataset_dir).resolve()
    parquet_files = parquet_files_in(dataset_dir, recursive=False)
    parquet_files.sort()

    if not parquet_files:
        print(f"No parquet files found in the directory: {dataset_dir}")
        sys.exit(0)

    if args.sample:
        parquet_files = parquet_files[:3]

    stats_list = gpt_nl_dataset_stats(parquet_files)
    # Dump stats_list to a yaml file
    output_file = dataset_dir / "dataset_stats.yaml"
    with open(output_file, "w") as f:
        yaml.dump(stats_list, f, default_flow_style=False)
