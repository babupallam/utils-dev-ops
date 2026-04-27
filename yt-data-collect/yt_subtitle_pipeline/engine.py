from __future__ import annotations

import concurrent.futures
from pathlib import Path
from typing import List, Sequence

from yt_subtitle_pipeline.exceptions import (
    SearchServiceError,
    TranscriptNotFoundError,
    YTSubtitleError,
)
from yt_subtitle_pipeline.models import AppConfig, VideoMetadata
from yt_subtitle_pipeline.services.archive_service import ArchiveService
from yt_subtitle_pipeline.services.search_service import SearchService
from yt_subtitle_pipeline.services.subtitle_service import SubtitleService
from yt_subtitle_pipeline.utils.file_io import FileIO
from yt_subtitle_pipeline.utils.logger import build_logger


class YTSubtitleEngine:
    """Core engine that coordinates search, subtitle extraction, link saving, and archiving."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize application engine.

        Args:
            config: Application configuration.
        """

        config.validate()

        self.config = config
        self.logger = build_logger(config.log_level)
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