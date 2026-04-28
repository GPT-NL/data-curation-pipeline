# GPT-NL Dataset deployment procedure

This document explains the procedure we took for preparing the delivery versions of the
GPT-NL_dataset.

The deployment procedure starts after the curation pipelines are executed for each input
dataset, each of them with their particular configuration. This document does not go
into the details of the curation procedure, but rather how we clean up, and prepare the
curated data into a packaged dataset that is then transferred to the training team.

## Structure of Deployment Folder

The name of a delivery folder is always composed in the following format:

- `gpt_nl_dataset_` as a prefix
- followed by `v_x.y` version tag, where `x`is the major version, and `y` the minor version.

Example: the folder `gpt_nl_dataset_v1.0` contains the GPT-NL dataset version 1.0

The folder structure is simple. Each sub-folder contains the files for one dataset collection. Collections are the individual datasets used to compose the GPT-NL dataset. Example:

```bash
$ ls -l
drwxrws---+ 2 user123 prjs0986  16384 Jun  2 22:35 american-stories
drwxrws---+ 2 user123 prjs0986 262144 Jun  2 22:36 cc_english-pd
drwxrws---+ 2 user123 prjs0986  16384 Jun  2 22:36 cc_eurovoc
drwxrws---+ 2 user123 prjs0986  32768 Jun  2 22:36 cc_german-pd
drwxrws---+ 2 user123 prjs0986 131072 Jun  2 22:36 cc_github_open_source
<snip>
```

## Post-processing procedures

Post-processing actions start after the final curated data is collected from the
curation pipelines into the delivery folder structure. The purpose of the
post-processing is to create homogeneously named and formatted final dataset files, and
collecting/measuring statistics. It also automates the process of dataset description
(generating the croissant-formatted description files).

The post-processing procedures are:

