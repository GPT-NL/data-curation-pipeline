## Selection of simple utility functions for manipulating parquet files.
import hashlib
from pathlib import Path
from typing import Tuple

import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa


# Define the SET of standard columns that should be present in the GPT-NL dataset format(deliverey set).
gpt_nl_dataset_columns = {
    "id",
    "text",
    "title",
    "source",
    "author",
    "license",
    "dataset_name",
    "dataset_url",
    "language",
    "language_score",
    "n_char",
    "n_non_symbol_words",
    "avg_word_length",
}


def read_parquet_file(file_path: Path) -> pa.Table:
    """Open a parquet file and return it as a pyarrow Table.
    Args:
        file_path (Path): The path to the parquet file.
    Returns:
        pa.Table: The parquet file as a pyarrow Table.
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a valid parquet file.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    try:
        return pq.read_table(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read parquet file {file_path}: {e}")


def write_parquet_file(
    data_table: pa.Table, file_path: Path, overwrite: bool = False
) -> None:
    """Write a pyarrow Table to a parquet file.
    Args:
        data_table (pa.Table): The pyarrow Table to write.
        file_path (Path): The path to the parquet file.
        overwrite (bool): If True, overwrite the file if it exists.
    Raises:
        ValueError: If the file already exists and overwrite is False.
    """
    if not overwrite and file_path.is_file():
        raise ValueError(
            f"The file {file_path} already exists. Use overwrite=True to overwrite it."
        )

    ##file_path = file_path.parent / f"patched_{file_path.name}"
    pq.write_table(data_table, file_path)


def apply_patches_to_parquet_files(
    parquet_files: list[Path], patches: tuple[callable], verbose=False
):
    """Apply given patches to the text column in the given parquet files.

    Patches are appled in the order they are provided in the `patches` tuple.
    """
    for file_path in parquet_files:
        data_table = read_parquet_file(file_path)
        text_column = data_table.column("text")

        for patch in patches:
            if verbose:
                print(f"Applying patch {patch.__name__} to {file_path}")
            text_column = patch(text_column)

        # Update the table with the modified text column
        data_table = data_table.set_column(
            data_table.schema.get_field_index("text"), "text", text_column
        )
        write_parquet_file(data_table, file_path, overwrite=True)


def parquet_files_in(input_dir: Path, recursive: bool = False) -> list[Path]:
    """Get all parquet files in the given directory.
    Args:
        input_dir (Path): The directory to search for parquet files.
        recursive (bool): If True, search recursively in subdirectories.
    Returns:
        list[Path]: A sorted list of Paths to parquet files.
    Raises:
        ValueError: If the input_dir is not a directory.
    """
    mask = "**/*.parquet" if recursive else "*.parquet"
    parquet_files = [
        fparquet.resolve() for fparquet in input_dir.glob(mask) if fparquet.is_file()
    ]

    return parquet_files


def _gpt_nl_compliant_dataframe(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, list[str]]:
    """
    Format the DataFrame to comply with the GPT-NL dataset standard format.

    Args:
        df (pd.DataFrame): The input DataFrame to be formatted.

    Returns:
        pd.DataFrame: The formatted DataFrame with only the required columns.
        list[str]: List of columns that were missing for a full GPT-NL standard.
    """
    # Check if all required columns are present
    missing_columns = set(gpt_nl_dataset_columns) - set(df.columns)
    # Continues without the missing columns
    effective_columns = [
        col for col in gpt_nl_dataset_columns if col not in missing_columns
    ]

    # Drop columns that are not in the standard format
    return df[effective_columns]


def format_dataset_to_gpt_nl_standard(
    file_path: Path | list[Path], dest_path: Path | list[Path] = None
):
    """Format a parquet file to comply with the GPT-NL dataset standard format.
    Args:
        file_path (Path): The path to the input parquet file.
        dest_path (Path, optional): The path to save the formatted file. If None, it will overwrite the original file.
        Returns:
        Tuple[Path, list[str]]: The path to the formatted file and a list of missing columns.
    """

    def is_sequence(obj):
        return isinstance(obj, list) or isinstance(obj, tuple)

    def format_parquet_file(file_path, dest_path):
        """Helper function to format a single parquet file."""
        df = pd.read_parquet(file_path, engine="pyarrow")
        df = _gpt_nl_compliant_dataframe(df)
        df.to_parquet(dest_path, index=False, engine="pyarrow")

    dest_path = file_path if dest_path is None else dest_path

    if not (
        (is_sequence(file_path) and is_sequence(dest_path))
        or (isinstance(file_path, Path) and isinstance(dest_path, Path))
    ):
        raise ValueError(
            "file_path and dest_path must be both Path or both sequence of Path."
        )

    if isinstance(file_path, Path):
        format_parquet_file(file_path, dest_path)
        return

    ## If file_path is a sequence of Paths
    if len(file_path) != len(dest_path):
        raise ValueError(
            "file_path and dest_path must have the same length if they are sequences."
        )

    for src, dest in zip(file_path, dest_path):
        format_parquet_file(src, dest)


def parquet_sha256_hex_hash(file_path: Path) -> str:
    """Calculate the SHA-256 hash of the given file.
    Args:
        file_path (Path): The path to the file.
    Returns:
        str: The SHA-256 hash of the file as a hexadecimal string.
    """
    with open(file_path, "rb") as f:
        digest = hashlib.file_digest(f, "sha256")

    return digest.hexdigest()


def parquet_file_info(file_path: Path) -> dict:
    """Basic information about the parquet file.

    Args:
        file_path (Path): The path to the parquet file.

    Returns:
        dict: A dictionary containing the file's name, size, and hash.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    if not file_path.suffix == ".parquet":
        raise ValueError(f"The file {file_path} is not a valid parquet file.")

    file_info = {
        "filename": file_path.name,
        "size": file_path.stat().st_size,
        "file_sha256_hex_hash": parquet_sha256_hex_hash(file_path),
    }
    return file_info
