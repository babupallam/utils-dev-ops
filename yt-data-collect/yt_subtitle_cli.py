#!/usr/bin/env python3
"""
yt_subtitle_cli.py

Step 1:
    Install dependencies:

        pip install -r requirements.txt

Step 2:
    Create config.yaml:

        pipeline:
          query: "python tutorial"
          limit: 10
          output_path: "outputs/subtitles.zip"
          links_output_path: "outputs/youtube_links.txt"

        search:
          upload_days: 365
          max_limit: 50
          sort_by: "view_count"

        subtitles:
          languages:
            - "en"
          max_workers: 4

        logging:
          level: "INFO"

Step 3:
    Run using config file:

        python yt_subtitle_cli.py --config config.yaml

Step 4:
    Or override config values from terminal:

        python yt_subtitle_cli.py \
            --config config.yaml \
            --query "machine learning" \
            --limit 5 \
            --output outputs/ml_subtitles.zip

Step 5:
    Output files:

        outputs/subtitles.zip
        outputs/youtube_links.txt
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import logging
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import yaml
import yt_dlp
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)


class YTSubtitleError(Exception):
    """Base exception for YouTube subtitle application errors."""


class TranscriptNotFoundError(YTSubtitleError):
    """Raised when a transcript cannot be found for a video."""


class SearchLimitExceeded(YTSubtitleError):
    """Raised when the requested search limit exceeds the configured maximum."""


class SearchServiceError(YTSubtitleError):
    """Raised when the search service fails."""


class ArchiveServiceError(YTSubtitleError):
    """Raised when ZIP archive creation fails."""


class ConfigFileError(YTSubtitleError):
    """Raised when the configuration file is invalid or unreadable."""


@dataclass(frozen=True)
class AppConfig:
    """Application configuration.

    Args:
        query: Search keywords used to find YouTube videos.
        limit: Maximum number of videos to process.
        output_path: Final ZIP archive path.
        links_output_path: Text file path for saving selected YouTube links.
        upload_days: Only include videos uploaded within this number of days.
        max_limit: Maximum allowed search limit.
        sort_by: Metadata field used for sorting search results.
        language_codes: Preferred transcript language codes.
        max_workers: Number of parallel transcript download workers.
        log_level: Logging verbosity level.
    """

    query: str
    limit: int
    output_path: Path
    links_output_path: Path
    upload_days: int = 365
    max_limit: int = 50
    sort_by: str = "view_count"
    language_codes: Tuple[str, ...] = ("en",)
    max_workers: int = 4
    log_level: str = "INFO"

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If required values are invalid.
            SearchLimitExceeded: If limit is greater than max_limit.
        """

        if not self.query.strip():
            raise ValueError("Search query cannot be empty.")

        if self.limit < 1:
            raise ValueError("Limit must be at least 1.")

        if self.limit > self.max_limit:
            raise SearchLimitExceeded(
                f"Requested limit {self.limit} exceeds max allowed limit {self.max_limit}."
            )

        if self.upload_days < 1:
            raise ValueError("upload_days must be at least 1.")

        if self.max_workers < 1:
            raise ValueError("max_workers must be at least 1.")

        if self.sort_by not in {"view_count", "upload_date"}:
            raise ValueError("sort_by must be either 'view_count' or 'upload_date'.")

        if not self.output_path.name.lower().endswith(".zip"):
            raise ValueError("Output path must end with .zip.")

        if not self.links_output_path.name.lower().endswith(".txt"):
            raise ValueError("Links output path must end with .txt.")


@dataclass(frozen=True)
class VideoMetadata:
    """Normalized YouTube video metadata.

    Args:
        video_id: YouTube video ID.
        title: Video title.
        url: Full YouTube watch URL.
        upload_date: Upload date in YYYYMMDD format when available.
        view_count: Number of views when available.
    """

    video_id: str
    title: str
    url: str
    upload_date: Optional[str]
    view_count: int


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

        output_path = Path(
            args.output or pipeline.get("output_path", "outputs/subtitles.zip")
        )

        links_output_path = Path(
            args.links_output
            or pipeline.get("links_output_path", "outputs/youtube_links.txt")
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
            upload_days=int(upload_days),
            max_limit=int(max_limit),
            sort_by=str(sort_by),
            language_codes=language_codes or ("en",),
            max_workers=int(max_workers),
            log_level=str(log_level),
        )

        config.validate()

        return config


