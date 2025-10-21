"""
Creates a summary yaml file for the curation pipeline of a given dataset

Usage:
    python dataset_summary.py <file_path_or_directory>
"""

import argparse
import yaml
from pathlib import Path

from check_parquet import validate_parquet_files_in_directory


def dataset_pipeline_path(path: Path) -> Path:
    """
    Discovers and returns the root directory of the dataset pipeline.

    The pipeline directory starts with "pipeline" and does not end with "_eval".
    If there are multiple directories satisfying this condition, returns the first one found.
    """
    pipeline_dirs = [
        d
        for d in path.iterdir()
        if d.is_dir() and d.name.startswith("pipeline") and not d.name.endswith("_eval")
    ]
    if not pipeline_dirs:
        raise FileNotFoundError(f"No valid pipeline directory found in {path}")
    return pipeline_dirs[0]


def summary_pipeline_stages(pipeline_path: Path) -> dict:
    """
    Returns a dictionary of dataset pipeline stages with their paths.

    The stages are expected to be provided in the list.
    Each stage is represented as a key in the dictionary with its path set to None.
    """
    stages = [
        "data_splitting",
        "string_normalization",
        "heuristic_filtering",
        "toxic_language_detection",
        "deduplication",
        "pii_masking",
        "machine_translation",
        "llm_processing",
    ]
    _stages = {}
    for stage in stages:
        _stage = {
            "path": None,
            "all_valid_parquet_files": False,
            "invalid_files": [],
        }  # default values for each stage
        stage_dirs = [
            d for d in pipeline_path.iterdir() if d.is_dir() and stage in d.name
        ]
        stage_path = stage_dirs[0].resolve() if stage_dirs else None
        if stage_path:
            _stage["path"] = str(stage_path)
            invalid_file_list, valid_parquet_files = (
                validate_parquet_files_in_directory(
                    directory_path=stage_path, num_threads=8
                )
            )
            _stage["all_valid_parquet_files"] = valid_parquet_files
            _stage["invalid_files"] = invalid_file_list
            _stages[stage] = _stage

    return _stages


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a dataset summary YAML file.")
    parser.add_argument(
        "path", default=".", help="Path to a .parquet file or a directory"
    )
    args = parser.parse_args()

    path = Path(args.path).resolve()
    if not path.exists():
        parser.print_help()
        raise FileNotFoundError(f"The specified path does not exist: {path}")

    print(f"Creating dataset summary for: {path}")

    ds_pipeline_path = dataset_pipeline_path(path)
    ds_pipeline_stages = summary_pipeline_stages(
        pipeline_path=ds_pipeline_path,
    )

    summary = {
        "dataset_name": path.name,
        "dataset_pipeline": str(ds_pipeline_path),
        "stages": ds_pipeline_stages,
    }

    with open(path / "dataset_summary.yaml", "w") as f:
        yaml.dump(summary, f)

    print(f"Dataset summary created at: {path / 'dataset_summary.yaml'}")
