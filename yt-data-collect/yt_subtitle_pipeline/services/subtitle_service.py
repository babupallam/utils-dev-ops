from __future__ import annotations

import logging
import time
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

    def __init__(
        self,
        language_codes: Sequence[str],
        logger: logging.Logger,
        request_delay_seconds: float = 8.0,
        retry_count: int = 3,
        retry_backoff_seconds: float = 10.0,
    ) -> None:
        """Initialize subtitle service.

        Args:
            language_codes: Preferred transcript language codes.
            logger: Application logger.
            request_delay_seconds: Delay before each transcript request.
            retry_count: Number of retry attempts per video.
            retry_backoff_seconds: Base retry waiting time.
        """

        self.language_codes = tuple(language_codes)
        self.logger = logger
        self.api = YouTubeTranscriptApi()
        self.request_delay_seconds = request_delay_seconds
        self.retry_count = retry_count
        self.retry_backoff_seconds = retry_backoff_seconds

    def fetch_srt(self, video: VideoMetadata) -> str:
        """Fetch transcript for one video and convert it to SRT.

        Args:
            video: Video metadata.

        Returns:
            SRT-formatted subtitle content.

        Raises:
            TranscriptNotFoundError: If transcript is unavailable.
        """

        last_error: Exception | None = None

        for attempt in range(1, self.retry_count + 2):
            try:
                if self.request_delay_seconds > 0:
                    self.logger.debug(
                        "Waiting %.2f seconds before transcript request for video %s.",
                        self.request_delay_seconds,
                        video.video_id,
                    )
                    time.sleep(self.request_delay_seconds)

                self.logger.debug(
                    "Fetching transcript for video %s. Attempt %d.",
                    video.video_id,
                    attempt,
                )

                fetched_transcript = self.api.fetch(
                    video.video_id,
                    languages=list(self.language_codes),
                )

                transcript = fetched_transcript.to_raw_data()

                return Formatter.transcript_to_srt(transcript)

            except (NoTranscriptFound, TranscriptsDisabled) as exc:
                raise TranscriptNotFoundError(
                    f"No transcript available for video {video.video_id}: {video.title}"
                ) from exc

            except Exception as exc:
                last_error = exc

                if attempt > self.retry_count:
                    break

                wait_time = self.retry_backoff_seconds * attempt

                self.logger.warning(
                    "Transcript request failed for video %s. Retrying in %.2f seconds. Error: %s",
                    video.video_id,
                    wait_time,
                    exc,
                )

                time.sleep(wait_time)

        raise TranscriptNotFoundError(
            f"Failed to fetch transcript for video {video.video_id}: {last_error}"
        )