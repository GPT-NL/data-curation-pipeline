import json
from pathlib import Path

import matplotlib.cm as cm
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import typer
from loguru import logger
from plotly.subplots import make_subplots

app = typer.Typer()


@app.command()
def plot_perplexity(list_of_paths: list[Path]):
    """Inspect the quality of the data looking at perplexity

    Thereby multiple paths can be given to plot multiple histograms
    """
    df = pd.DataFrame(columns=["value", "file"])
    for path in list_of_paths:
        logger.info(f"Getting the info of {path}")
        summary_folder = path / "summary"
        assert summary_folder.exists(), logger.error(
            f"Summary folder does not exist: {summary_folder}"
        )

        # Use Path to find all relevant JSON files
        json_files = list(summary_folder.glob("perplexity*english/*.json")) + list(
            summary_folder.glob("perplexity*dutch/*.json")
        )

        for json_file in json_files:
            logger.info(f"Found JSON file: {json_file}")
            with open(json_file, "r") as f:
                json_data = json.load(f)["summary"]
                new_row = pd.DataFrame(
                    [{"value": json_data["mean"], "file": json_file.parents[2].name}]
                )
                df = pd.concat([df, new_row], ignore_index=True)

    # Create the initial box plot
    fig = px.strip(
        df,
        x="value",
        y="file",
        # facet_row="file",
        color="file",
        orientation="h",
        # log_x=True,
        template="none",
    )
    fig.update_layout(
        yaxis=dict(title_text="")  # Set the y-axis title to an empty string
    )
    fig.update_yaxes(showticklabels=False)
    fig.update_xaxes(title_text="Perplexity")

    fig.update_xaxes(matches=None)
    fig.update_yaxes(matches=None)
    fig.write_image("results.png", width=800, height=600, scale=2)


if __name__ == "__main__":
    app()
