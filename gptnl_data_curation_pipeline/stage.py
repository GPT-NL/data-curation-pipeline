import dataclasses
import os
import shutil
from collections import OrderedDict
from enum import Enum
from pathlib import Path
from shutil import copyfile

import yaml
from datatrove.data import Document
from datatrove.executor.base import PipelineStep
from datatrove.executor.local import LocalPipelineExecutor
from datatrove.executor.slurm import SlurmPipelineExecutor
from datatrove.pipeline.readers import ParquetReader
from datatrove.pipeline.writers.parquet import ParquetWriter
from jsonargparse import ArgumentParser, Namespace


class ProcessingType(Enum):
    local = "local"
    hpc = "hpc"
    # Refer to sbatch arguments for the `hpc_` arguments https://slurm.schedmd.com/sbatch.html


def gptnl_parquet_writer_adapter(self, document: Document) -> dict:
    """
    A specific adapter for formatting and guaranteeing some properties of the parquet file format.

    See the code for the DiskWriter class in datatrove for more details. And within it the _default_adapter method.

    Modifications:
    - For a given filed in the document, if the value is None, or bool(value) is False, the key is included with the value None.
    - The 'text' field is always included and a None value is transformed into an empty string "".
    Args:
        document: document to format

    Returns: a dictionary to write to disk

    """
    data = dataclasses.asdict(document)
    if "text" not in data or data["text"] is None:
        data["text"] = ""
    if "extra" not in data or data["extra"] is None:
        data["extra"] = ""
    if self.expand_metadata and "metadata" in data:
        data |= data.pop("metadata")
    return data


