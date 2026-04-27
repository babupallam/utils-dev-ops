from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from yt_subtitle_pipeline.exceptions import SearchLimitExceeded


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