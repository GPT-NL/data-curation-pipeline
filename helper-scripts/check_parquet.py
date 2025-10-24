"""
Parquet File Validation Script This script validates Parquet files in a specified
directory or checks a single Parquet file. Usage:
    python validate_parquet.py <file_path_or_directory>
"""

import pyarrow.parquet as pq
import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

# Configure logging
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.terminator = "\r"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[stream_handler],
)


def is_parquet_valid(file_path) -> tuple[str, bool]:
    """
    Validate a single Parquet file."""
    try:
        pq.ParquetFile(file_path)
        logging.info(f"Valid Parquet file: {file_path}")
        return (file_path, True)
    except Exception as e:
        logging.error(f"Invalid Parquet file: {file_path} | Error: {e}")
        return (file_path, False)


def validate_parquet_files_in_directory(
    directory_path, num_threads=8
) -> tuple[list[str], bool]:
    """
    Validate all Parquet files in a directory using multithreading."""
    invalid_files = []
    parquet_files = [
        os.path.join(root, name)
        for root, _, files in os.walk(directory_path)
        for name in files
        if name.endswith(".parquet")
    ]

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(is_parquet_valid, fp): fp for fp in parquet_files}
        for future in as_completed(futures):
            file_path, valid = future.result()
            if not valid:
                invalid_files.append(file_path)

    all_parquet_files_valid = len(invalid_files) == 0
    return (invalid_files, all_parquet_files_valid)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Parquet files.")
    parser.add_argument(
        "path", default=".", help="Path to a .parquet file or a directory"
    )
    parser.add_argument(
        "--threads", type=int, default=8, help="Number of threads to use (default: 8)"
    )
    args = parser.parse_args()

    path = args.path
    num_threads = args.threads

    if os.path.isfile(path):
        _, valid = is_parquet_valid(path)
        if valid:
            logging.info("Parquet file is valid.")
        else:
            logging.warning("Parquet file is invalid.")
    elif os.path.isdir(path):
        invalids, _ = validate_parquet_files_in_directory(path, num_threads)
        output_file = "ALL_PARQUET_FILES_VALID"
        if invalids:
            output_file = "invalid_parquet_files.json"

        with open(output_file, "w") as f:
            if invalids:
                json.dump(invalids, f, indent=2)
                logging.info(
                    f"\nValidation complete. Invalid files saved to: {output_file}"
                )
            else:
                logging.info("\nAll Parquet files are valid.")
    else:
        logging.error("Provided path is neither a file nor a directory.")
