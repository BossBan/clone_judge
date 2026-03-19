import argparse
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv-files",
        nargs="+",
        type=Path,
        help="CSV files to process.",
    )
    parser.add_argument(
        "--code-dir",
        type=Path,
        default=Path("data"),
        help="Data directory containing the code files.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv(
            "ZHIPUAI_API_KEY", "f53c763c7c4c498e884cd3c3ebec8ca2.1IOwLwLi105s6tCe"
        ),
        help="Zhipu AI API key.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Batch timeout in seconds passed to CloneChecker.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="How many code pairs to send in one batch.",
    )
    parser.add_argument(
        "--concurrency-limit",
        type=int,
        default=200,
        help="Concurrent API calls limit passed to CloneChecker.",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=Path("prompt_template.txt"),
        help="Prompt template file for clone_checker.",
    )
    parser.add_argument(
        "--csv-chunk-size",
        type=int,
        default=1000,
        help="How many CSV rows to process per chunk.",
    )
    parser.add_argument(
        "--lines",
        type=int,
        default=None,
        help="Number of lines to randomly sample from each CSV file. If not provided, process all lines.",
    )
    return parser.parse_args()
