from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

from yt_subtitle_pipeline.models import VideoMetadata


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