class Formatter:
    """Formatting utilities for filenames and subtitle conversion."""

    @staticmethod
    def sanitize_filename(value: str, max_length: int = 120) -> str:
        """Convert arbitrary text into a safe filename.

        Args:
            value: Raw filename value.
            max_length: Maximum filename length.

        Returns:
            Safe filename string.
        """

        cleaned = re.sub(r"[^\w\s.-]", "", value, flags=re.UNICODE)
        cleaned = re.sub(r"\s+", "_", cleaned.strip())
        cleaned = cleaned.strip("._")

        if not cleaned:
            cleaned = "untitled"

        return cleaned[:max_length]

    @staticmethod
    def seconds_to_srt_timestamp(seconds: float) -> str:
        """Convert seconds to SubRip timestamp.

        Args:
            seconds: Timestamp in seconds.

        Returns:
            Timestamp formatted as HH:MM:SS,mmm.
        """

        if seconds < 0:
            seconds = 0

        milliseconds_total = int(round(seconds * 1000))
        hours = milliseconds_total // 3_600_000
        milliseconds_total %= 3_600_000

        minutes = milliseconds_total // 60_000
        milliseconds_total %= 60_000

        secs = milliseconds_total // 1_000
        millis = milliseconds_total % 1_000

        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

    @classmethod
    def transcript_to_srt(cls, transcript: Sequence[Dict[str, Any]]) -> str:
        """Convert raw transcript JSON items into valid SRT text.

        Args:
            transcript: Transcript items returned by youtube-transcript-api.

        Returns:
            Subtitle text in SubRip format.
        """

        blocks: List[str] = []

        for index, item in enumerate(transcript, start=1):
            start = float(item.get("start", 0.0))
            duration = float(item.get("duration", 0.0))
            end = start + max(duration, 0.001)

            text = str(item.get("text", "")).replace("\n", " ").strip()

            if not text:
                continue

            start_ts = cls.seconds_to_srt_timestamp(start)
            end_ts = cls.seconds_to_srt_timestamp(end)

            blocks.append(f"{index}\n{start_ts} --> {end_ts}\n{text}")

        return "\n\n".join(blocks) + "\n"


class FileIO:
    """File input/output helper utilities."""

    @staticmethod
    def ensure_parent_dir(path: Path) -> None:
        """Create parent directory for a given path if missing.

        Args:
            path: Target file path.
        """

        path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def write_text(path: Path, content: str) -> None:
        """Write UTF-8 text to disk.

        Args:
            path: Destination file path.
            content: Text content.
        """

        FileIO.ensure_parent_dir(path)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def save_youtube_links(path: Path, videos: Sequence[VideoMetadata]) -> None:
        """Save selected YouTube links to a separate text file.

        Args:
            path: Destination text file path.
            videos: Selected video metadata list.
        """

        FileIO.ensure_parent_dir(path)

        lines: List[str] = []

        for index, video in enumerate(videos, start=1):
            lines.append(f"{index}. {video.title}")
            lines.append(f"   URL: {video.url}")
            lines.append(f"   Video ID: {video.video_id}")
            lines.append(f"   Upload Date: {video.upload_date or 'unknown'}")
            lines.append(f"   View Count: {video.view_count}")
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")


