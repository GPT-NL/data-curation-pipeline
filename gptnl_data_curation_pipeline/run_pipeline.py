import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from jsonargparse import ArgumentParser, Namespace

from gptnl_data_curation_pipeline.run_stage import (
    prepare_stage,
    print_stage_details,
    run_stage_hpc,
    run_stage_local,
)
from gptnl_data_curation_pipeline.stages import stages

if TYPE_CHECKING:
    from .stage import Stage

pipeline_iteration_version_prefix = "pipeline"


def run_pipeline(opts=sys.argv[1:]):
    args, config = parse_args(opts)

    # Validate config.
    stage_count = len(config["stages"])
    for stage_details in config["stages"]:
        stage_name = stage_details.get("stage")
        if not stage_name:
            raise ValueError("Stage name cannot be empty.")
        if stage_name not in stages:
            raise ValueError(
                f"Unknown stage: {stage_name}. " f"Known stages: {list(stages.keys())}"
            )
        if not stage_details.get("output_folder") and not config.get(
            "output_folder_template"
        ):
            raise ValueError(f"Stage {stage_name} requires an output folder.")

    # Set arguments.
    config_file = args.config_file
    input_from_previous_output = config["input_from_previous_output"] or False
    output_folder_template = config["output_folder_template"]
    logs_folder = config["logs_folder"]
    slurm_logs_folder = config["slurm_logs_folder"]
    pipeline_iteration_version = get_pipeline_iteration_version(
        get_pipeline_iteration_path(output_folder_template),
        config_file.stem,
    )
    processing_type = config["processing_type"]
    mail_type = config.get("mail_type", None)
    mail_user = config.get("mail_user", None)
    hpc_ear = config.get("hpc_ear", True)
    hpc_exclude = config.get("hpc_exclude", None)
    hpc_nice = config.get("hpc_nice", None)
    skip_confirmation = args.skip_confirmation

    # Collect cmd line arguments per stage.
    stages_args = [
        [stage_details.pop("stage")]
        + [
            option
            for k, v in stage_details.items()
            for option in (f"--{k}", v)
            if option is not None and option is not True
        ]
        for stage_details in config["stages"]
    ]

    # Prepare stages.
    prepared_stages: list[tuple[str, Stage]] = []
    for i, stage_args in enumerate(stages_args):
        previous_stage = prepared_stages[-1][1] if prepared_stages else None
        stage_name = stage_args[0]
        # Set input folder as previous output folder.
        if previous_stage and input_from_previous_output:
            if "--input_folder" in stage_args:
                arg_idx = stage_args.index("--input_folder")
                stage_args[arg_idx + 1] = previous_stage.output_folder
            else:
                stage_args.append("--input_folder")
                stage_args.append(str(previous_stage.output_folder))

        # Set output folder.
        if output_folder_template and "--output_folder" not in stage_args:
            stage_args.append("--output_folder")
            stage_args.append(
                output_folder_template.format(
                    pipeline_iteration=pipeline_iteration_version,
                    stage_idx=i + 1,
                    stage_idx0=i,
                    stage_name=stage_name,
                )
            )
        output_folder = (  # Also used in the (slurm) logs folder(s), if set.
            stage_args[stage_args.index("--output_folder") + 1]
            if "--output_folder" in stage_args
            else None
        )

        # Set logs folder.
        if logs_folder and "--logs_folder" not in stage_args:
            stage_args.append("--logs_folder")
            stage_args.append(logs_folder)
            # {output_folder} is filled in later.

        # Set slurm logs folder.
        if slurm_logs_folder and "--slurm_logs_folder" not in stage_args:
            stage_args.append("--slurm_logs_folder")
            stage_args.append(slurm_logs_folder)
            # {output_folder} is filled in later.

        # Set processing type.
        if processing_type and "--processing_type" not in stage_args:
            stage_args.append("--processing_type")
            stage_args.append(processing_type)

        # Set mail_type for HPC
        if mail_type and "--mail_type" not in stage_args:
            stage_args.append("--mail_type")
            stage_args.append(mail_type)

        # Set mail_user for HPC
        if mail_user and "--mail_user" not in stage_args:
            stage_args.append("--mail_user")
            stage_args.append(mail_user)

        # Set Energy Aware Runtime
        if hpc_ear and "--hpc_ear" not in stage_args:
            stage_args.append("--hpc_ear")
            stage_args.append(hpc_ear)

        # Define if a node should be excluded
        if hpc_exclude and "--hpc_exclude" not in stage_args:
            stage_args.append("--hpc_exclude")
            stage_args.append(hpc_exclude)

        # Define if priority should be adjusted
        if hpc_nice and "--hpc_nice" not in stage_args:
            stage_args.append("--hpc_nice")
            stage_args.append(hpc_nice)

        # Check if stage requires an output folder.
        if (
            not output_folder
            and len(
                [v for v in stage_args if isinstance(v, str) and "{output_folder}" in v]
            )
            > 0
        ):
            raise ValueError(
                f"Stage {stage_args[0]} requires an output folder in one of its arguments."
            )

        # Fill values.
        filled_stage_args = [
            (
                v.format(
                    output_folder=output_folder,
                    pipeline_iteration=pipeline_iteration_version,
                    stage_idx=i + 1,
                    stage_idx0=i,
                    stage_name=stage_name,
                )
                if isinstance(v, str)
                else str(v)
            )
            for v in stage_args
        ]
        prepared_stages.append(prepare_stage(filled_stage_args))

    # Print stages details arguments.
    for i, (stage_name, stage) in enumerate(prepared_stages):
        print(f"Pipeline stage {i + 1} of {stage_count}")
        print_stage_details(stage, stage_name)
    print("")

    # Ask for confirmation.
    if not skip_confirmation:
        confirmation = input("Do you want to run this pipeline? [y]/n ")
        if confirmation not in ("y", ""):
            print("Pipeline cancelled.")
            return

    if processing_type == "local":
        for i, (stage_name, stage) in enumerate(prepared_stages):
            print(f"Running pipeline stage {i + 1} of {stage_count}")
            print_stage_details(stage, stage_name)
            run_stage_local(stage, stage_name, pipeline_config_path=args.config_file)
    elif processing_type == "hpc":
        run_stage_hpc(prepared_stages, pipeline_config_path=args.config_file)


