from datatrove.data import DocumentsPipeline
from datatrove.pipeline.base import PipelineStep
from datatrove.pipeline.readers import ParquetReader
from datatrove.pipeline.writers.parquet import ParquetWriter
from datatrove.utils.typeshelper import StatHints
from jsonargparse import ArgumentParser, Namespace
from tqdm import tqdm

from gptnl_data_curation_pipeline.stage import Stage, gptnl_parquet_writer_adapter


class DataSplittingStage(Stage):
    """Splits all parquet files in a directory into smaller parquet files.

    You can split the input files by specifying the maximum file size of each output file (`max_file_size`).
    Keep in mind that the file size is checked before writing a new batch of rows in the `ParquetWriter`,
    so your `max_file_size` is not a hard constraint. If you notice that the files are significantly bigger
    than the target size, try reducing the `batch_size`: this will write more frequently to the output file
    so that the output files will be more aligned with the target `max_file_size`.

    If the input rows are very long, you can additionally split them into shorter ones by using the
    `batch_size` parameter (in combination with the optional `line_chunk_size`).

    #### File size margin computation
    Since every char of text occupies 1B (neglecting metadata) you can compute how much a file can be bigger
    than the provided `max_file_size` by multiplying `line_length * max_file_size * batch_size`.

    Examples:
    - `line_length=100_000`: let's assume all the rows are long 100k characters
    - `max_file_size=20*(2**20)`: 20MB
    - `batch_size=50`: how frequently to write to disk

    In this case, the potential file size can exceed the `max_file_size` by a margin of 5MB (50 * 100kB),
    resulting in files of size 25MB

    #### Splitting long rows

    If you set the `line_chunk_size`, this stage will split lines according to `line_chunk_size` (simple
    string chunking, can truncate words at the extremes).
    This will impact the `line_length` and reduce your file size margins.

    If you don't want to split the rows, set `line_chunk_size=None` and the output file will only be splitted
    row-wise to get the desired file size.
    """

    line_chunk_size: int | None
    """Number of characters to split the input rows into shorter rows. If None, no splitting of rows is done."""

    max_file_size: int
    """Target file size."""

    batch_size: int
    """How frequently to write to disk (and check file size, afecting file size margin)."""

    def _specify_cli_arguments(self, parser_subcommand: ArgumentParser):
        """Specify CLI arguments.

        Args:
            parser_subcommand (ArgumentParser): the parser for the subcommand.
        """
        parser_subcommand.add_argument(
            "--line_chunk_size",
            default=None,
            type=int | None,
            help="Number of characters to split the input rows into shorter rows. If None, no splitting of rows is done.",
        )
        parser_subcommand.add_argument(
            "--max_file_size",
            default=100_000_000,
            type=int,
            help="Target file size.",
        )
        parser_subcommand.add_argument(
            "--batch_size",
            default=50,
            type=int,
            help="How frequently to write to disk (and check file size, afecting file size margin).",
        )

    def _set_up_modules(self, args: Namespace):
        """Constructs the modules of each stage based on the CLI arguments used for this stage."""
        pass

    def get_stage_spec(self):
        reader = ParquetReader(
            data_folder=str(self.input_folder),
            file_progress=True,
            doc_progress=True,
            # Logs may be present in  a subdirectory of self.input_folder.
            # As all input files are in the root of self.input_folder,
            # we prevent log files being read by ParquetReader by setting recursive to False
            recursive=False,
            glob_pattern="*.parquet",
            text_key="text",
            id_key="extraction_uid",
        )
        writer = ParquetWriter(
            output_folder=str(self.output_folder),
            max_file_size=self.max_file_size,
            batch_size=self.batch_size,
            expand_metadata=True,
            adapter=gptnl_parquet_writer_adapter,
        )

        if self.line_chunk_size is not None:
            return [
                reader,
                TextChunkerStep(chunk_size=self.line_chunk_size),
                writer,
            ]
        else:
            return [
                reader,
                writer,
            ]


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


class TextChunkerStep(PipelineStep):
    type = "splitter"
    name = "text chunk splitter"

    def __init__(self, chunk_size: int):
        self.chunk_size = chunk_size
        super().__init__()

    def run(
        self, data: DocumentsPipeline, rank: int = 0, world_size: int = 1
    ) -> DocumentsPipeline:
        for i, doc in enumerate(tqdm(data, desc="chunking")):
            self.stat_update(StatHints.total)
            with self.track_time():
                text = doc.text
                text_splitted = chunks(text, self.chunk_size)
                for t in text_splitted:
                    doc.text = t
                    self.stat_update(StatHints.forwarded)
                    yield doc