class Stage:
    processing_type: ProcessingType
    """Type of processing: local or on the hpc."""

    input_folder: Path
    """Path to the data input directory."""

    output_folder: Path
    """Path to the data output directory."""

    logs_folder: Path
    """Path to the logs directory."""

    slurm_logs_folder: Path
    """Path to the slurm logs directory."""

    hpc_n_tasks: int
    """Total number of tasks to run on HPC (use to comply with maximum execution time limit)"""

    hpc_time: str
    """Time limit for job"""

    hpc_partition: str
    """HPC Partition to use"""

    hpc_cpus_per_task: int
    """How many CPUs for each task"""

    hpc_mem_per_cpu_gb: int
    """How much memory for each CPU"""

    hpc_gpus: int
    """How many GPUs"""

    hpc_reservation: str | None
    """Name of the slurm eservation"""

    hpc_exclude: str | None
    """Define which partition to exclude"""

    hpc_nice: int | None
    """Define adjusted scheduling priority"""

    hpc_ear: bool
    """To activate the Energy Aware Runtime (EAR) on HPC."""

    mail_type: str
    """HPC: Type of email notifications to receive (NONE, BEGIN, END, FAIL, REQUEUE, or ALL)"""

    mail_user: str | None
    """HPC: Email address to send notifications to"""

    env_commands: str
    """HPC: Additional env commands that are executed at the start of the slurm job"""

    def __init__(self):
        """Contains the modules to include in the pipeline."""
        self.active_modules: list[PipelineStep] = []
        # Base modules since each stage needs a reader and writter
        self._base_module = OrderedDict(
            {
                "ParquetReader": {
                    "cls": ParquetReader,
                    "default": dict(
                        data_folder="",  # will be overwritten later on in the setting up function
                        file_progress=True,
                        doc_progress=True,
                        glob_pattern="*.parquet",
                        # Logs may be present in a subdirectory of self.input_folder.
                        # As all input files are in the root of self.input_folder,
                        # we prevent log files being read by ParquetReader by setting recursive to False
                        recursive=False,
                        text_key="text",
                    ),
                },
                "ParquetWriter": {
                    "cls": ParquetWriter,
                    "default": dict(
                        output_folder="",
                        expand_metadata=True,
                        max_file_size=int(0.25 * 2**30),
                        adapter=gptnl_parquet_writer_adapter,
                    ),
                },
            }
        )

    def specify_cli_arguments(self, parser_subcommand: ArgumentParser):
        """This specifies the CLI arguments for every stage by defining the reader and writer.

        If the stage has more arguments than the default, override this.

        Also check https://jsonargparse.readthedocs.io/en/v4.30.0/#sub-commands
        """

        for base_module_name, base_module in self._base_module.items():
            parser_subcommand.add_class_arguments(
                base_module["cls"],
                base_module_name,
                default=base_module["default"],
                fail_untyped=False,
                skip=base_module.get("skip", None),
            )
        self._specify_cli_arguments(parser_subcommand=parser_subcommand)

    def _specify_cli_arguments(self, parser_subcommand: ArgumentParser):
        """This specifies the CLI arguments used for this stage.

        If the stage has more arguments than the default, override this.

        Also check https://jsonargparse.readthedocs.io/en/v4.30.0/#sub-commands
        """

        for module_name, module in self._modules.items():
            parser_subcommand.add_class_arguments(
                module["cls"],
                module_name,
                default=module["default"],
                fail_untyped=False,
                skip=module.get("skip", None),
            )

    def set_up_base_module(self, args: Namespace):
        for module_name, module in self._base_module.items():
            if module_name in args:
                if (
                    module_name == "ParquetReader"
                    and args[module_name].data_folder == ""
                ):
                    self.__dict__["ParquetReader.data_folder"] = args[
                        module_name
                    ].data_folder = str(self.input_folder)
                elif (
                    module_name == "ParquetWriter"
                    and args[module_name].output_folder == ""
                ):
                    self.__dict__["ParquetReader.output_folder"] = args[
                        module_name
                    ].output_folder = str(self.output_folder)

        return args

    def set_up_modules(self, args: Namespace):
        """Construct the modules"""

        args = self.set_up_base_module(args)

        # First, add the Parquet reader
        if "ParquetReader" in self._base_module:
            parquet_reader_module = self._base_module["ParquetReader"]
            self.active_modules.append(
                parquet_reader_module["cls"](
                    **vars(args.get("ParquetReader", Namespace()))
                )
            )

        # Then, add the modules from _set_up_modules
        self._set_up_modules(args)

        # Finally, add the Parquet writer
        if "ParquetWriter" in self._base_module:
            parquet_writer_module = self._base_module["ParquetWriter"]
            args["ParquetWriter"].output_folder = str(self.output_folder)
            self.active_modules.append(
                parquet_writer_module["cls"](
                    **vars(args.get("ParquetWriter", Namespace()))
                )
            )

    def _set_up_modules(self, args: Namespace):
        """Constructs the modules of each stage based on the CLI arguments used for this stage."""

        for module_name, module in self._modules.items():
            self.active_modules.append(
                module["cls"](**vars(args.get(module_name, Namespace())))
            )

    def get_stage_spec(self) -> list[PipelineStep]:
        """Returns the pipeline used by the Datatrove executor.

        The default run_stage implementation uses this, so override this if you don't
        have your own run_stage implementation.
        """
        return [
            *self.active_modules,  # Unpack the list of active modules
        ]

    def clean_output_folder(self):
        """Remove all files in the output folder.

        Call this before running the pipeline stage.
        """
        if not self.output_folder.exists():
            return
        shutil.rmtree(str(self.output_folder))

    def run_stage(
        self,
        job_name: str | None = None,
        pipeline_config_path: str | None = None,
        depending_slurm_jobs: SlurmPipelineExecutor | None = None,
    ) -> None | SlurmPipelineExecutor:
        stage_spec = self.get_stage_spec()
        if not os.path.exists(self.logs_folder):
            os.makedirs(self.logs_folder)
        if pipeline_config_path:
            copyfile(
                src=pipeline_config_path, dst=self.logs_folder / "pipeline_config.yaml"
            )
        with open(self.logs_folder / "stage_params.yaml", "w") as f:
            yaml.dump(vars(self), f)

        if self.processing_type == ProcessingType.local:

            executor = LocalPipelineExecutor(
                pipeline=stage_spec,
                logging_dir=str(self.logs_folder),
                workers=-1,
                tasks=1,
            )
            executor.run()
        else:
            venv_path = Path(__file__).parents[1] / "venv" / "bin" / "activate"

            if job_name is None:
                job_name = self.__class__.__name__

            sbatch_args = self.get_sbatch_args()

            executor = SlurmPipelineExecutor(
                job_name=job_name,
                pipeline=stage_spec,
                tasks=self.hpc_n_tasks,
                cpus_per_task=self.hpc_cpus_per_task,
                mem_per_cpu_gb=self.hpc_mem_per_cpu_gb,
                time=self.hpc_time,
                workers=-1,
                logging_dir=str(self.logs_folder),
                slurm_logs_folder=str(self.slurm_logs_folder),
                env_command=f"module load 2023 Python/3.11.3-GCCcore-12.3.0; "
                f"source {venv_path}; export OMP_NUM_THREADS={self.hpc_cpus_per_task}; export PYTHONFAULTHANDLER=1; "
                f"mkdir -p {self.logs_folder / 'emission'}; "
                f"{self.env_commands}",
                sbatch_args=sbatch_args,
                randomize_start_duration=3,
                partition=self.hpc_partition,
                mail_type=self.mail_type,
                mail_user=self.mail_user,
                depends=depending_slurm_jobs,
                tasks_per_job=1,
                max_array_size=30001,  # the MaxArraySize value in $ scontrol show config, default is 1k. With this we can have less and bigger job arrays
            )

            # This correction is necessary because the initialization of qos in the
            # constructor does not work (bug in DataTrove).
            executor.qos = None
            return executor

    def get_sbatch_args(self) -> dict[str, str]:
        """Define the extra sbatch arugments"""
        sbatch_args = {
            "ntasks": 1,  # necessary with datatrove<=0.4 https://github.com/huggingface/datatrove/pull/296
        }
        if self.hpc_ear:
            sbatch_args = sbatch_args | {
                "ear": "on",
                "ear-policy": "monitoring",
                "ear-verbose": 1,
                "ear-user-db": f"{self.logs_folder / 'emission' / 'ear_db'}",
            }

        if self.hpc_reservation:
            sbatch_args["reservation"] = self.hpc_reservation

        if self.hpc_gpus:
            sbatch_args["gpus"] = self.hpc_gpus

        if self.hpc_exclude:
            sbatch_args["exclude"] = self.hpc_exclude

        if self.hpc_nice:
            sbatch_args["nice"] = self.hpc_nice

        return sbatch_args
