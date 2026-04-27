from __future__ import annotations

import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, Optional

from yt_subtitle_pipeline.exceptions import ArchiveServiceError
from yt_subtitle_pipeline.models import VideoMetadata
from yt_subtitle_pipeline.utils.file_io import FileIO
from yt_subtitle_pipeline.utils.formatter import Formatter


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