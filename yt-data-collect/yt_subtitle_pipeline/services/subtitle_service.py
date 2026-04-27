from __future__ import annotations

import logging
from typing import Sequence

from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

from yt_subtitle_pipeline.exceptions import TranscriptNotFoundError
from yt_subtitle_pipeline.models import VideoMetadata
from yt_subtitle_pipeline.utils.formatter import Formatter


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