from pathlib import Path

import pandas as pd


def add_duplicates():
    # Get the path to the current script file (helper-scripts/add_duplicates.py)
    current_script_path = Path(__file__).resolve()
    helper_scripts_folder = current_script_path.parent

    # Specify the relative path to the input Parquet file
    input_file_path = (
        helper_scripts_folder / ".." / ".." / "test-data" / "0. raw" / "data.parquet"
    )
    # Specify the relative path to save the sampled Parquet file
    output_file_path = (
        helper_scripts_folder
        / ".."
        / ".."
        / "test-data"
        / "0. duplicates"
        / "data_duplicated.parquet"
    )

    # Create the output directory if it doesn't exist
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Read the Parquet file
    df = pd.read_parquet(input_file_path)

    # Sample 5% of the rows
    sampled_df = df.sample(frac=0.05, random_state=1)

    # Reset the index to avoid the extra index column
    sampled_df = sampled_df.reset_index(drop=True)

    # Specify the columns to keep
    columns_to_keep = ["text", "metadata", "id"]
    sampled_df = sampled_df[columns_to_keep]

    # Append the copied rows to the sampled dataframe
    final_df = pd.concat([sampled_df, df])
    final_df = final_df.reset_index(drop=True)
    final_df = final_df[columns_to_keep]

    # Save the sampled data to a new Parquet file
    final_df.to_parquet(output_file_path)

    print(f"Sampled data saved to {output_file_path}")


if __name__ == "__main__":
    add_duplicates()