class SearchService:
    """Search service that uses yt-dlp to fetch YouTube metadata."""

    def __init__(self, logger: logging.Logger) -> None:
        """Initialize the search service.

        Args:
            logger: Application logger.
        """

        self.logger = logger

    def search(
        self,
        query: str,
        limit: int,
        upload_days: int,
        sort_by: str,
    ) -> List[VideoMetadata]:
        """Search YouTube videos and return filtered metadata.

        Args:
            query: Search keywords.
            limit: Maximum number of videos to return.
            upload_days: Include only videos uploaded within this number of days.
            sort_by: Sorting field, either view_count or upload_date.

        Returns:
            List of normalized video metadata.

        Raises:
            SearchServiceError: If yt-dlp fails to fetch metadata.
        """

        self.logger.info("Searching YouTube videos for query: %s", query)

        search_count = max(limit * 3, limit)
        search_expression = f"ytsearch{search_count}:{query}"

        ydl_options: Dict[str, Any] = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "ignoreerrors": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_options) as ydl:
                raw_result = ydl.extract_info(search_expression, download=False)
        except Exception as exc:
            raise SearchServiceError(f"yt-dlp search failed: {exc}") from exc

        entries = raw_result.get("entries", []) if raw_result else []
        cutoff_date = dt.datetime.now(dt.UTC).date() - dt.timedelta(days=upload_days)

        videos: List[VideoMetadata] = []

        for entry in entries:
            if not entry:
                continue

            video_id = str(entry.get("id") or "").strip()
            title = str(entry.get("title") or "Untitled").strip()
            upload_date = entry.get("upload_date")
            view_count = int(entry.get("view_count") or 0)

            if not video_id:
                continue

            if upload_date and not self._is_recent_upload(upload_date, cutoff_date):
                self.logger.debug("Skipping old video: %s", title)
                continue

            videos.append(
                VideoMetadata(
                    video_id=video_id,
                    title=title,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    upload_date=upload_date,
                    view_count=view_count,
                )
            )

        if sort_by == "upload_date":
            videos.sort(key=lambda item: item.upload_date or "", reverse=True)
        else:
            videos.sort(key=lambda item: item.view_count, reverse=True)

        selected = videos[:limit]

        self.logger.info("Selected %d videos after filtering and sorting.", len(selected))

        return selected

    @staticmethod
    def _is_recent_upload(upload_date: str, cutoff_date: dt.date) -> bool:
        """Check whether a YouTube upload date is within the accepted range.

        Args:
            upload_date: Date string in YYYYMMDD format.
            cutoff_date: Minimum allowed upload date.

        Returns:
            True if the video is recent enough, otherwise False.
        """

        try:
            parsed_date = dt.datetime.strptime(upload_date, "%Y%m%d").date()
        except ValueError:
            return True

        return parsed_date >= cutoff_date


class SubtitleService:
    """Subtitle service that fetches transcripts and converts them to SRT."""

    def __init__(self, language_codes: Sequence[str], logger: logging.Logger) -> None:
        """Initialize subtitle service.

        Args:
            language_codes: Preferred subtitle language codes.
            logger: Application logger.
        """

        self.language_codes = tuple(language_codes)
        self.logger = logger
        self.api = YouTubeTranscriptApi()

    def fetch_srt(self, video: VideoMetadata) -> str:
        """Fetch transcript for one video and convert it to SRT.

        Args:
            video: Video metadata.

        Returns:
            SRT-formatted subtitle content.

        Raises:
            TranscriptNotFoundError: If transcript is unavailable.
        """

        self.logger.debug("Fetching transcript for video: %s", video.url)

        try:
            fetched_transcript = self.api.fetch(
                video.video_id,
                languages=list(self.language_codes),
            )

            transcript = fetched_transcript.to_raw_data()

        except (NoTranscriptFound, TranscriptsDisabled) as exc:
            raise TranscriptNotFoundError(
                f"No transcript available for video {video.video_id}: {video.title}"
            ) from exc

        except Exception as exc:
            raise TranscriptNotFoundError(
                f"Failed to fetch transcript for video {video.video_id}: {exc}"
            ) from exc

        return Formatter.transcript_to_srt(transcript)


