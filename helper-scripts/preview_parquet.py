import pandas as pd
import sys


def preview_parquet(file_path, n=10):
    try:
        df = pd.read_parquet(file_path)
        print(df.head(n))
        print(df.info())
        print(df.describe())
        print(df.columns)
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python preview_parquet.py <file_path> [n]")
    else:
        file_path = sys.argv[1]
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        preview_parquet(file_path, n)
