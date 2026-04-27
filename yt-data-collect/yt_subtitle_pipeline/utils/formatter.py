from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence


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