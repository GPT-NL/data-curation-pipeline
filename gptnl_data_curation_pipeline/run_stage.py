import itertools
import sys
from pathlib import Path

from colorama import Fore
from jsonargparse import ArgumentParser

from .stage import ProcessingType, Stage
from .stages import stages


def handle_stage_execution(opts=sys.argv[1:]):
    (stage_name, stage) = prepare_stage(opts)
    print_stage_details(stage, stage_name)
    run_stage_local(stage, stage_name)


def prepare_stage(opts: list[str]) -> tuple[str, Stage]:
    # Parse options.
    stage_name = opts[0]
    args = parse_args(opts)
    # Create stage.
    stage: Stage = stages[args.subcommand]["inst"].__class__()

    # Set up modules first:
    for key, value in args[args.subcommand].items():
        setattr(stage, key, value)

    stage.set_up_modules(args[args.subcommand])

    return stage_name, stage


def print_stage_details(stage: Stage, stage_name: str):
    print(f"Stage {Fore.YELLOW}{stage_name}{Fore.RESET} has options:")
    max_key_length = max(len(k) for k in vars(stage))
    for k, v in vars(stage).items():
        print(f"  {k.ljust(max_key_length)}: {Fore.GREEN}{v}{Fore.RESET}")
    print("")


def run_stage_local(
    stage: Stage, job_name: str, pipeline_config_path: str | None = None
):
    stage.clean_output_folder()
    stage.run_stage(job_name=job_name, pipeline_config_path=pipeline_config_path)


def run_stage_hpc(
    prepared_stages: list[tuple[str, Stage]], pipeline_config_path: str | None = None
):
    # Loop in reverse to set the dependencies right
    executors = [None]
    for i, (stage_name, stage) in enumerate(prepared_stages):
        stage.clean_output_folder()
        executor = stage.run_stage(
            job_name=stage_name,
            depending_slurm_jobs=executors[i],
            pipeline_config_path=pipeline_config_path,
        )
        executors.append(executor)
    # Run the last executor which will cascade all the executors to the end
    executors[-1].run()


def parse_args(opts: list[str]):
    # Specify options.
    parser = ArgumentParser(
        prog="stage",
        description="Runs a data curation pipeline stage. Note that the output folders "
        "are emptied before the stage is run.",
    )
    subcommands = parser.add_subcommands()
    for stage_name, stage_details in stages.items():
        parser_subcomm = ArgumentParser()
        # Same for every subcommand:
        parser_subcomm.add_argument(
            "-p",
            "--processing_type",
            default=ProcessingType.local,
            type=ProcessingType,
            help="Type of processing",
        )
        # Set the emailing instructions.
        parser_subcomm.add_argument(
            "-mt",
            "--mail_type",
            type=str,
            default="ALL",
            choices=["NONE", "BEGIN", "END", "FAIL", "REQUEUE", "ALL"],
            help="Type of email notifications to receive",
        )
        parser_subcomm.add_argument(
            "-u",
            "--mail_user",
            type=str,
            default=None,
            help="Email address to send notifications to",
        )

        parser_subcomm.add_argument(
            "--env_commands",
            default="",
            type=str,
            help="Additional env commands that are ran at start up of the node",
        )

        parser_subcomm.add_argument(
            "--hpc_ear",
            type=bool,
            help="Activate EAR to monitor energy and performance of HPC nodes",
        )

        parser_subcomm.add_argument(
            "--hpc_exclude",
            type=str,
            help="Define which nodes within a partition to exclude on the hpc",
        )
        parser_subcomm.add_argument(
            "--hpc_nice",
            type=int | None,
            default=None,
            help="Define adjusted scheduling priority",
        )
        # Different default for each subcommand:
        parser_subcomm.add_argument(
            "-l",
            "--logs_folder",
            default=stage_details["default_logs_folder"],
            type=Path,
            help="Path to the logs directory.",
        )
        # Same for every subcommand:
        parser_subcomm.add_argument(
            "-s",
            "--slurm_logs_folder",
            default="logs/slurm_logs",
            type=Path,
            help="Path to the slurm logs directory.",
        )
        # Different default for each subcommand:
        parser_subcomm.add_argument(
            "-i",
            "--input_folder",
            default=stage_details["default_input_folder"],
            type=Path,
            help="Path to the data input directory.",
        )
        # Different default for each subcommand:
        parser_subcomm.add_argument(
            "-o",
            "--output_folder",
            default=stage_details["default_output_folder"],
            type=Path,
            help="Path to the data output directory. Emptied before every stage run.",
        )
        parser_subcomm.add_argument(
            "--hpc_n_tasks",
            default=32,
            type=int,
            help="Total number of tasks to run on HPC (use to comply with maximum execution time limit)",
        )
        parser_subcomm.add_argument(
            "--hpc_time",
            default="00:10:00",
            type=str,
            help="Time limit for job",
        )
        parser_subcomm.add_argument(
            "--hpc_partition",
            default="genoa",
            type=str,
            help="HPC Partition to use",
        )
        parser_subcomm.add_argument(
            "--hpc_cpus_per_task",
            default=1,
            type=int,
            help="How many CPUs for each task",
        )
        parser_subcomm.add_argument(
            "--hpc_mem_per_cpu_gb",
            default=2,
            type=int,
            help="How much memory for each CPU",
        )
        parser_subcomm.add_argument(
            "--hpc_gpus",
            default=None,
            type=int | None,
            help="How many GPUs",
        )
        parser_subcomm.add_argument(
            "--hpc_reservation",
            default=None,
            type=str | None,
            help="Name of the slurm reservation (if present)",
        )
        stage_details["inst"].specify_cli_arguments(parser_subcomm)
        subcommands.add_subcommand(stage_name, parser_subcomm)

    return parser.parse_args(opts)


if __name__ == "__main__":
    handle_stage_execution(sys.argv[1:])