class ArchiveService:
    """Archive service that manages temporary files and ZIP creation."""

    def __init__(self, output_path: Path, logger: logging.Logger) -> None:
        """Initialize archive service.

        Args:
            output_path: Final ZIP archive path.
            logger: Application logger.
        """

        self.output_path = output_path
        self.logger = logger
        self._temp_dir: Optional[Path] = None

    def __enter__(self) -> "ArchiveService":
        """Create temporary workspace.

        Returns:
            Current archive service instance.
        """

        self._temp_dir = Path(tempfile.mkdtemp(prefix="yt_subtitles_"))
        self.logger.debug("Created temporary directory: %s", self._temp_dir)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Clean up temporary workspace.

        Args:
            exc_type: Exception type when present.
            exc: Exception object when present.
            traceback: Traceback object when present.
        """

        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self.logger.debug("Removed temporary directory: %s", self._temp_dir)

    @property
    def temp_dir(self) -> Path:
        """Return active temporary directory.

        Returns:
            Temporary directory path.

        Raises:
            ArchiveServiceError: If archive service has not been entered.
        """

        if self._temp_dir is None:
            raise ArchiveServiceError("ArchiveService must be used as a context manager.")

        return self._temp_dir

    def create_subtitle_file(self, video: VideoMetadata, srt_content: str) -> Path:
        """Create one SRT file inside the temporary workspace.

        Args:
            video: Video metadata.
            srt_content: SRT subtitle content.

        Returns:
            Created SRT file path.
        """

        safe_title = Formatter.sanitize_filename(video.title)
        file_name = f"{safe_title}_{video.video_id}.srt"
        file_path = self.temp_dir / file_name

        FileIO.write_text(file_path, srt_content)

        self.logger.debug("Created subtitle file: %s", file_path)

        return file_path

    def create_zip(self, files: Iterable[Path]) -> Path:
        """Create final ZIP archive from generated subtitle files.

        Args:
            files: Paths to subtitle files.

        Returns:
            Final ZIP archive path.

        Raises:
            ArchiveServiceError: If ZIP creation fails.
        """

        FileIO.ensure_parent_dir(self.output_path)

        try:
            with zipfile.ZipFile(
                self.output_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as zip_file:
                for file_path in files:
                    zip_file.write(file_path, arcname=file_path.name)
        except Exception as exc:
            raise ArchiveServiceError(f"Failed to create ZIP archive: {exc}") from exc

        self.logger.info("ZIP archive created: %s", self.output_path)

        return self.output_path


class YTSubtitleEngine:
    """Core engine that coordinates search, subtitle extraction, link saving, and archiving."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize application engine.

        Args:
            config: Application configuration.
        """

        config.validate()

        self.config = config
        self.logger = self._build_logger(config.log_level)
        self.search_service = SearchService(self.logger)
        self.subtitle_service = SubtitleService(config.language_codes, self.logger)

    def run(self) -> Path:
        """Run the complete subtitle extraction workflow.

        Returns:
            Path to final ZIP archive.

        Raises:
            YTSubtitleError: If the workflow cannot complete.
        """

        videos = self.search_service.search(
            query=self.config.query,
            limit=self.config.limit,
            upload_days=self.config.upload_days,
            sort_by=self.config.sort_by,
        )

        if not videos:
            raise SearchServiceError("No videos found for the given query and date range.")

        FileIO.save_youtube_links(self.config.links_output_path, videos)
        self.logger.info("YouTube links saved: %s", self.config.links_output_path)

        with ArchiveService(self.config.output_path, self.logger) as archive_service:
            subtitle_files = self._download_transcripts_parallel(
                videos=videos,
                archive_service=archive_service,
            )

            if not subtitle_files:
                raise TranscriptNotFoundError(
                    "No subtitles were available for the selected videos."
                )

            return archive_service.create_zip(subtitle_files)

    def _download_transcripts_parallel(
        self,
        videos: Sequence[VideoMetadata],
        archive_service: ArchiveService,
    ) -> List[Path]:
        """Download transcripts concurrently and create temporary SRT files.

        Args:
            videos: Videos to process.
            archive_service: Active archive service.

        Returns:
            List of generated SRT file paths.
        """

        subtitle_files: List[Path] = []
        worker_count = min(self.config.max_workers, len(videos))

        self.logger.info("Downloading transcripts with %d worker(s).", worker_count)

        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_video = {
                executor.submit(self.subtitle_service.fetch_srt, video): video
                for video in videos
            }

            for future in concurrent.futures.as_completed(future_to_video):
                video = future_to_video[future]

                try:
                    srt_content = future.result()
                    subtitle_file = archive_service.create_subtitle_file(video, srt_content)
                    subtitle_files.append(subtitle_file)

                    self.logger.info("Subtitle extracted: %s", video.title)

                except TranscriptNotFoundError as exc:
                    self.logger.warning("%s", exc)

                except Exception as exc:
                    self.logger.exception(
                        "Unexpected failure while processing video %s: %s",
                        video.video_id,
                        exc,
                    )

        return subtitle_files

    @staticmethod
    def _build_logger(log_level: str) -> logging.Logger:
        """Build configured application logger.

        Args:
            log_level: Logging level name such as INFO or DEBUG.

        Returns:
            Configured logger instance.
        """

        logger = logging.getLogger("yt_subtitle_engine")
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        logger.handlers.clear()

        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

        logger.addHandler(handler)
        logger.propagate = False

        return logger


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