def get_pipeline_iteration_path(folder_template: str) -> str:
    folder_template_path = Path(folder_template)
    pipeline_iteration_path = Path()
    for path_part in folder_template_path.parts:
        if "{pipeline_iteration}" in str(path_part):
            return pipeline_iteration_path
        pipeline_iteration_path = pipeline_iteration_path / path_part
    return None


def get_pipeline_iteration_version(path: Path | None, tag: str) -> str:
    return (
        f"{pipeline_iteration_version_prefix}{get_run_instance(path)}"
        f"_{tag}_{get_last_commit_hash_short()}"
    )


def get_run_instance(path: Path | None) -> str:
    if not path:
        return "00000"
    # Get last pipeline run instance.
    files = sorted(path.glob(f"{pipeline_iteration_version_prefix}*"))
    last_file = files[-1] if files else None
    if not last_file:
        return "00000"

    # Get 5 digits after 'pipeline' from the filename.
    last_run_inst_indx = last_file.name[
        len(pipeline_iteration_version_prefix) : len(pipeline_iteration_version_prefix)
        + 5
    ]
    return str(int(last_run_inst_indx) + 1).zfill(5)


def get_last_commit_hash_short():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()[0:7]
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return None


def parse_args(opts: list[str]) -> tuple[Namespace, dict]:
    parser = ArgumentParser(
        prog="pipeline",
        description="Runs a data curation pipeline.",
    )

    # Add arguments.
    parser.add_argument("config_file", type=Path, help="Path to the config file.")
    parser.add_argument(
        "-s", "--skip-confirmation", action="store_true", help="Skip confirmation."
    )

    # Parse arguments.
    args = parser.parse_args(opts)
    config_file = args.config_file

    # Read config file.
    if not config_file.exists():
        raise ValueError(f"Config file {config_file} does not exist.")
    with Path.open(config_file) as f:
        return (args, yaml.safe_load(f))


if __name__ == "__main__":
    run_pipeline()
