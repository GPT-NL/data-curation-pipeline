<div align="center">
<h1>
<a href="https://gpt-nl.nl/" target="_blank"><img src ="https://gpt-nl.nl/publish/pages/5180/beeldmerk-gpt_nl.svg" alt="GPT-NL" widht="200"></a><br>
Data Curation Pipeline
</h1>
</div>


To improve the training of a large language model, it is crucial to have high-quality text data. Achieving higher-quality content requires applying filters and modifications to the data to remove data of bad quality (containing no proper sentences, high symbol to character ratio, high ratio of flagged words, or irrelevant languages).

The curation of the collected data follows the steps as defined in the [documentation](https://gpt-nl.ci.tno.nl/documentation/).

# Table of Contents

- [Split between pipeline and modules used in the pipeline](#split-between-pipeline-and-modules-used-in-the-pipeline)
- [Local installation](#local-installation)
- [Installation on Snellius](#installation-on-snellius)
- [Extra scripts](#extra-scripts)
- [Running a pipeline stage](#running-a-pipeline-stage)
- [Running a pipeline stage on Snellius](#running-a-pipeline-stage-on-snellius)
- [Using private modules](#using-private-modules)
- [Developing new pipeline modules](#developing-new-pipeline-modules)
- [Data](#data)
- [Pipeline stages](#pipeline-stages)
- [Visualis Carbon Footprint](#visualise-carbon-footprint)
- [Visualise Data Quality Results](#visualise-data-quality-results)

## Split between pipeline and modules used in the pipeline

This repository contains the data curation pipeline. The modules used in the pipeline are developed in [this repository](https://ci.tno.nl/gitlab/gpt-nl/dataset_creation/modules).

The reason for working this way is that we want to keep the data curation modules isolated, small and easy to use. In the pipeline, we'll want to specify which version of the module we want to use (using something like `poetry add gptnl_ftfy_formatter@0.1.0`). Putting both the pipeline and the modules in the same repository promotes local referencing, which in turn goes against the point of versioning.  
Another reason is that we'll want to open source our code, which will be made easier with this way of working. Publishing to the public PyPi index is as simple as removing `--repository tno-gptnl` from the publish command.

[This repository](https://ci.tno.nl/gitlab/gpt-nl/dataset_creation/private-pypi-index/-/packages) (with [this API link](https://ci.tno.nl/gitlab/api/v4/projects/16649/packages/pypi)) contains the private package index.

## Local installation

- If on Windows, install [Windows Subsystem for Linux](https://learn.microsoft.com/en-us/windows/wsl/install):
  - Run `wsl --install` followed by `sudo apt update` then `sudo apt install python3-pip python3-venv`
  - Switch to the directory of this repository using `cd <dir>`
- Install poetry: `pip install poetry`
- Create your virtual environment `python -m venv venv` and activate it `. venv\bin\acitvate`
- Install dependencies in the virtual environment that poetry will create: `poetry install`
- Run post install script: `poetry run python post_install.py`

Format the code **_automatically_** with [black](https://code.visualstudio.com/docs/python/formatting).

## Installation on Snellius

- Login to Snellius. If you do not know how to do this, follow [this](https://servicedesk.surf.nl/wiki/display/WIKI/Connecting+to+the+system) tutorial.
- Clone this repository using:

  ```shell
  git clone git@.../dataset_creation/pipeline.git
  ```

  Note that for this step you may need to adjust your ssh key (on Snellius).

- Run the script `init_snellius.sh` by running `cd PATH_TO_CURATION_PIPELINE_ROOT` and `. init_snellius.sh`. This script will:
  - load the necessary modules in Snellius;
  - install or update the necessary dependencies in the virtual environment handled by poetry.

## Extra scripts

Run `poetry run add_duplicates` to add duplicates. This can be used to test the deduplication stage.

Run `poetry run ruff check` to run the linter.

Format the code **_automatically_** with [black](https://code.visualstudio.com/docs/python/formatting).

## Running a pipeline stage

Run a pipeline stage using:

```shell
poetry run stage <STAGE> [STAGE_ARGS]
```

Where `<STAGE>` is the name of the stage to run, and `STAGE_ARGS` are the optional arguments passed to the pipeline stage. `<STAGE>` can be any value of `data_splitting`, `string_normalization`, `heuristic_filtering`, `pii_masking`, `deduplication` or `toxic_language_detection`. Add the `-h` option to see all options.

The following options are available for `STAGE_ARGS`. Folders are relative to the directory the command was executed from.

| Pipeline stage             | Option                               | Default                     | Description                                                                                                                             |
| -------------------------- | ------------------------------------ | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| all                        | `-p` or <br /> `--processing_type`   | `local`                     | Type of processing: `local` or `hpc`                                                                                                    |
| all                        | `-l` or <br /> `--logs_folder`       | stage-dependent             | Path to the logs directory.                                                                                                             |
| all                        | `-s` or <br /> `--slurm_logs_folder` | `logs/slurm_logs`           | Path to the slurm logs directory. Only used if `--processing_type` is `hpc`.                                                            |
| all                        | `-i` or <br /> `--input_folder`      | stage-dependent             | Path to the data input directory.                                                                                                       |
| all                        | `-o` or <br /> `--output_folder`     | stage-dependent             | Path to the data output directory.                                                                                                      |
| `data_splitting`           | `--max_file_size`                    | `100_000_000`               | Target file size.                                                                                                                       |
| `data_splitting`           | `--batch_size`                       | `50`                        | How frequently to write to disk (and check file size, afecting file size margin).                                                       |
| `data_splitting`           | `--line_chunk_size`                  | unset                       | Number of characters to split the input rows into shorter rows. If not set, no splitting of rows is done.                               |
| `string_normalization`     | `--normalization_method`             | `NFC`                       | Normalization method. One of `NFC`, `NFKC`, `NFD`, `NFKD`.                                                                              |
| `deduplication`            | `--intermediate_folder`              | `test-data/5. deduplicated` | The folder to use for intermediate results.                                                                                             |
| `deduplication`            | `--use_bit_hashes`                   | `int                        | Whether to use 64-bit or 32-bit hashes for the Minhash config.                                                                          |
| `deduplication`            | `--num_buckets`                      | `14`                        | The number of buckets to use for the Minhash config.                                                                                    |
| `deduplication`            | `--hashes_per_bucket`                | `8`                         | The number of hashes per bucket to use for the Minhash config.                                                                          |
| `deduplication`            | `--n_grams`                          | `5`                         | The number of n-grams to use for the Minhash config.                                                                                    |
| `toxic_language_detection` | `--device`                           | `-1`                        | Device ordinal for CPU/GPU supports. Setting this to `-1` will leverage CPU, `>=0` will run the model on the associated CUDA device ID. |

If the DataTrove executor says _"Not doing anything as all X tasks have already been completed."_, remove the relevant logs folder.

## Running a pipeline stage on Snellius

Before you trigger a pipeline stage, you may want to have some monitors in your environment to help you follow what is happening. Those steps are NOT obligatory, but may help when inspecting or trying out stuff. We assume you are using some multiplex terminal here, such as TMUX. That allows you to create many panes, e.g. one to run the scripts, other to edit them, other to see logs and monitors, etc. TMUX is installed in Snellius.

**Job Watch:** Create a new pane in your TMUX window. In this new pane, execute the line `watch squeue -u $USER`. That will open a monitor on all the slurm jobs you have. Leave this monitor open in this pane and switch to your execution pane.

Don't forget to run the `init_snellius.sh` script. With all in place, execute a pipeline stage with the `--processing_type hpc` option from the main directory of this repository. For example:

```bash
cd PATH_TO_CURATION_PIPELINE_ROOT
poetry run stage string_normalization --processing_type hpc
```

See the jobs span in the watch monitor. Wait for completion and enjoy the ride.

## Running a pipeline

You can run entire pipelines with the `poetry run pipeline CONFIG_FILE [--skip_confirmation|-s]` command. This accepts a configuration yaml file that contains the stages' command line arguments.

Make sure to commit the yaml files to the `pipeline-configs` directory. We want the pipeline runs to be traceable.

| Option                       | Default         | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ---------------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mail_type`                  | `All`           | Email notifications to receive when running the pipeline on HPC: `NONE`, `BEGIN`, `END`, `FAIL`, `REQUEUE`, or `ALL`. The email contains the status update of the running pipeline.                                                                                                                                                                                                                                                                                                                                     |
| `mail_user`                  | `None`          | Email address to send notifications to when running the pipeline on HPC. If the mail_user isn't set, the emails aren't sent.                                                                                                                                                                                                                                                                                                                                                                                            |
| `hpc_ear`                    | `true`          | Activate Energy Aware Runtime (EAR) system software for energy management. EAR offers energy and performance node monitoring, job accounting and energy optimization                                                                                                                                                                                                                                                                                                                                                    |
| `hpc_exclude`                | `None`          | Define which node to exclude when submitting a hpc job. For example hpc_exclude : [gcn[73-74]]                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `hpc_nice`                   | `None`          | Define adjustments to the priority of the job. For example hpc_nice : 100                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `input_from_previous_output` | `false`         | Whether to use the previous output folder as the input folder for the next stage. `input_folder` may be overwritten by a stage's configuration.                                                                                                                                                                                                                                                                                                                                                                         |
| `output_folder_template`     |                 | The output folder template that determines the output folder for every stage. May be overwritten by a stage's configuration. If not set, the stage's default value will be used. Dynamic values that can be used: <ul><li>`{pipeline_iteration}` is `pipeline {run_idx}_{yaml_filename}_{previous_commit_shorthash}` and must be the entire folder name.</li><li>`{stage_idx}` is the stage 1-based index.</li><li>`{stage_idx0}` is the stage 0-based index.</li><li>`{stage_name}` is the stage name.</li></ul>       |
| `logs_folder`                | stage-dependent | The logs folder used for any stage's Datatrove logs. May be overwritten by a stage's configuration. All substrings of `{output_folder}` will be replaced by the output folder of the stage, but only if `output_folder` is explicitly set (using the stage's `output_folder` option or using the global `output_folder_template`).                                                                                                                                                                                      |
| `slurm_logs_folder`          | stage-dependent | The slurm logs folder used for any stage's Datatrove logs. May be overwritten by a stage's configuration. All substrings of `{output_folder}` will be replaced by the output folder of the stage, but only if `output_folder` is explicitly set (using the stage's `output_folder` option or using the global `output_folder_template`).                                                                                                                                                                                |
| `stages`                     | _required_      | Array of stages. **_Don't run the same stage twice in one pipeline. This may result in unexpected behaviour._**                                                                                                                                                                                                                                                                                                                                                                                                         |
| `stages[].stage`             | _required_      | The stage name. Run `poetry run stage -h` to see the available stages. **_Don't run the same stage twice in one pipeline. This may result in unexpected behaviour._**                                                                                                                                                                                                                                                                                                                                                   |
| `stages[].*`                 |                 | The stage-dependent options. Run `poetry run stage STAGE_NAME` to see the available options per stage. Use full option names (e.g. `--input_folder` but without the `--`) instead of abbreviations (e.g. `-i`). All substrings of `{output_folder}` will be replaced by the output folder of the stage, but only if `output_folder` is explicitly set (using the stage's `output_folder` option or using the global `output_folder_template`). Other substrings are replaced as described for `output_folder_template`. |
| `stages[].processing_type`   | `local`         | Type of processing: `local` or `hpc`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `stages[].logs_folder`       | stage-dependent | Path to the logs directory.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `stages[].slurm_logs_folder` | stage-dependent | Path to the slurm logs directory. Only used if `processing_type` is `hpc`.                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `stages[].input_folder`      | stage-dependent | Path to the data input directory.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `stages[].output_folder`     | stage-dependent | Path to the data output directory.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

Example:

```yaml
input_from_previous_output: true
output_folder_template: test-data/curated/{pipeline_iteration}/{stage_idx}_{stage_name}
processing_type: local
logs_folder: "{output_folder}/logs"
slurm_logs_folder: "{output_folder}/slurm_logs"
stages:
  - stage: data_splitting
    input_folder: test-data/0. raw
  - stage: string_normalization
  - stage: deduplication
    output_folder: test-data/__. final
```

> Please have a look at [\pipeline-configs/test-run.yaml](./pipeline-configs/test-run.yaml) for more information.

## Using private modules

We use [this private package index](https://ci.tno.nl/gitlab/gpt-nl/dataset_creation/private-pypi-index/-/packages). The `poetry.toml` file contains the credentials. The `pyproject.toml` specifies the location of the private package index.

**To add dependencies** from this private package index, use `poetry add DEPENDENCY --source tno-gptnl`. For first installing this repository, `poetry install` handles everything automatically.

**To update dependencies** from this private package index after you've published an update, use `poetry add DEPENDENCY@latest --source tno-gptnl`.

❗ Note that this approach is not secure. When moving to open source, the project tokens should be invalidated and the dependencies should be moved from the private to the public PyPi index. ❗

## Developing new pipeline modules

This repository is only for creating the pipeline. For developing new modules, see [this repository](https://ci.tno.nl/gitlab/gpt-nl/dataset_creation/modules). You can publish those to our private package index, after which you can install them in this repository using [the steps above](#using-private-modules). This allows version pinning and stimulates isolated module development, which in turn is useful for module reuse and open sourcing the code at some point.

## Data

Data should _**not**_ be committed to this repository. This is a **code** repository, not a data repository. The only exception is a small dataset that has been added to test the pipeline.

## Pipeline stages

### Reading and writing data at each stage

Each stage uses the `ParquetReader` and `ParquetWriter` (datatrove) modules to read and write data.

The reader is not modified and used as provided by datatrove.

The writer module receives a custom adapter function `gptnl_parquet_writer_adapter`. This adapter enforces some properties of the output file:

- there will be always a `text` field.
- `text1` field is never `NULL` or `None`. If the `text` field value is None at the writing time, it will be replaced by an empty string.

### 1. Data splitting

In Snellius, the data curation pipeline splits the flow of work into many tasks and workers, all working in parallel. For achieving that, the data should be split into multiple files.

You can split the input files by specifying the maximum file size of each output file (`max_file_size`). Keep in mind that the file size is checked before writing a new batch of rows in the `ParquetWriter`, so your `max_file_size` is not a hard constraint. If you notice that the files are significantly bigger than the target size, try reducing the `batch_size`: this will write more frequently to the output file so that the output files will be more aligned with the target `max_file_size`.

If the input rows are very long, you can additionally split them into shorter ones by using the `batch_size` parameter (in combination with the optional `line_chunk_size`).

#### File size margin computation

Since every char of text occupies 1B (neglecting metadata) you can compute how much a file can be bigger than the provided `max_file_size` by multiplying `line_length * max_file_size * batch_size`.

Examples:

- `line_length=100_000`: let's assume all the rows are long 100k characters
- `max_file_size=20*(2**20)`: 20MB
- `batch_size=50`: how frequently to write to disk

In this case, the potential file size can exceed the `max_file_size` by a margin of 5MB (50 \* 100kB), resulting in files of size 25MB.

#### Splitting long rows

If you set the `line_chunk_size`, this stage will split lines according to `line_chunk_size` (simple string chunking, can truncate words at the extremes).
This will impact the `line_length` and reduce your file size margins.

If you don't want to split the rows, set `line_chunk_size=None` and the output file will only be splitted row-wise to get the desired file size.

### 2. String normalization

| Normalizer                          | Description                                                   | Modified by us                                                           | Currently in the Pipeline |
| ----------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------- |
| Datatrove - FTFY                    | Fixes fixes bad Unicdoe.                                      | ✅ Added the possibility to choose from 'NFC', 'NFKC', 'NFD', and 'NFKD' | ✅                        |
| DataJuicer - Punctuation Normalizer | Normalize punctuation to such as replacing 【 to \[ or ━ to - | ✅ Converted to Datatrove pipeline                                       | ✅                        |
| DataJuicer - Whitespace Normalizer  | Normalize whitespace to " ".                                  | ✅ Converted to Datatrove pipeline                                       | ✅                        |

### 3. Heuristic filtering: quality filters and language detectors

Heuristic filters are applied to remove undesired data, generating a new dataset with only the desired datapoints.

| Filters                              | Subfilter                        | Description                                                                                                                                                                                                                                                           | Modified by us                    | Currently in the Pipeline |
| ------------------------------------ | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ------------------------- |
| Datatrove - Language Filter          |                                  | Filters out non-English/Dutch text or if the score is below 0.65                                                                                                                                                                                                      | 🟥                                | ✅                        |
| Datatrove - Gopher Quality Filter    |                                  |                                                                                                                                                                                                                                                                       | ✅ Tokenizer is language specific | ✅                        |
|                                      | filter_symbol-to-word ratio      | Drop documents with a ratio of # or ... higher than 0.1                                                                                                                                                                                                               | 🟥                                | ✅                        |
|                                      | filter_n_bullets                 | Drop document with more than 90% lines starting in bullet points                                                                                                                                                                                                      | 🟥                                | ✅                        |
|                                      | filter_n_ellipsis                | Drop document with more than 30% lines ending in bullet ellipsis                                                                                                                                                                                                      | 🟥                                | ✅                        |
|                                      | filter_max_non_alpha_words_ratio | Drop document with less than 80% of words containing at least one alphabetic character                                                                                                                                                                                | 🟥                                | ✅                        |
|                                      | filter_n_stop_words              | Drop document with less than 2 stop words                                                                                                                                                                                                                             | 🟥                                | ✅                        |
| Datatrove - Gopher Repetition Filter |                                  |                                                                                                                                                                                                                                                                       | ✅ Tokenizer is language specific | ✅                        |
|                                      | filter_dup_line_frac             | Drop documents with line duplicates ratio > 0.35                                                                                                                                                                                                                      | 🟥                                | ✅                        |
|                                      | filter_dup_para_frac             | Drop documents with paragraph duplicates ratio > 0.3 5                                                                                                                                                                                                                | 🟥                                | ✅                        |
|                                      | filter_dup_line_char_frac        | Drop documents with char duplicate ratio > 0.2                                                                                                                                                                                                                        | 🟥                                | ✅                        |
|                                      | filter_dup_para_char_frac        | Drop documents with char duplicates across paragraphs ratio > 0.2                                                                                                                                                                                                     | 🟥                                | ✅                        |
|                                      | filter_top_n_grams               | Top 2-gram character fraction 0.25<br>Top 3-gram character fraction 0.23<br>Top 4-gram character fraction 0.21                                                                                                                                                        | 🟥                                | ✅                        |
|                                      | filter_dup_n_grams               | Duplicate 5-gram character fraction 0.20<br>Duplicate 6-gram character fraction 0.19<br>Duplicate 7-gram character fraction 0.18<br>Duplicate 8-gram character fraction 0.17<br>Duplicate 9-gram character fraction 0.16<br>Duplicate 10-gram character fraction 0.15 | 🟥                                | ✅                        |
| Nordic Pile Quality Filter           |                                  |                                                                                                                                                                                                                                                                       | ✅ Tokenizer is language specific | ✅                        |
|                                      | filter_max_digit_fraction        | Drop documents with a digit fraction >0.2                                                                                                                                                                                                                             | 🟥                                | ✅                        |
|                                      | filter_min_n_char                | Drop documents with documents with number of characters <50                                                                                                                                                                                                           | 🟥                                | ✅                        |
|                                      | filter_min_mean_med_char         | Drop documents with a mean median number of characters per line <9                                                                                                                                                                                                    | 🟥                                | ✅                        |
|                                      | filter_min_mean_med_word         | Drop documents with a mean median number of characters per line <2.1.3                                                                                                                                                                                                | 🟥                                | ✅                        |

### 4. PII masking

Personally identifying information is detected and replaced with synthetically generated data fitting with the context and selected locale. Optionally, markers can be left instead of synthetic replacements.

From version 0.1.5 of the pipeline, and the pii module version 0.4.0, the PII mappers were fully substituted. The previous custom version implemented using Datatrove based filters was substituted by a stage that uses the PrivateAI SW, which uses GPU model heuristics to detect and mark private data entities. Terms referring to the same entity in the document are uniquely masked. We generate random sequences of data that fits with the entity, with Faker as the data source for more entity types.

Example stage with pipeline arguments and filter arguments (related to performance and replacement method):

```yaml
- stage: pii_masking
  input_folder: /projects/prjs0986/wp12/curated/<DATASET>/<PIPELINE_DIR>/stage<NUMBER>_deduplication
  output_folder: /projects/prjs0986/wp12/curated/<DATASET>/<PIPELINE_DIR>/stage<NUMBER+1>_pii_masking
  hpc_time: "10:00:00"
  hpc_partition: gpu_a100
  # hpc_reservation: gpt-nl
  hpc_gpus: "1"
  hpc_cpus_per_task: "16" # Need 16 cores (per private AI GPU instance - actually needs 64 but CPU affinity warnings can be ignored with GPU instance)
  #hpc_mem_per_cpu_gb: "1"  # 120/128 = 0.9375
  hpc_mem_per_cpu_gb: "4" # Need 64GB ram per private AI instance, 64/16 = 4
  hpc_n_tasks: "4" # Number of data trove tasks with split up files
  # Start multiple containers with different ports and wait for healthy containers
  env_commands: "for gpu in ${{CUDA_VISIBLE_DEVICES//,/ }}; do CUDA_VISIBLE_DEVICES=$gpu apptainer run --nv --contain --pwd /app --env PAI_PORT=$((gpu+SLURM_ARRAY_TASK_ID+8080)) --env PAI_TRITON_HTTP_PORT=$((gpu+SLURM_ARRAY_TASK_ID+SLURM_ARRAY_TASK_MAX+8089)) /projects/0/prjs0986/wp13/private-ai/private_ai_gpu.sif & done; sleep 40"
  PII_PrivateAI_TNO:
    chunk_pool_workers: 32 # Number of workers for chunks
    doc_pool_workers: 16 # Number of workers for documents
    request_batch_size: 64 # Chunks of the same document to be sent in the same request to PAI
    batch_size: 16 # Documents to handle in the same batch
    api_endpoint: "http://localhost:808{CUDA_VISIBLE_DEVICES}/" # Template for endpoint per GPU instance (uses task array index and comma-separated indexes from CUDA_VISIBLE_DEVICES)
    replacement_type: "MARKER" # GPU instance does not support SYNTHETIC
    synthetic_replacement_chance: 1.00 # Replace 100% of markers with own synthetic data
    synthetic_replacement_locale: "nl-NL" # Depending on the dominant language use : English en-GB, Dutch nl-NL
```

The following table indicates the entities that are detected and marked by PrivateAI, the replacement strategy methods and locale parameters and what each method does to provide a synthetic replacement sample.

| Entity type/marker            | Synthetic replacement strategy          | Replacement                                                                                                                        |
| ----------------------------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `[DRIVER_LICENSE]`            | `ReplacementStrategy.license`           | Ten digits                                                                                                                         |
| `[EMAIL_ADDRESS]`             | `Faker.ascii_safe_email`                | Email address from example domains                                                                                                 |
| `[HEALTHCARE_NUMBER]`         | `ReplacementStrategy.healthcare_policy` | Nine digits                                                                                                                        |
| `[IP_ADDRESS]`                | `Faker.ipv4_private`                    | IPv4 address (four numbers between 0 and 255 with periods) from private address ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) |
| `[LOCATION_ADDRESS]`          | `Faker.address` (nl-NL/en-GB)           | Street name plus number, postcode and town                                                                                         |
| `[LOCATION_ADDRESS_STREET]`   | `Faker.street_address` (nl-NL/en-GB)    | Street name plus number                                                                                                            |
| `[LOCATION_COORDINATE]`       | `ReplacementStrategy.coordinate`        | Two floating points with comma, within bounding box around the Netherlands                                                         |
| `[LOCATION_ZIP]`              | `Faker.postcode` (nl-NL)                | Four digits plus two letters                                                                                                       |
| `[NAME]`                      | `Faker.name` (nl-NL/en-GB)              | Full name                                                                                                                          |
| `[NAME_FAMILY]`               | `Faker.last_name` (nl-NL/en-GB)         | Family name                                                                                                                        |
| `[NAME_GIVEN]`                | `Faker.first_name` (nl-NL/en-GB)        | Given name                                                                                                                         |
| `[PASSPORT_NUMBER]`           | `ReplacementStrategy.passport`          | RvIG structure: two letters, five alphanumerics and one digit (never an O)                                                         |
| `[PHONE_NUMBER]`              | `Faker.phone_number` (nl-NL)            | Dutch phone number, sometimes with country calling code and parentheses                                                            |
| `[SSN]`                       | `Faker.ssn` (nl-NL)                     | Nine digits                                                                                                                        |
| `[VEHICLE_ID]`                | `Faker.license_plate_car` (nl-NL)       | Three groups of either numbers or non-vowel letters with dashes                                                                    |
| `[BANK_ACCOUNT]`              | `Faker.iban` (nl-NL)                    | NL, two digits, BANK, ten digits                                                                                                   |
| `[CREDIT_CARD]`               | `Faker.credit_card_number`              | About sixteen digits                                                                                                               |
| `[CREDIT_CARD_EXPIRATION]`    | `Faker.credit_card_expire`              | Month/year                                                                                                                         |
| `[CVV]`                       | `Faker.credit_card_security_code`       | Three digits                                                                                                                       |
| `[NAME_MEDICAL_PROFESSIONAL]` | `Faker.name` (nl-NL/en-GB)              | Dr. plus full name                                                                                                                 |
| `[NUMERICAL_PII]`             | `ReplacementStrategy.number`            | Eight digits                                                                                                                       |
| `[URL]`                       | `ReplacementStrategy.url` (nl-NL)       | HTTPS with three words, .nl/com/net/org, path of two words and possibly a query parameter/value                                    |
| `[USERNAME]`                  | `ReplacementStrategy.username` (nl-NL)  | Two words plus four digits or three words                                                                                          |

### 5. Deduplication

This stage involves removing all exact duplicates and performing MinHash Deduplication.
Currently this stage only works on the HPC. As such, please run it using the -p hpc argument.
In the future the default for the deduplication will be changed to HPC. It remains to be disscussed if a local version of deduplication will be supported in the future.

### 6. Toxic language detection

### 7. Machine Translation

This stage translates a dataset from another language into Dutch. It should be run just after dataset extraction and data splitting. Differently from other stages, translation needs GPU. Therefore, the `processing_type` needs to be set to `hpc`, and the correct options need to be set (`hpc_gpus` and `hpc_partition`). See the examples in the `pipeline-configs` folder.

The translation may take quite a long time, so be sure to analyse beforehand the size of your dataset splits to be sure that each task will complete within the time limits (e.g. snellius jobs can last up to 5 days maximum).

1. split the dataset (use the `data_splitting` stage with initial `max_file_size`, `line_chunk_size` and `batch_size`)
2. find the biggest file: `ls -lhS PATH_TO_SPLITTED_DATASET | head`
3. use the `machine_translation` stage with `dry_run=True` and `glob_pattern=*BIGGEST_FILE.parquet` to determine the total number of batches (see in the job logs)
4. as reference, the translation model running on H100 node on snellius (partition=gpu_h100) takes approximately 12 seconds to process 1 batch of size 32
5. estimate the execution time for the biggest file (`n_batches` \* `time_per_batch`)
6. if the estimated time exceeds the time limit (take some margin!!), restart from point 1 with appropriate parameters (`max_file_size`, `line_chunk_size` and `batch_size`)
7. set `hpc_n_tasks` to the number of files (you can also combine more files in one task, by dividing this value by a factor), remove `dry_run` and `glob_pattern` and re-run the `machine_translation` stage

### 8. LLM Processing

This module allows you to process text throuh a LLM. You pick the model name and the prompt and you get back the results.

### Visualise Carbon Footprint

> **WARNING**
> If you can't install energy-utils it might be a ssh connection issue so try to change poetry add "energy-utils@git+ssh://tnocigit/gpt-nl/model-development/energy-utils.git" to poetry add "energy-utils@git+ssh://**{your_ssh_alias}**/gpt-nl/model-development/energy-utils.git"

> Make sure to to set hpc_ear to true in the yaml file!

```bash
python -m energy_utils FILE_PREFIX.g/tcnXX.time.loops.csv
```

If the file has data from multiple slurm jobs, you will receive an exception and need to pass additionally the selected job ID.

```bash
python -m energy_utils FILE_PREFIX.g/cnXX.time.loops.csv --job-id=YYYYY
```

### Visualise Data Quality Results

To visualize the computed perplexity score between two different datasets, run the following command.

```bash
python helper-scripts/inspect_quality.py folder_1/quality_analysis/ folder_2/quality_analysis/
```

## Post-curation checks

After the pipeline (all applicable stages) is completed, some checks should be done to
guarantee that the whole process worked well. This is done with a series of checks:

### Check that all generated .parquet files are valid

In the root of the pipeline, run the helper script:

```bash
python helper-scripts/check_parket.py .
```

This will walk the subtree of the pipeline, check the validity of all .parquet files in
it, and print either a `invalid_parquet_files.json` file or a `ALL_PARQUET_FILES_VALID`
file in the root directory.

## Changelog

A log of changes per pipeline version is maintained in the `CHANGELOG.md` file.

If you are a developer, please, pay attention to the following guidelines for reporting
significant changes in the pipeline.

Some modifications **_MUST_** be reported:

- Changes in the modules versions used in the pyproject.toml file
- Insertion of new modules in the pipeline (new stages, e.g. machine translation)

Further instructions for reporting changes are found in the `CHANGELOG.md` file.

### Installing mlcroissant

To install mlcroissannt, use the following command:

pip install "git+https://github.com/mlcommons/croissant.git@main#subdirectory=python/mlcroissant"