| ID                                                                 | Description                                                              |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| [PP01](#pp01---copy-files-from-curation-base-to-collection-folder) | Collecting .parquet files from curation base and checking their validity |
| [PP02](#pp02---renaming-parquet-files)                             | Renaming .parquet files according to dataset name.                       |
| [PP03](#pp03---formatting-dataset-files)                           | Formatting .parquet files according to the delivery standard             |
| [PP04](#pp04---collecting-dataset-statistics)                      | Collecting dataset (collections) statistics                              |
| [PP05](#pp05---creating-croissant-descriptors)                     | Creating _Croissant_ description files for the collections               |
| [PP06](#pp06---re-run-the-file-integrity-checks)                   | Run final integrity checks and close the delivery of the collection      |

### Preparation

Scripts for this procedure are collected in the `pipeline` repository. For executing them, you will have to:

1. Clone the repository. Follow instructions from the [repository README.md](https://github.com/GPT-NL/data-curation-pipeline?tab=readme-ov-file#data-curation-pipeline)
2. Run the initialization script `source init_snellius.sh`

<TODO>: Include here a sequence (in order) of the post-processing procedures.

### PP01 - Copy files from curation base to collection folder

First, **create a folder for the collection within the data set delivery folder**. The
convention is to use the same name of the collection as used in the curation base.

Second, **copy only `.parquet` files from the last curation stage folder to the
collection folder you created.**

Third, check validity of all the copied files. For that, execute the script `check_parquet.py` as follows:

```bash
$ python <helper_script_folder>/check_parquet.py <dataset_dir>
```

That will produce either an empty file `ALL_PARQUET_FILES_VALID` in the folder, _or_ a file `invalid_parquet_files.json` with a list of the invalid files. More info on this script below.

```bash
$ python <helper_script_folder>/check_parquet.py --help
usage: check_parquet.py [-h] [--threads THREADS] path

Validate Parquet files.

positional arguments:
  path               Path to a .parquet file or a directory

options:
  -h, --help         show this help message and exit
  --threads THREADS  Number of threads to use (default: 8)
```

Do not proceed if invalid parquet files were found. Solve the problem in the curation
base first, then collect and re-test the files to the delivery set.

### PP02 - Renaming .parquet files

Final files at the end of the curation pipeline may have non-homogeneous file names due
to differences in the pipeline execution, number of files, etc. They are typically just
some sequence of numbered files bound to the number of threads and slurm jobs.

This post processing procedure puts in place a single naming convention for all the
files within and across the dataset.

To execute this procedure, run the `rename_parquet.py` script as follows:

```bash
$ python <helper_script_folder>/rename_parquet.py --input_dir <dataset_dir> --prefix <file_prefix>
```

By convention, `file_prefix` is **the name of the dataset**.

Files will be prefixed and numerated in a sequence. Example of its output:

```bash
-rw-rw----+ 1 user123 prjs0986 114494920 Jun  2 18:54 kb_0001.parquet
-rw-rw----+ 1 user123 prjs0986 157850628 Jun  2 18:54 kb_0002.parquet
-rw-rw----+ 1 user123 prjs0986 134988528 Jun  2 18:54 kb_0003.parquet
-rw-rw----+ 1 user123 prjs0986 103273950 Jun  2 18:54 kb_0004.parquet
-rw-rw----+ 1 user123 prjs0986 156669121 Jun  2 18:54 kb_0005.parquet
-rw-rw----+ 1 user123 prjs0986 124876036 Jun  2 18:54 kb_0006.parquet
-rw-rw----+ 1 user123 prjs0986  94046642 Jun  2 18:54 kb_0007.parquet
-rw-rw----+ 1 user123 prjs0986  41669378 Jun  2 18:54 kb_0008.parquet
-rw-rw----+ 1 user123 prjs0986  73834849 Jun  2 18:54 kb_0009.parquet
-rw-rw----+ 1 user123 prjs0986  78382672 Jun  2 18:54 kb_0010.parquet
-rw-rw----+ 1 user123 prjs0986  74762606 Jun  2 18:54 kb_0011.parquet
-rw-rw----+ 1 user123 prjs0986  65089761 Jun  2 18:54 kb_0012.parquet
```

More info on the `rename_parquet` script:

```bash
$ python <helper_script_folder>/rename_parquet.py --help
usage: rename_parquet.py [-h] --input_dir INPUT_DIR --prefix PREFIX [--verbose]

Rename parquet files in a directory.

options:
  -h, --help            show this help message and exit
  --input_dir INPUT_DIR
                        Input directory containing parquet files.
  --prefix PREFIX       Prefix for the new file names.
  --verbose             Print verbose output.
```

### PP03 - Formatting dataset files

Besides non-homogeneous file names (see PP01), final files at the end of the curation
pipeline may have also non-homogeneous file formats due to differences in the pipeline
execution, number of files, etc. They have different column compositions. The purpose
of this step is to bring all the files of the deployment into the same table format.

The deployment files in a GPT-NL dataset must have the following columns:

```python
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
```

Other columns will remain in files at the curation set, but will be eliminated from the
delivery set files.

If columns are missing they are filled in with a defined default value.

This post processing procedure puts in place a mechanism to homogenize the files within
and across the dataset and its collection.

To execute this procedure, run the `dataset_format.py` script as follows:

```bash
$ python <helper_script_folder>/dataset_format.py --help

usage: dataset_format.py [-h] [--dry-run] file_path

Format dataset to comply with the GPT-NL dataset standard format. Please ensure to backup your original file before running this script. This script replaces the original file, use with caution.

positional arguments:
  file_path      Path to the input parquet file.  If file path is a directory, the command will apply the format to all the internal *.parquet files.

options:
  -h, --help     show this help message and exit
  --dry-run, -d  A dry run will save the changes to a new file with '_formatted' suffix instead of overwriting the original file.
  --yes, -y      Answer yes to all confirmation questions. Useful on scripts.
```

### PP04 - Extracting dataset (collection) statistics

The next step in the deployment is to aggregate file specific and statistical
information in the dataset. That is done per collection and per file within each
collection.

The extraction and aggregation of info can be done per collection folder, invoking the `dataset_stats.py` script. Instructions are as follows:

```bash
$ python <helper_script_folder>/dataset_stats.py --help
usage: dataset_stats.py [-h] [--verbose] [--sample] dataset_dir

Collect statistics for each parquet file in the dataset

positional arguments:
  dataset_dir    Path to the dataset folder. We assume the folder is populated with .parquet files with a table structure defined in the GPT-NL dataset standard
                 format.

options:
  -h, --help     show this help message and exit
  --verbose, -v  Prints all the statistics for each parquet file in the dataset to the console.
  --sample, -s   Prints a sample statistics file information with 3 files sampled from the dataset directory.
```

This script produces a dataset_stats.yaml file with file information and statistics.

A snippet of the file is depicted below:

```yaml
- file_sha256_hex_hash: ef21ac04bb4c2000a9a151de5d9a82cc7a0b24f574b24eb9beb3c699fcc45f4f
  filename: american-stories_0001.parquet
  size: 288539757
  stats:
    char_stats:
      max: 10795
      mean: 873.0237429906542
      min: 50
      std: 934.19546217253
      total: 373654162
    column_types:
    - string
    - double
    ...
    columns:
    - text
    - avg_word_length
    ...
    language_score_stats:
      avg_word_length_mean:
      - 4.588718961635696
      - 4.314285714285715
      avg_word_length_stddev:
      - 0.36122577635508807
      - 0.11428571428571432
      language:
      - en
      - da
      language_score_max:
      - 0.9998667240142822
      - 0.7020418047904968
      language_score_mean:
      - 0.9425626640138525
      - 0.6945686638355255
      language_score_min:
      - 0.6500967741012573
      - 0.6870955228805542
```

### PP05 - Creating _Croissant_ descriptors

Each collection of the GPT-NL dataset should be delivered with a [`croissant`](https://mlcommons.org/working-groups/data/croissant/) description file.

We prepared a helper script to generate the croissant file based on the structure of a `.parquet` file within the collection folder. To generate the initial (almost complete) croissant file, use the:

```bash
$ python <helper_script_folder>/make_croissant.py <dataset collection folder>
```

See script help:

```bash
$ python ~/git/pipeline/helper-scripts/make_croissant.py --help
usage: make_croissant.py [-h] dataset_dir

Produces a Croissant metadata file from a Parquet dataset.

positional arguments:
  dataset_dir  Path to a dataset(collection folder) that exemplifies the dataset file. We assume the file is representative in its structure and metadata to all
               the files in the dataset.

options:
  -h, --help   show this help message and exit
```

### PP06 - Re-run the file integrity checks

As some of the operations in this deployment procedure manipulate (and as such can corrupt) the `.parquet` files. A last check for the file integrity must happen.

Just execute again the `check_parquet.py` script. See [instructions in PP01](#pp01---copy-files-from-curation-base-to-collection-folder).

Finally, run the checklist for deployment below and if all is done, the collection can be declared as delivered.

## Checklist for deployment

- [ ] All dataset collections copied to the deployment folder structure? (See [Structure
      of Deployment Folder](structure-of-deployment-folder))

- Post-processing
  - [ ] Renamed parquet files in each collection? Is the prefix equal to the
        collection name? (See [Renaming .parquet files](renaming-parquet-files))

## One Script to rule them all, One Script to find them, One Script to bring them all and in the darkness bind them

There is a sbatch script to follow all those steps -- `deliver_collection.job`

1. Start by running in the `pipeline` folder:

```
source .init_snellius
```

2. Run the script `sbatch deliver_collection.job <source folder for the collection> <name of the collection>`
