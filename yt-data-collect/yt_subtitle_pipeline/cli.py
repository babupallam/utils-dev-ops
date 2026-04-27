from __future__ import annotations

import argparse
import logging
from pathlib import Path

from yt_subtitle_pipeline.config_loader import ConfigLoader
from yt_subtitle_pipeline.engine import YTSubtitleEngine
from yt_subtitle_pipeline.exceptions import YTSubtitleError


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argparse namespace.
    """

    parser = argparse.ArgumentParser(
        description="Search YouTube videos and extract available subtitles into a ZIP archive."
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to YAML configuration file.",
    )

    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="YouTube search query. Overrides config.yaml.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of videos to process. Overrides config.yaml.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output ZIP file path. Overrides config.yaml.",
    )

    parser.add_argument(
        "--links-output",
        type=Path,
        default=None,
        help="Output text file path for YouTube links. Overrides config.yaml.",
    )

    parser.add_argument(
        "--upload-days",
        type=int,
        default=None,
        help="Only include videos uploaded within the last N days. Overrides config.yaml.",
    )

    parser.add_argument(
        "--sort-by",
        choices=("view_count", "upload_date"),
        default=None,
        help="Sort selected videos by view_count or upload_date. Overrides config.yaml.",
    )

    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Number of parallel transcript workers. Overrides config.yaml.",
    )

    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Comma-separated transcript language codes, for example: en,en-US.",
    )

    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        default=None,
        help="Logging level. Overrides config.yaml.",
    )

    return parser.parse_args()


def main() -> int:
    """Application entry point.

    Returns:
        Process exit code.
    """

    try:
        args = parse_args()
        config = ConfigLoader.build_config(args)
        engine = YTSubtitleEngine(config)
        engine.run()
        return 0

    except YTSubtitleError as exc:
        logging.basicConfig(level=logging.ERROR)
        logging.error("%s", exc)
        return 1

    except Exception as exc:
        logging.basicConfig(level=logging.ERROR)
        logging.exception("Unexpected application failure: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())