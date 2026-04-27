from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict, List

import yt_dlp

from yt_subtitle_pipeline.exceptions import SearchServiceError
from yt_subtitle_pipeline.models import VideoMetadata


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