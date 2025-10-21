import os
import shutil
from collections import OrderedDict
from pathlib import Path
from shutil import copyfile

import yaml
from datatrove.executor.slurm import SlurmPipelineExecutor
from datatrove.pipeline.dedup.minhash import (
    MinhashConfig,
    MinhashDedupBuckets,
    MinhashDedupCluster,
    MinhashDedupFilter,
    MinhashDedupSignature,
)
from datatrove.pipeline.readers import ParquetReader
from datatrove.pipeline.writers.parquet import ParquetWriter
from datatrove.utils.hashing import HashConfig
from jsonargparse import ArgumentParser, Namespace

from gptnl_data_curation_pipeline.stage import ProcessingType, Stage


class DeduplicationStage(Stage):

    bit_precision: int
    """Whether to use 64-bit hashes for the Minhash config. Better precision means
    fewer false positives (collisions)."""

    def __init__(self):
        """Initialize the pipeline stage.

        Args:
            default_intermediate_folder (str, optional): default folder to use for
            intermediate results. Defaults to "".
        """
        super().__init__()

        self._modules = OrderedDict(
            {
                "MinhashConfig": {
                    "cls": MinhashConfig,
                    "default": {
                        "num_buckets": 14,
                        "hashes_per_bucket": 8,
                        "n_grams": 5,
                    },
                }
            }
        )

    def _specify_cli_arguments(self, parser_subcommand: ArgumentParser):
        """Specify CLI arguments.

        Args:
            parser_subcommand (ArgumentParser): the parser for the subcommand.
        """
        super()._specify_cli_arguments(parser_subcommand)

        parser_subcommand.add_argument(
            "--bit_precision",
            type=int,
            default=64,
            help="Whether to use 64-bit hashes for the Minhash config. Better "
            "precision means fewer false positives (collisions).",
            choices=[32, 64],
        )

    def _set_up_modules(self, args: Namespace):
        """Constructs the modules of each stage based on the CLI arguments used for this stage."""
        for module_name, module in self._modules.items():
            if module_name in args:

                if module_name == "MinhashConfig":
                    args[module_name].hash_config = HashConfig(
                        precision=self.bit_precision
                    )
                    self.minhash_config = module["cls"](
                        **vars(
                            args[module_name],
                        ),
                    )

    def run_stage(
        self,
        job_name=None,
        pipeline_config_path: str | None = None,
        depending_slurm_jobs: SlurmPipelineExecutor | None = None,
    ) -> SlurmPipelineExecutor | NotImplementedError:
        if not os.path.exists(self.logs_folder):
            os.makedirs(self.logs_folder)
        if pipeline_config_path:
            copyfile(
                src=pipeline_config_path, dst=self.logs_folder / "pipeline_config.yaml"
            )
        with open(self.logs_folder / "stage_params.yaml", "w") as f:
            yaml.dump(vars(self), f)

        if self.processing_type == ProcessingType.local:
            raise NotImplementedError(
                "Local processing is not yet supported for this pipeline stage."
            )
        elif self.processing_type == ProcessingType.hpc:
            venv_path = Path(__file__).parents[2] / "venv" / "bin" / "activate"

            sbatch_args = self.get_sbatch_args()

            # stage 1 computes minhash signatures for each task (each task gets a set of
            # files)
            executor_1 = SlurmPipelineExecutor(
                job_name="signature",
                pipeline=[
                    ParquetReader(
                        data_folder=str(self.input_folder),
                        file_progress=True,
                        doc_progress=True,
                        # Logs may be present in  a subdirectory of self.input_folder.
                        # As all input files are in the root of self.input_folder,
                        # we prevent log files being read by ParquetReader by setting recursive to False
                        recursive=False,
                        text_key="text",
                    ),
                    MinhashDedupSignature(
                        output_folder=str(
                            self.output_folder / "intermediate" / "signatures"
                        ),
                        config=self.minhash_config,
                    ),
                ],
                tasks=self.hpc_n_tasks,
                time=self.hpc_time,
                workers=-1,
                logging_dir=str(self.logs_folder / "signatures"),
                slurm_logs_folder=str(self.slurm_logs_folder / "signatures"),
                env_command=f"module load 2023 Python/3.11.3-GCCcore-12.3.0; "
                f"source {venv_path}; export OMP_NUM_THREADS={self.hpc_cpus_per_task}; export PYTHONFAULTHANDLER=1; "
                f"{self.env_commands}",
                randomize_start_duration=3,
                mem_per_cpu_gb=self.hpc_mem_per_cpu_gb,
                cpus_per_task=self.hpc_cpus_per_task,
                partition=self.hpc_partition,
                mail_type=self.mail_type,
                mail_user=self.mail_user,
                depends=depending_slurm_jobs,
                sbatch_args=sbatch_args,
                tasks_per_job=1,
                max_array_size=30001,
            )

            executor_1.qos = None

            executor_2 = SlurmPipelineExecutor(
                job_name="buckets",
                pipeline=[
                    MinhashDedupBuckets(
                        input_folder=str(
                            self.output_folder / "intermediate" / "signatures"
                        ),
                        output_folder=str(
                            self.output_folder / "intermediate" / "buckets"
                        ),
                        config=self.minhash_config,
                    ),
                ],
                tasks=self.minhash_config.num_buckets,
                time=self.hpc_time,
                logging_dir=str(self.logs_folder / "buckets"),
                depends=executor_1,
                slurm_logs_folder=str(self.slurm_logs_folder / "buckets"),
                env_command=f"module load 2023 Python/3.11.3-GCCcore-12.3.0; "
                f"source {venv_path}; export OMP_NUM_THREADS={self.hpc_cpus_per_task}; export PYTHONFAULTHANDLER=1; "
                f"{self.env_commands}",
                workers=-1,
                randomize_start_duration=3,
                mem_per_cpu_gb=self.hpc_mem_per_cpu_gb,
                cpus_per_task=self.hpc_cpus_per_task,
                partition=self.hpc_partition,
                mail_type=self.mail_type,
                mail_user=self.mail_user,
                sbatch_args=sbatch_args,
                tasks_per_job=1,
                max_array_size=30001,
            )

            executor_2.qos = None

            # stage 3 creates clusters of duplicates using the results from all buckets
            executor_3 = SlurmPipelineExecutor(
                job_name="cluster",
                pipeline=[
                    MinhashDedupCluster(
                        input_folder=str(
                            self.output_folder / "intermediate" / "buckets"
                        ),
                        output_folder=str(
                            self.output_folder / "intermediate" / "remove_ids"
                        ),
                        config=self.minhash_config,
                    ),
                ],
                tasks=1,
                time=self.hpc_time,
                logging_dir=str(self.logs_folder / "cluster"),
                mem_per_cpu_gb=self.hpc_mem_per_cpu_gb,
                cpus_per_task=self.hpc_cpus_per_task,
                depends=executor_2,
                slurm_logs_folder=str(self.slurm_logs_folder / "cluster"),
                env_command=f"module load 2023 Python/3.11.3-GCCcore-12.3.0; "
                f"source {venv_path}; export OMP_NUM_THREADS={self.hpc_cpus_per_task}; export PYTHONFAULTHANDLER=1; "
                f"{self.env_commands}",
                workers=-1,
                randomize_start_duration=3,
                partition=self.hpc_partition,
                mail_type=self.mail_type,
                mail_user=self.mail_user,
                sbatch_args=sbatch_args,
                tasks_per_job=1,
                max_array_size=30001,
            )

            executor_3.qos = None

            # stage 4 reads the original input data and removes all but 1 sample per
            # duplicate cluster the data must match exactly stage 1, so number of tasks
            # and the input source must be the same
            executor_4 = SlurmPipelineExecutor(
                job_name="filter",
                pipeline=[
                    ParquetReader(
                        data_folder=str(self.input_folder),
                        file_progress=True,
                        doc_progress=True,
                        # Logs may be present in  a subdirectory of self.input_folder.
                        # As all input files are in the root of self.input_folder,
                        # we prevent log files being read by ParquetReader by setting recursive to False
                        recursive=False,
                        text_key="text",
                    ),
                    MinhashDedupFilter(
                        input_folder=str(
                            self.output_folder / "intermediate" / "remove_ids"
                        ),
                        exclusion_writer=ParquetWriter(
                            str(self.output_folder / "intermediate" / "removed"),
                            expand_metadata=True,
                            max_file_size=0.5 * 2**30,  # 500MB sizes
                        ),
                    ),
                    ParquetWriter(
                        output_folder=str(self.output_folder),
                        expand_metadata=True,
                        max_file_size=0.5 * 2**30,  # 500MB sizes
                    ),
                ],
                tasks=self.hpc_n_tasks,
                time=self.hpc_time,
                logging_dir=str(self.logs_folder / "filter"),
                depends=executor_3,
                slurm_logs_folder=str(self.slurm_logs_folder / "filter"),
                env_command=f"module load 2023 Python/3.11.3-GCCcore-12.3.0; "
                f"source {venv_path}; export OMP_NUM_THREADS={self.hpc_cpus_per_task}; export PYTHONFAULTHANDLER=1; "
                f"{self.env_commands}",
                workers=-1,
                randomize_start_duration=3,
                mem_per_cpu_gb=self.hpc_mem_per_cpu_gb,
                cpus_per_task=self.hpc_cpus_per_task,
                partition=self.hpc_partition,
                mail_type=self.mail_type,
                mail_user=self.mail_user,
                sbatch_args=sbatch_args,
                tasks_per_job=1,
                max_array_size=30001,
            )

            executor_4.qos = None

            return executor_4
