import argparse
import sys
import os
import json
import yaml
import pyarrow.parquet as pq
from pathlib import Path
from parquet_utils import parquet_files_in


CROISSANT_CONTEXT = {
    "@vocab": "https://schema.org/",
    "cr": "http://mlcommons.org/schema/croissant#",
    "sc": "https://schema.org/",
}

COLUMN_DESCRIPTIONS = {
    "id": "Unique identifier for the dataset.",
    "title": "Title of the source document, article, or text, from which the text is extracted.",
    "text": "The main text content of the document.",
    "source": "Source of the text, such as a book, url, newspaper, report, etc.",
    "author": "Author of the source document.",
    "license": "License under which the dataset is released.",
    "dataset_name": "Name of the dataset.",
    "dataset_url": "URL of the source dataset.",
    "language": "Language of the text content. Automatically detected -- may not be accurate.",
    "language_score": "Confidence score of the language detection.",
    "n_char": "Number of characters in the text entry (row).",
    "n_non_symbol_words": "Number of non-symbol words in the text entry (row).",
    "avg_word_length": "Average length of words in the text entry (row).",
}


def prompt_user(label, default=None):
    prompt = f"{label}" + (f" [{default}]" if default else "") + ": "
    response = input(prompt)
    return response.strip() if response.strip() else default


def _map_pyarrow_type_to_croissant(pa_type):
    if pa_type == "string":
        return "sc:Text"
    if pa_type in ["int32", "int64"]:
        return "sc:Integer"
    if pa_type in ["float", "double"]:
        return "sc:Float"
    if pa_type == "boolean":
        return "sc:Boolean"
    if pa_type.startswith("timestamp"):
        return "sc:DateTime"
    if pa_type.startswith("list"):
        return "list<element: string>"
    if pa_type.startswith("struct"):
        return "struct"
    return "sc:Text"


def init_croissant_metadata(
    parquet_path,
    dataset_name,
    dataset_license,
    dataset_url,
    dataset_description,
    file_id,
):
    """Initialize the Croissant metadata structure.
    Args:
        parquet_path (Path): Path to the input Parquet file.
        dataset_name (str): Name of the dataset.
        dataset_license (str): License of the dataset.
        dataset_url (str): URL of the dataset.
        dataset_description (str): Description of the dataset.
        file_id (str): Identifier for the file in the metadata.
    Returns:
        dict: A dictionary representing an initial Croissant metadata.  Dict should be
        extended further with field content.
    """
    metadata = {
        "@context": CROISSANT_CONTEXT,
        "@type": "sc:Dataset",
        "name": dataset_name,
        "description": dataset_description,
        "license": dataset_license,
        "url": dataset_url,
        "conformsTo": "http://mlcommons.org/croissant/1.0",
        "distribution": [
            {
                "@type": "cr:FileObject",
                "@id": file_id,
                "contentUrl": parquet_path.name,
                "encodingFormat": "application/parquet",
            }
        ],
        "recordSet": [
            {
                "@type": "cr:RecordSet",
                "name": "default",
                "description": "Records extracted from the input Parquet file.",
                "field": [],
            }
        ],
    }

    return metadata


def update_croissant_metadata(col_names, col_types, file_id, metadata):
    """Update the Croissant metadata with fields based on the Parquet schema.
    Args:
        col_names (list[str]): List of column names in the Parquet file.
        col_types (list[pyarrow.DataType]): List of column types in the Parquet file.
        file_id (str): Identifier for the file in the metadata.
        metadata (dict): The Croissant metadata dictionary to be updated.

        The metadata dictionary is updated with fields extracted from the Parquet schema.
    """
    for name, pa_type in zip(col_names, col_types):
        croissant_type = _map_pyarrow_type_to_croissant(str(pa_type))
        description = COLUMN_DESCRIPTIONS.get(
            name, f"Field extracted from column '{name}'"
        )
        if name == "PII":
            croissant_type = (
                "struct<entity_type_counts: list<element: null>, entity_types: list<element: null>, "
                "not_removed_entities: list<element: null>, not_removed_entity_counts: list<element: null>, "
                "processed_entities: list<element: null>, processed_entity_counts: list<element: null>>"
            )
            description = "Details about Personally Identifiable Information (PII) detected in the text."
        elif name == "ToxicLanguage":
            croissant_type = "list<element: struct<label: string, score: double, sentence: string, start_index: int64>>"
            description = "Details about toxic language detected in the text."

        field = {
            "@type": "cr:Field",
            "name": name,
            "description": description,
            "dataType": croissant_type,
            "source": {"fileObject": {"@id": file_id}, "extract": {"column": name}},
        }

        metadata["recordSet"][0]["field"].append(field)


def _make_parser():
    """Create an argument parser for the script."""
    _SCRIPT_DESCRIPTION = "Produces a Croissant metadata file from a Parquet dataset."
    parser = argparse.ArgumentParser(description=_SCRIPT_DESCRIPTION)
    parser.add_argument(
        "dataset_dir",
        type=str,
        help="Path to a dataset(collection folder) that exemplifies the dataset file. We assume the file is representative in its structure and metadata to all the files in the dataset.",
    )
    return parser


def main():
    parser = _make_parser()
    args = parser.parse_args()

    if not args.dataset_dir:
        print("Dataset directory is required.")
        sys.exit(1)

    dataset_dir = Path(args.dataset_dir).resolve()
    parquet_files = parquet_files_in(dataset_dir, recursive=False)
    if not parquet_files:
        print(f"No parquet files found in the directory: {dataset_dir}")
        sys.exit(0)

    parquet_files.sort()
    parquet_path = parquet_files[0]  # Use the first file to extract structure

    if not parquet_path.exists() or not parquet_path.is_file():
        print(f"File not found: {parquet_path}")
        sys.exit(1)

    schema = pq.read_schema(parquet_path, memory_map=True)
    col_names = schema.names
    col_types = schema.types

    table = pq.read_table(parquet_path, columns=col_names)
    df_sample = table.to_pandas().head(3)

    def get_value(col):
        return (
            df_sample[col][0]
            if col in df_sample and df_sample[col].notna().any()
            else None
        )

    dataset_name = get_value("dataset_name") or prompt_user(
        "Enter dataset name", default=parquet_path.stem
    )
    dataset_license = get_value("dataset_license") or prompt_user(
        "Enter dataset license"
    )
    dataset_url = get_value("dataset_url") or prompt_user("Enter dataset URL")
    dataset_author = get_value("author") or prompt_user("Enter dataset author")
    dataset_description = prompt_user("Enter a short description of the dataset")

    file_id = "input_parquet"

    metadata = init_croissant_metadata(
        parquet_path,
        dataset_name,
        dataset_license,
        dataset_url,
        dataset_description,
        file_id,
    )

    update_croissant_metadata(col_names, col_types, file_id, metadata)

    base = parquet_path.stem
    out_json = f"{base}_croissant.jsonld"
    out_yaml = f"{base}_croissant.yaml"

    with open(out_json, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved: {out_json}")

    with open(out_yaml, "w") as f:
        yaml.safe_dump(metadata, f, sort_keys=False)
    print(f"Saved: {out_yaml}")


if __name__ == "__main__":
    main()
