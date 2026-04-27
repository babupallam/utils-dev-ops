from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, Optional
import datetime as dt

import yaml

from yt_subtitle_pipeline.exceptions import ConfigFileError
from yt_subtitle_pipeline.models import AppConfig
from yt_subtitle_pipeline.utils.formatter import Formatter


class ConfigLoader:
    """Load pipeline configuration from YAML file and CLI overrides."""

    @staticmethod
    def load_yaml(path: Optional[Path]) -> Dict[str, Any]:
        """Load YAML configuration file.

        Args:
            path: Path to config.yaml.

        Returns:
            Configuration dictionary.

        Raises:
            ConfigFileError: If the file cannot be read or parsed.
        """

        if path is None:
            return {}

        if not path.exists():
            raise ConfigFileError(f"Config file does not exist: {path}")

        try:
            with path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
        except Exception as exc:
            raise ConfigFileError(f"Failed to load config file: {exc}") from exc

        if not isinstance(data, dict):
            raise ConfigFileError("Config file must contain a YAML dictionary.")

        return data

    @staticmethod
    def build_config(args: argparse.Namespace) -> AppConfig:
        """Build final AppConfig from config.yaml and CLI overrides.

        Args:
            args: Parsed command-line arguments.

        Returns:
            Final validated application configuration.
        """

        data = ConfigLoader.load_yaml(args.config)

        pipeline = data.get("pipeline", {})
        search = data.get("search", {})
        subtitles = data.get("subtitles", {})
        logging_config = data.get("logging", {})

        query = args.query or pipeline.get("query", "")
        limit = args.limit if args.limit is not None else pipeline.get("limit", 10)

        base_output_dir = Path(pipeline.get("base_output_dir", "outputs"))

        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_folder_name = Formatter.build_run_folder_name(query=query, timestamp=timestamp)
        run_output_dir = base_output_dir / run_folder_name

        output_path = Path(
            args.output or run_output_dir / "subtitles.zip"
        )

        links_output_path = Path(
            args.links_output or run_output_dir / "youtube_links.txt"
        )

        upload_days = (
            args.upload_days
            if args.upload_days is not None
            else search.get("upload_days", 365)
        )

        max_limit = search.get("max_limit", 50)
        sort_by = args.sort_by or search.get("sort_by", "view_count")

        max_workers = (
            args.max_workers
            if args.max_workers is not None
            else subtitles.get("max_workers", 4)
        )

        yaml_languages = subtitles.get("languages", ["en"])
        cli_languages = args.language.split(",") if args.language else None

        language_codes = tuple(
            language.strip()
            for language in (cli_languages or yaml_languages)
            if str(language).strip()
        )

        log_level = args.log_level or logging_config.get("level", "INFO")

        config = AppConfig(
            query=query,
            limit=int(limit),
            output_path=output_path,
            links_output_path=links_output_path,
            run_output_dir=run_output_dir,
            upload_days=int(upload_days),
            max_limit=int(max_limit),
            sort_by=str(sort_by),
            language_codes=language_codes or ("en",),
            max_workers=int(max_workers),
            log_level=str(log_level),
        )

        config.validate()

        return config