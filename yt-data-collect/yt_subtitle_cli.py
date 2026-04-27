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


@dataclass(frozen=True)
class AppConfig:
    """Application configuration.

    Attributes:
        query: Search keywords used to find YouTube videos.
        limit: Maximum number of videos to process.
        output_path: Final ZIP archive path.
        upload_days: Only include videos uploaded within this number of days.
        max_limit: Maximum allowed search limit.
        language_codes: Preferred transcript language codes.
        max_workers: Number of parallel transcript download workers.
        log_level: Logging verbosity level.
    """

    query: str
    limit: int
    output_path: Path
    upload_days: int = 365
    max_limit: int = 50
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

        if not self.output_path.name.lower().endswith(".zip"):
            raise ValueError("Output path must end with .zip.")


@dataclass(frozen=True)
class VideoMetadata:
    """Normalized YouTube video metadata.

    Attributes:
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


class SearchService:
    """Search service that uses yt-dlp to fetch YouTube metadata."""

    def __init__(self, logger: logging.Logger) -> None:
        """Initialize the search service.

        Args:
            logger: Application logger.
        """

        self.logger = logger

    def search(self, query: str, limit: int, upload_days: int) -> List[VideoMetadata]:
        """Search YouTube videos and return filtered metadata.

        Args:
            query: Search keywords.
            limit: Maximum number of videos to return.
            upload_days: Include only videos uploaded within this number of days.

        Returns:
            List of normalized video metadata sorted by view count.

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
            # Step 1:
            # New youtube-transcript-api versions use fetch().
            fetched_transcript = self.api.fetch(
                video.video_id,
                languages=list(self.language_codes),
            )

            # Step 2:
            # Convert FetchedTranscript object into normal list[dict].
            transcript = fetched_transcript.to_raw_data()

        except (NoTranscriptFound, TranscriptsDisabled) as exc:
            raise TranscriptNotFoundError(
                f"No transcript available for video {video.video_id}: {video.title}"
            ) from exc

        except Exception as exc:
            raise TranscriptNotFoundError(
                f"Failed to fetch transcript for video {video.video_id}: {exc}"
            ) from exc

        # Step 3:
        # Convert raw transcript JSON into valid .srt text.
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
    """Core engine that coordinates search, subtitle extraction, and archiving."""

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
        )

        if not videos:
            raise SearchServiceError("No videos found for the given query and date range.")

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

        self.logger.info(
            "Downloading transcripts with %d worker(s).",
            worker_count,
        )

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

                    self.logger.info(
                        "Subtitle extracted: %s",
                        video.title,
                    )
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
        "--query",
        required=True,
        type=str,
        help="YouTube search query.",
    )

    parser.add_argument(
        "--limit",
        required=True,
        type=int,
        help="Maximum number of videos to process.",
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output ZIP file path.",
    )

    parser.add_argument(
        "--upload-days",
        default=365,
        type=int,
        help="Only include videos uploaded within the last N days.",
    )

    parser.add_argument(
        "--max-workers",
        default=4,
        type=int,
        help="Number of parallel transcript workers.",
    )

    parser.add_argument(
        "--language",
        default="en",
        type=str,
        help="Comma-separated transcript language codes, for example: en,en-US.",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        help="Logging level.",
    )

    return parser.parse_args()


def main() -> int:
    """Application entry point.

    Returns:
        Process exit code.
    """

    args = parse_args()

    language_codes = tuple(
        language.strip()
        for language in args.language.split(",")
        if language.strip()
    )

    config = AppConfig(
        query=args.query,
        limit=args.limit,
        output_path=args.output,
        upload_days=args.upload_days,
        language_codes=language_codes or ("en",),
        max_workers=args.max_workers,
        log_level=args.log_level,
    )

    try:
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